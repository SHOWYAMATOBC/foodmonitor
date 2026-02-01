#!/usr/bin/env python3
"""
DGS2 970-Series Sensor Reader

Reads data from DGS2 digital gas sensor connected via USB-UART adapter
Sends data to Node.js backend via REST API

Configuration:
- Serial Port: /dev/ttyUSB0
- Baud Rate: 9600
- Data Bits: 8
- Parity: None
- Stop Bits: 1

Sensor Output Format:
sensor_sn, ppb, temperature, humidity, adc_gas, adc_temp, adc_hum

Sensor Commands:
\r - Single measurement
C  - Toggle continuous measurements (~1 Hz)
"""

import serial
import json
import requests
import sys
import time
import csv
import os
from datetime import datetime
import logging

# Configuration
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600
BACKEND_URL = 'http://localhost:3001/api/sensor/data'
RETRY_COUNT = 5
RETRY_DELAY = 2  # seconds
LOG_FILE = 'sensor_readings.csv'
MAX_LOG_ENTRIES = 500

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DGS2Reader:
    """DGS2 Sensor Reader Class"""
    
    def __init__(self, port=SERIAL_PORT, baudrate=BAUD_RATE):
        """
        Initialize sensor reader
        
        Args:
            port (str): Serial port path
            baudrate (int): Serial baudrate
        """
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.readings_count = 0
        self.csv_entries_count = 0
        
    def connect(self):
        """
        Connect to serial port with retry logic
        
        Returns:
            bool: True if connected, False otherwise
        """
        for attempt in range(RETRY_COUNT):
            try:
                self.ser = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1
                )
                logger.info(f'Connected to {self.port} at {self.baudrate} baud')
                return True
            except serial.SerialException as e:
                logger.warning(f'Connection attempt {attempt + 1}/{RETRY_COUNT} failed: {e}')
                if attempt < RETRY_COUNT - 1:
                    time.sleep(RETRY_DELAY)
        
        logger.error(f'Failed to connect to sensor after {RETRY_COUNT} attempts')
        return False
    
    def send_command(self, command):
        """
        Send command to sensor
        
        Args:
            command (str): Command to send ('R' for single, 'C' for continuous)
        """
        if not self.ser or not self.ser.is_open:
            logger.error('Serial connection not open')
            return
        
        try:
            # Commands are sent as bytes
            if command == 'R':
                self.ser.write(b'\r')
                logger.debug('Sent single measurement command (\\r)')
            elif command == 'C':
                self.ser.write(b'C')
                logger.debug('Sent continuous mode command (C)')
        except serial.SerialException as e:
            logger.error(f'Failed to send command: {e}')
    
    def parse_reading(self, line):
        """
        Parse sensor output line into structured data
        
        Format: sensor_sn, ppb, temperature, humidity, adc_gas, adc_temp, adc_hum
        
        Args:
            line (str): Raw sensor output line
            
        Returns:
            dict: Parsed sensor data or None if invalid
        """
        try:
            # Remove whitespace and split by comma
            parts = [p.strip() for p in line.split(',')]
            
            if len(parts) != 7:
                logger.warning(f'Invalid reading format (expected 7 fields, got {len(parts)}): {line}')
                return None
            
            sensor_sn, ppb, temp_raw, hum_raw, adc_gas, adc_temp, adc_hum = parts
            
            # Convert values to appropriate types
            # Temperature and humidity are scaled by 100
            reading = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'sensor_sn': sensor_sn,
                'ppb': float(ppb)-2300, # Adjusting baseline as per sensor calibration
                'temperature': float(temp_raw) / 100.0,
                'humidity': float(hum_raw) / 100.0,
                'adc_gas': int(adc_gas),
                'adc_temp': int(adc_temp),
                'adc_hum': int(adc_hum)
            }
            
            return reading
        except (ValueError, IndexError) as e:
            logger.warning(f'Failed to parse reading: {e} | Line: {line}')
            return None
    
    def send_to_backend(self, data):
        """
        Send parsed sensor data to Node.js backend
        
        Args:
            data (dict): Parsed sensor reading
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.post(
                BACKEND_URL,
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f'Backend returned status {response.status_code}: {response.text}')
                return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f'Cannot connect to backend at {BACKEND_URL}. Is the server running?')
            return False
        except requests.exceptions.Timeout:
            logger.error('Request to backend timed out')
            return False
        except Exception as e:
            logger.error(f'Failed to send data to backend: {e}')
            return False
    
    def save_to_csv(self, data):
        """
        Save reading to CSV log file (only first 500 entries, then stop)
        
        Args:
            data (dict): Parsed sensor reading
        """
        try:
            # Only save if we haven't reached the limit
            if self.csv_entries_count >= MAX_LOG_ENTRIES:
                return
            
            # Check if file exists to decide whether to write header
            file_exists = os.path.exists(LOG_FILE)
            
            # Append entry to CSV
            with open(LOG_FILE, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'sensor_sn', 'ppb', 'temperature', 'humidity', 'adc_gas', 'adc_temp', 'adc_hum']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header only if file is new
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(data)
            
            self.csv_entries_count += 1
            logger.debug(f'Logged to CSV ({self.csv_entries_count}/{MAX_LOG_ENTRIES})')
            
            # Log when we reach the limit
            if self.csv_entries_count >= MAX_LOG_ENTRIES:
                logger.info(f'CSV logging limit reached ({MAX_LOG_ENTRIES} entries). No more entries will be saved.')
        except Exception as e:
            logger.error(f'Failed to save to CSV: {e}')
    
    def run(self):
        """
        Main reader loop
        Reads from sensor and sends to backend
        """
        if not self.connect():
            return
        
        try:
            logger.info('Starting continuous measurements...')
            self.send_command('C')  # Enable continuous mode
            
            logger.info('Waiting for sensor readings...')
            
            while True:
                try:
                    # Read line from sensor
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8').strip()
                        
                        if line:  # Skip empty lines
                            # Parse the reading
                            reading = self.parse_reading(line)
                            
                            if reading:
                                self.readings_count += 1
                                
                                # Send to backend
                                if self.send_to_backend(reading):
                                    # Save to CSV (keeps last 500)
                                    self.save_to_csv(reading)
                                    
                                    logger.info(
                                        f'Reading #{self.readings_count} | '
                                        f'PPB: {reading["ppb"]:.1f} | '
                                        f'Temp: {reading["temperature"]:.2f}°C | '
                                        f'Humidity: {reading["humidity"]:.2f}%'
                                    )
                                else:
                                    logger.warning('Failed to send reading to backend')
                    else:
                        time.sleep(0.1)  # Short sleep to avoid busy-waiting
                        
                except serial.SerialException as e:
                    logger.error(f'Serial read error: {e}')
                    break
                except UnicodeDecodeError as e:
                    logger.warning(f'Failed to decode serial data: {e}')
                    continue
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logger.error(f'Unexpected error in read loop: {e}')
                    time.sleep(1)
                    
        except KeyboardInterrupt:
            logger.info('Shutting down...')
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()
                logger.info(f'Serial port closed. Total readings: {self.readings_count}')

def main():
    """Main entry point"""
    logger.info('DGS2 Sensor Reader Starting')
    logger.info(f'Serial Port: {SERIAL_PORT}')
    logger.info(f'Baud Rate: {BAUD_RATE}')
    logger.info(f'Backend URL: {BACKEND_URL}')
    
    reader = DGS2Reader(SERIAL_PORT, BAUD_RATE)
    reader.run()

if __name__ == '__main__':
    main()
