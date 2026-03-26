#!/usr/bin/env python3
"""
BME688 Environmental Sensor Reader

Reads temperature, humidity, pressure, and gas resistance from BME688 sensor.
Stores raw readings in CSV and provides functions for data access.

Requirements:
- BME688 sensor connected via I2C at address 0x77
- Adafruit CircuitPython BME680 library (pip install adafruit-circuitpython-bme680 adafruit-blinka)
"""

import sys
import time
import os
import csv
import threading
import logging
from datetime import datetime
from collections import deque
from typing import Dict, Optional, List

try:
    import board
    import busio
    import adafruit_bme680
except ImportError:
    print("Error: Adafruit BME680 library not found.")
    print("Install with: pip install adafruit-circuitpython-bme680 adafruit-blinka")
    sys.exit(1)

# Configuration
I2C_ADDRESS = 0x77
BME688_CSV_FILENAME = 'bme688_data.csv'
READ_INTERVAL = 2  # seconds
BUFFER_SIZE = 30  # Store last 30 readings in memory

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('BME688')


class BME688Reader:
    """BME688 Sensor Reader with threading and data buffering"""

    def __init__(self, csv_filename: str = BME688_CSV_FILENAME):
        """Initialize BME688 reader"""
        self.csv_filename = csv_filename
        self.sensor = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()

        # In-memory buffer for readings
        self.buffer = deque(maxlen=BUFFER_SIZE)

        # Calibration state
        self.baseline_resistance = None
        self.last_valid_reading = None

    def initialize_sensor(self) -> bool:
        """Initialize the BME688 sensor"""
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=I2C_ADDRESS)

            # Set gas sensor parameters for better readings
            self.sensor.sea_level_pressure = 1013.25

            logger.info("BME688 sensor initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize BME688: {e}")
            return False

    def read_sensor_data(self) -> Optional[Dict]:
        """
        Read raw data from BME688 sensor

        Returns:
            Dictionary with readings or None if failed
        """
        try:
            reading = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'temperature_c': round(self.sensor.temperature, 2),
                'humidity_percent': round(self.sensor.humidity, 2),
                'pressure_hpa': round(self.sensor.pressure, 2),
                'gas_resistance_ohm': round(self.sensor.gas, 0)
            }

            # Update baseline resistance on first reading
            if self.baseline_resistance is None and reading['gas_resistance_ohm'] > 0:
                self.baseline_resistance = reading['gas_resistance_ohm']
                logger.info(f"Baseline gas resistance set to {self.baseline_resistance} Ω")

            return reading
        except Exception as e:
            logger.error(f"Failed to read sensor: {e}")
            return None

    def log_to_csv(self, data: Dict) -> None:
        """Log sensor data to CSV file"""
        try:
            file_exists = os.path.isfile(self.csv_filename)

            with open(self.csv_filename, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'temperature_c', 'humidity_percent', 'pressure_hpa', 'gas_resistance_ohm']
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

        if not self.initialize_sensor():
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        logger.info("BME688 reader started")

    def stop(self) -> None:
        """Stop reading sensor"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("BME688 reader stopped")

    def _read_loop(self) -> None:
        """Main reading loop (runs in background thread)"""
        while self.is_running:
            try:
                data = self.read_sensor_data()

                if data:
                    with self.lock:
                        self.buffer.append(data)
                        self.last_valid_reading = data

                    self.log_to_csv(data)

                    logger.debug(
                        f"T: {data['temperature_c']}°C, "
                        f"H: {data['humidity_percent']}%, "
                        f"P: {data['pressure_hpa']}hPa, "
                        f"Gas: {data['gas_resistance_ohm']}Ω"
                    )

                time.sleep(READ_INTERVAL)

            except Exception as e:
                logger.error(f"Error in read loop: {e}")
                time.sleep(1)

    def get_latest_reading(self) -> Optional[Dict]:
        """Get latest sensor reading"""
        with self.lock:
            return self.last_valid_reading

    def get_average_readings(self, seconds: int = 60) -> Optional[Dict]:
        """
        Get averaged readings over specified period

        Returns:
            Dict with averaged values or None if insufficient data
        """
        with self.lock:
            if not self.buffer:
                return None

            readings = list(self.buffer)

            if len(readings) < 2:
                return None

            avg_reading = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'temperature_c': round(sum(r['temperature_c'] for r in readings) / len(readings), 2),
                'humidity_percent': round(sum(r['humidity_percent'] for r in readings) / len(readings), 2),
                'pressure_hpa': round(sum(r['pressure_hpa'] for r in readings) / len(readings), 2),
                'gas_resistance_ohm': round(sum(r['gas_resistance_ohm'] for r in readings) / len(readings), 0),
                'readings_count': len(readings)
            }

            return avg_reading

    def calculate_aqi(self) -> Optional[float]:
        """
        Calculate AQI from gas resistance

        Formula: AQI = (baseline_resistance / current_resistance) * 100
        Normalized to 0-500 scale

        Returns:
            AQI score or None if not available
        """
        if self.baseline_resistance is None or not self.last_valid_reading:
            return None

        current_resistance = self.last_valid_reading['gas_resistance_ohm']

        if current_resistance <= 0:
            return None

        # Calculate raw AQI
        raw_aqi = (self.baseline_resistance / current_resistance) * 100

        # Normalize to 0-500 scale
        # 100 = clean air (baseline), 500 = very polluted
        normalized_aqi = max(0, min(500, raw_aqi * 5))

        return round(normalized_aqi, 2)

    def get_buffer_data(self) -> List[Dict]:
        """Get all buffered readings"""
        with self.lock:
            return list(self.buffer)


def read_bme688() -> Optional[Dict]:
    """Standalone function to get latest BME688 reading"""
    reader = BME688Reader()
    if reader.initialize_sensor():
        data = reader.read_sensor_data()
        return data
    return None


if __name__ == "__main__":
    # Test the reader
    reader = BME688Reader()
    reader.start()

    try:
        for i in range(10):
            time.sleep(2)
            latest = reader.get_latest_reading()
            if latest:
                print(f"[{i+1}] {latest}")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        reader.stop()
