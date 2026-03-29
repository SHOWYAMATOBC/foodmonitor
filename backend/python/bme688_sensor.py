#!/usr/bin/env python3
"""
BME688 Environmental Sensor Reader
Reads temperature, humidity, pressure from BME688 sensor
One reading per minute saved to CSV
"""

import sys
import time
import os
import csv
import threading
import logging
from datetime import datetime
from collections import deque
from typing import Dict, Optional

try:
    import board
    import busio
    import adafruit_bme680
    BME688_LIB_AVAILABLE = True
except ImportError:
    board = None
    busio = None
    adafruit_bme680 = None
    BME688_LIB_AVAILABLE = False

# Configuration
I2C_ADDRESS = 0x77
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BME688_CSV_FILENAME = os.path.join(BASE_DIR, 'data', 'bme688_readings.csv')
READ_INTERVAL = 10  # seconds between individual reads
BUFFER_INTERVAL = 60  # aggregate every 60 seconds
BUFFER_SIZE = 6  # 60 seconds / 10 seconds = 6 readings per minute

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] BME688 - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('BME688')


class BME688Sensor:
    """BME688 Environmental Sensor Reader"""

    def __init__(self, csv_filename: str = BME688_CSV_FILENAME):
        """Initialize BME688 reader"""
        self.csv_filename = csv_filename
        self.sensor = None
        self.is_running = False
        self.thread = None
        self.lock = threading.Lock()

        # Buffer for readings (60 seconds)
        self.buffer = deque(maxlen=BUFFER_SIZE)
        self.last_valid_reading = None
        self.last_csv_write = None

    def initialize_sensor(self) -> bool:
        """Initialize the BME688 sensor"""
        if not BME688_LIB_AVAILABLE:
            logger.error("✗ Adafruit BME680 library not found. Running without BME688 sensor.")
            logger.error("  Install with: pip install adafruit-circuitpython-bme680 adafruit-blinka")
            return False
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=I2C_ADDRESS)
            self.sensor.sea_level_pressure = 1013.25
            logger.info("✓ BME688 sensor initialized successfully")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to initialize BME688: {e}")
            return False

    def read_sensor_data(self) -> Optional[Dict]:
        """Read raw data from BME688 sensor"""
        try:
            reading = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'temperature_c': round(self.sensor.temperature, 2),
                'humidity_percent': round(self.sensor.humidity, 2),
                'pressure_hpa': round(self.sensor.pressure, 2),
                'gas_resistance_ohm': round(self.sensor.gas, 0)
            }
            return reading
        except Exception as e:
            logger.error(f"Failed to read sensor: {e}")
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
            'temperature_c': round(sum(r['temperature_c'] for r in readings) / len(readings), 2),
            'humidity_percent': round(sum(r['humidity_percent'] for r in readings) / len(readings), 2),
            'pressure_hpa': round(sum(r['pressure_hpa'] for r in readings) / len(readings), 2),
            'gas_resistance_ohm': round(sum(r['gas_resistance_ohm'] for r in readings) / len(readings), 0),
            'readings_count': len(readings)
        }
        return avg_reading

    def log_to_csv(self, data: Dict) -> None:
        """Log sensor data to CSV file"""
        try:
            file_exists = os.path.isfile(self.csv_filename)

            with open(self.csv_filename, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'temperature_c', 'humidity_percent', 'pressure_hpa', 'gas_resistance_ohm']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                csv_data = {k: data[k] for k in fieldnames if k in data}
                writer.writerow(csv_data)
            logger.info(f"📝 BME688 reading saved: T={data['temperature_c']}°C, H={data['humidity_percent']}%, P={data['pressure_hpa']}hPa, R={data['gas_resistance_ohm']}Ω")
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
        logger.info("🚀 BME688 reader started")

    def stop(self) -> None:
        """Stop reading sensor"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("⏹️  BME688 reader stopped")

    def _read_loop(self) -> None:
        """Main reading loop (runs in background thread)"""
        last_buffer_flush = time.time()

        while self.is_running:
            try:
                # Read sensor data
                data = self.read_sensor_data()

                if data:
                    with self.lock:
                        self.buffer.append(data)
                        self.last_valid_reading = data

                # Check if 60 seconds have passed
                current_time = time.time()
                if current_time - last_buffer_flush >= BUFFER_INTERVAL:
                    avg = self.get_average_reading()
                    if avg:
                        self.log_to_csv(avg)
                    last_buffer_flush = current_time

                time.sleep(READ_INTERVAL)

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
    sensor = BME688Sensor()
    sensor.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down BME688 sensor...")
        sensor.stop()
