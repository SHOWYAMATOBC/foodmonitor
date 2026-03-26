#!/usr/bin/env python3
"""
DDS2-970650 VOC Gas Sensor Reader

Reads VOC (Volatile Organic Compounds) data from DDS2-970650 digital gas sensor.
Handles sensor warm-up, calibration, and stores raw readings in CSV.

Sensor Output Format:
sensor_sn, ppb, temperature, humidity, adc_gas, adc_temp, adc_hum

Serial Port Configuration:
- Port: /dev/ttyUSB0 (configurable)
- Baud Rate: 9600
- Data Bits: 8
- Parity: None
- Stop Bits: 1

Sensor Commands:
- \r (CR) - Single measurement
- C - Toggle continuous mode (~1 Hz)
"""

import serial
import time
import os
import csv
import threading
import logging
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, Optional, List

# Configuration
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
DDS2_CSV_FILENAME = 'dds2_data.csv'
READ_TIMEOUT = 2  # seconds

# Calibration
VOC_WARMUP_TIME = 15 * 60  # 15 minutes warm-up phase
VOC_BASELINE_SAMPLES = 100  # Samples to average for baseline

BUFFER_SIZE = 30  # Store last 30 readings in memory

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('DDS2')


class DDS2Reader:
    """DDS2-970650 Sensor Reader with VOC calibration"""

    def __init__(self, port: str = SERIAL_PORT, baudrate: int = BAUD_RATE,
                 csv_filename: str = DDS2_CSV_FILENAME):
        """Initialize DDS2 reader"""
        self.port = port
        self.baudrate = baudrate
        self.csv_filename = csv_filename
        self.ser = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()

        # In-memory buffer
        self.buffer = deque(maxlen=BUFFER_SIZE)
        self.last_valid_reading = None

        # VOC Calibration state
        self.warmup_start_time = None
        self.is_warming_up = False
        self.baseline_ppb = None
        self.baseline_samples = deque(maxlen=VOC_BASELINE_SAMPLES)
        self.calibration_complete = False

    def connect(self) -> bool:
        """Connect to serial port"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=READ_TIMEOUT
            )
            logger.info(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to serial port {self.port}: {e}")
            return False

    def disconnect(self) -> None:
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial port closed")

    def send_command(self, command: str) -> None:
        """
        Send command to sensor

        Args:
            command: 'R' for single reading, 'C' for continuous mode
        """
        if not self.ser or not self.ser.is_open:
            logger.error("Serial connection not open")
            return

        try:
            if command.upper() == 'R':
                self.ser.write(b'\r')
                logger.debug("Sent single measurement command (CR)")
            elif command.upper() == 'C':
                self.ser.write(b'C')
                logger.debug("Sent continuous mode command (C)")
        except serial.SerialException as e:
            logger.error(f"Failed to send command: {e}")

    def parse_reading(self, line: str) -> Optional[Dict]:
        """
        Parse sensor output line

        Format: sensor_sn, ppb, temperature, humidity, adc_gas, adc_temp, adc_hum

        Args:
            line: Raw sensor output

        Returns:
            Parsed data dictionary or None if invalid
        """
        try:
            parts = [p.strip() for p in line.split(',')]

            if len(parts) != 7:
                logger.warning(f"Invalid reading format (got {len(parts)} fields): {line}")
                return None

            sensor_sn, ppb_str, temp_str, hum_str, adc_gas_str, adc_temp_str, adc_hum_str = parts

            # Temperature and humidity are scaled by 100
            reading = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'sensor_sn': sensor_sn,
                'ppb_raw': float(ppb_str),
                'temperature': float(temp_str) / 100.0,
                'humidity': float(hum_str) / 100.0,
                'adc_gas': int(adc_gas_str),
                'adc_temp': int(adc_temp_str),
                'adc_hum': int(adc_hum_str)
            }

            return reading
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse reading: {e} | Line: {line}")
            return None

    def calibrate_voc(self, ppb_raw: float) -> None:
        """
        Perform VOC calibration during warm-up phase

        Args:
            ppb_raw: Raw PPB reading from sensor
        """
        if not self.is_warming_up:
            return

        self.baseline_samples.append(ppb_raw)

        # Check if warm-up period is complete
        elapsed = datetime.utcnow() - self.warmup_start_time
        if elapsed.total_seconds() >= VOC_WARMUP_TIME:
            if len(self.baseline_samples) > 0:
                self.baseline_ppb = sum(self.baseline_samples) / len(self.baseline_samples)
                self.is_warming_up = False
                self.calibration_complete = True
                logger.info(f"VOC calibration complete. Baseline PPB: {self.baseline_ppb:.2f}")
            else:
                logger.warning("No samples collected during warm-up phase")

    def apply_voc_calibration(self, ppb_raw: float) -> float:
        """
        Apply VOC calibration to raw PPB reading

        Formula: voc_ppb = |ppb_raw - baseline_ppb|

        Args:
            ppb_raw: Raw PPB value from sensor

        Returns:
            Calibrated VOC value in PPB
        """
        if self.is_warming_up:
            self.calibrate_voc(ppb_raw)
            return ppb_raw  # Return raw value during warm-up

        if self.baseline_ppb is None:
            return ppb_raw  # Return raw if no calibration yet

        # Return absolute difference from baseline
        return abs(ppb_raw - self.baseline_ppb)

    def log_to_csv(self, data: Dict) -> None:
        """Log sensor data to CSV file"""
        try:
            file_exists = os.path.isfile(self.csv_filename)

            with open(self.csv_filename, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'sensor_sn', 'ppb', 'temperature', 'humidity',
                            'adc_gas', 'adc_temp', 'adc_hum']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                writer.writerow(data)
        except Exception as e:
            logger.error(f"Failed to log to CSV: {e}")

    def start(self) -> None:
        """Start reading sensor in background thread"""
        if self.is_running:
            logger.warning("Sensor already running")
            return

        if not self.connect():
            return

        self.is_running = True
        self.is_warming_up = True
        self.warmup_start_time = datetime.utcnow()
        logger.info(f"Starting VOC warm-up phase ({VOC_WARMUP_TIME / 60:.0f} minutes)...")

        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        logger.info("DDS2 reader started")

    def stop(self) -> None:
        """Stop reading sensor"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.disconnect()
        logger.info("DDS2 reader stopped")

    def _read_loop(self) -> None:
        """Main reading loop (runs in background thread)"""
        try:
            # Start continuous mode
            self.send_command('C')
            time.sleep(1)

            while self.is_running:
                try:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8').strip()

                        if line:
                            reading = self.parse_reading(line)

                            if reading:
                                # Apply VOC calibration
                                ppb_calibrated = self.apply_voc_calibration(reading['ppb_raw'])

                                # Store calibrated PPB
                                reading['ppb'] = round(ppb_calibrated, 2)
                                reading['voc_ppb'] = reading['ppb']  # Alias for data fusion

                                with self.lock:
                                    self.buffer.append(reading)
                                    self.last_valid_reading = reading

                                self.log_to_csv(reading)

                                status = "WARMING UP" if self.is_warming_up else "CALIBRATED"
                                logger.debug(
                                    f"{status} | "
                                    f"PPB: {reading['ppb']:.2f}, "
                                    f"T: {reading['temperature']:.2f}°C, "
                                    f"H: {reading['humidity']:.2f}%"
                                )
                    else:
                        time.sleep(0.1)

                except serial.SerialException as e:
                    logger.error(f"Serial read error: {e}")
                    if self.is_running:
                        time.sleep(1)
                except UnicodeDecodeError as e:
                    logger.warning(f"Failed to decode serial data: {e}")
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error(f"Error in read loop: {e}")
                    time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Read loop interrupted")

    def get_latest_reading(self) -> Optional[Dict]:
        """Get latest sensor reading"""
        with self.lock:
            return self.last_valid_reading

    def get_average_readings(self) -> Optional[Dict]:
        """Get averaged readings from buffer"""
        with self.lock:
            if not self.buffer:
                return None

            readings = list(self.buffer)

            if len(readings) < 2:
                return None

            avg_reading = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'sensor_sn': readings[0]['sensor_sn'],
                'ppb_avg': round(sum(r['ppb'] for r in readings) / len(readings), 2),
                'ppb_max': round(max(r['ppb'] for r in readings), 2),
                'ppb_min': round(min(r['ppb'] for r in readings), 2),
                'temperature': round(sum(r['temperature'] for r in readings) / len(readings), 2),
                'humidity': round(sum(r['humidity'] for r in readings) / len(readings), 2),
                'readings_count': len(readings)
            }

            return avg_reading

    def is_calibrated(self) -> bool:
        """Check if VOC sensor is calibrated"""
        return self.calibration_complete

    def get_warmup_time_remaining(self) -> Optional[int]:
        """Get remaining warm-up time in seconds"""
        if not self.is_warming_up or not self.warmup_start_time:
            return None

        elapsed = (datetime.utcnow() - self.warmup_start_time).total_seconds()
        remaining = max(0, VOC_WARMUP_TIME - elapsed)
        return int(remaining)

    def get_buffer_data(self) -> List[Dict]:
        """Get all buffered readings"""
        with self.lock:
            return list(self.buffer)


def read_dds2() -> Optional[Dict]:
    """Standalone function to get latest DDS2 reading"""
    reader = DDS2Reader()
    if reader.connect():
        try:
            reader.send_command('R')  # Single reading
            time.sleep(0.5)

            if reader.ser.in_waiting > 0:
                line = reader.ser.readline().decode('utf-8').strip()
                return reader.parse_reading(line)
        finally:
            reader.disconnect()

    return None


if __name__ == "__main__":
    # Test the reader
    reader = DDS2Reader()
    reader.start()

    try:
        for i in range(10):
            time.sleep(2)
            latest = reader.get_latest_reading()
            if latest:
                print(f"[{i+1}] {latest}")

            remaining = reader.get_warmup_time_remaining()
            if remaining:
                print(f"    Warm-up time remaining: {remaining}s")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.stop()
