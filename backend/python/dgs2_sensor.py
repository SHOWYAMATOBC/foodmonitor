#!/usr/bin/env python3
"""
DGS2-970650 VOC Gas Sensor Reader
Reads VOC (Volatile Organic Compounds) data from DGS2 sensor
One reading per minute saved to CSV
"""

import serial
import time
import os
import csv
import threading
import logging
from datetime import datetime
from collections import deque
from typing import Dict, Optional

# Configuration
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DGS2_CSV_FILENAME = os.path.join(BASE_DIR, 'data', 'dgs2_readings.csv')
READ_INTERVAL = 10  # seconds between individual reads
BUFFER_INTERVAL = 60  # aggregate every 60 seconds
BUFFER_SIZE = 6  # 60 seconds / 10 seconds = 6 readings per minute

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] DGS2 - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('DGS2')


class DGS2Sensor:
    """DGS2-970650 VOC Gas Sensor Reader"""

    def __init__(self, port: str = SERIAL_PORT, baudrate: int = BAUD_RATE,
                 csv_filename: str = DGS2_CSV_FILENAME):
        """Initialize DGS2 reader"""
        self.port = port
        self.baudrate = baudrate
        self.csv_filename = csv_filename
        self.ser = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()

        # Buffer for readings (60 seconds)
        self.buffer = deque(maxlen=BUFFER_SIZE)
        self.last_valid_reading = None

    def connect(self) -> bool:
        """Connect to serial port"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2
            )
            logger.info(f"✓ Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            logger.error(f"✗ Failed to connect to serial port {self.port}: {e}")
            return False

    def disconnect(self) -> None:
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial port closed")

    def send_command(self, command: str) -> None:
        """Send command to sensor"""
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
        """
        try:
            parts = [p.strip() for p in line.split(',')]

            if len(parts) != 7:
                return None

            sensor_sn, ppb_str, temp_str, hum_str, adc_gas_str, adc_temp_str, adc_hum_str = parts

            # Temperature and humidity are scaled by 100
            reading = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'sensor_sn': sensor_sn,
                'ppb': float(ppb_str),
                'temperature': float(temp_str) / 100.0,
                'humidity': float(hum_str) / 100.0,
                'adc_gas': int(adc_gas_str),
                'adc_temp': int(adc_temp_str),
                'adc_hum': int(adc_hum_str)
            }

            return reading
        except (ValueError, IndexError):
            return None

    def get_average_reading(self) -> Optional[Dict]:
        """Get average reading from current buffer"""
        if not self.buffer:
            return None

        with self.lock:
            readings = list(self.buffer)

        if len(readings) == 0:
            return None

        avg_reading = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'ppb': round(sum(r['ppb'] for r in readings) / len(readings), 2),
            'temperature': round(sum(r['temperature'] for r in readings) / len(readings), 2),
            'humidity': round(sum(r['humidity'] for r in readings) / len(readings), 2),
            'readings_count': len(readings)
        }
        return avg_reading

    def log_to_csv(self, data: Dict) -> None:
        """Log sensor data to CSV file"""
        try:
            file_exists = os.path.isfile(self.csv_filename)

            with open(self.csv_filename, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'ppb', 'temperature', 'humidity']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                csv_data = {k: data[k] for k in fieldnames if k in data}
                writer.writerow(csv_data)
            logger.info(f"📝 DGS2 reading saved: VOC={data['ppb']}ppb, T={data['temperature']}°C, H={data['humidity']}%")
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
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        logger.info("🚀 DGS2 reader started")

    def stop(self) -> None:
        """Stop reading sensor"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.disconnect()
        logger.info("⏹️  DGS2 reader stopped")

    def _read_loop(self) -> None:
        """Main reading loop (runs in background thread)"""
        # Start continuous mode
        self.send_command('C')
        time.sleep(1)

        last_buffer_flush = time.time()

        while self.is_running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()

                    if line:
                        reading = self.parse_reading(line)

                        if reading:
                            with self.lock:
                                self.buffer.append(reading)
                                self.last_valid_reading = reading

                # Check if 60 seconds have passed
                current_time = time.time()
                if current_time - last_buffer_flush >= BUFFER_INTERVAL:
                    avg = self.get_average_reading()
                    if avg:
                        self.log_to_csv(avg)
                    last_buffer_flush = current_time

                time.sleep(READ_INTERVAL)

            except serial.SerialException as e:
                logger.error(f"Serial read error: {e}")
                if self.is_running:
                    time.sleep(1)
            except UnicodeDecodeError:
                pass
            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                time.sleep(1)

    def get_latest_reading(self) -> Optional[Dict]:
        """Get the latest raw reading"""
        with self.lock:
            return self.last_valid_reading

    def get_buffer_size(self) -> int:
        """Get current buffer size"""
        with self.lock:
            return len(self.buffer)


if __name__ == "__main__":
    sensor = DGS2Sensor()
    sensor.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down DGS2 sensor...")
        sensor.stop()
