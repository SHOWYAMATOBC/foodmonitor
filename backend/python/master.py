#!/usr/bin/env python3
"""
Food Monitoring System - Master Control
Starts all sensors and calibrator with initialization sequence
Maintains REAL-TIME in-memory data buffer (NOT persisted to disk)
"""

import sys
import time
import json
import logging
import csv
import os
from datetime import datetime, timedelta
from collections import deque

from bme688_sensor import BME688Sensor
from dgs2_sensor import DGS2Sensor
from calibrator import DataCalibrator
import realtime_data  # Shared in-memory buffer module

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] Master - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('Master')

# Configuration
WARMUP_DURATION = 5 * 60  # 5 minutes


class AnomalyDetector:
    """Detects anomalies in sensor readings"""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.history = deque(maxlen=window_size)
        self.anomalies_detected = []

    @staticmethod
    def _as_float(value):
        """Safely convert value to float; return None for invalid values."""
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    
    def detect_anomalies(self, reading: dict) -> dict:
        """
        Detects anomalies in current reading
        Returns anomaly info or empty dict
        """
        anomalies = {}
        
        # Temperature spike detection (> 5°C change in 1 minute)
        if self.history and 'temperature' in reading and 'temperature' in self.history[-1]:
            temp_prev = self._as_float(self.history[-1].get('temperature'))
            temp_curr = self._as_float(reading.get('temperature'))
            if temp_prev is not None and temp_curr is not None and abs(temp_curr - temp_prev) > 5:
                anomalies['temperature_spike'] = {
                    'prev': temp_prev,
                    'current': temp_curr,
                    'change': temp_curr - temp_prev
                }
        
        # Humidity out-of-range detection
        humidity = self._as_float(reading.get('humidity'))
        if humidity is not None:
            if humidity > 100 or humidity < 0:
                anomalies['humidity_out_of_range'] = humidity
        
        # Humidity rapid change (> 20% in 1 minute)
        if self.history and 'humidity' in reading and 'humidity' in self.history[-1]:
            hum_prev = self._as_float(self.history[-1].get('humidity'))
            hum_curr = self._as_float(reading.get('humidity'))
            if hum_prev is not None and hum_curr is not None and abs(hum_curr - hum_prev) > 20:
                anomalies['humidity_spike'] = {
                    'prev': hum_prev,
                    'current': hum_curr,
                    'change': hum_curr - hum_prev
                }
        
        # Pressure deviation detection (> 10 hPa change)
        if self.history and 'pressure' in reading and 'pressure' in self.history[-1]:
            pres_prev = self._as_float(self.history[-1].get('pressure'))
            pres_curr = self._as_float(reading.get('pressure'))
            if pres_prev is not None and pres_curr is not None and abs(pres_curr - pres_prev) > 10:
                anomalies['pressure_anomaly'] = {
                    'prev': pres_prev,
                    'current': pres_curr,
                    'change': pres_curr - pres_prev
                }
        
        # VOC spike detection (> 50 ppb increase in 1 minute)
        if self.history and 'voc_ppb' in reading and 'voc_ppb' in self.history[-1]:
            voc_prev = self._as_float(self.history[-1].get('voc_ppb'))
            voc_curr = self._as_float(reading.get('voc_ppb'))
            if voc_prev is not None and voc_curr is not None and (voc_curr - voc_prev) > 50:
                anomalies['voc_spike'] = {
                    'prev': voc_prev,
                    'current': voc_curr,
                    'change': voc_curr - voc_prev
                }
        
        # Add current reading to history
        self.history.append(reading)
        
        return anomalies
    
    def is_anomalous(self, reading: dict) -> bool:
        """Check if reading contains any anomalies"""
        return len(self.detect_anomalies(reading)) > 0


def print_separator(title: str = ""):
    """Print a separator line"""
    if title:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}\n")
    else:
        print(f"{'=' * 70}\n")


def print_sensor_status(bme688: BME688Sensor, dgs2: DGS2Sensor) -> None:
    """Print current sensor status"""
    print("\n📡 SENSOR STATUS:\n")

    # BME688 Status
    bme688_reading = bme688.get_latest_reading()
    print(f"🌡️  BME688 Environmental Sensor:")
    print(f"   Status: {'✓ CONNECTED' if bme688.is_running else '✗ DISCONNECTED'}")
    if bme688_reading:
        print(f"   Last Reading:")
        print(f"     • Temperature: {bme688_reading['temperature_c']}°C")
        print(f"     • Humidity: {bme688_reading['humidity_percent']}%")
        print(f"     • Pressure: {bme688_reading['pressure_hpa']} hPa")
        print(f"     • Gas Resistance: {bme688_reading['gas_resistance_ohm']} Ω")
    print(f"   Buffer: {bme688.get_buffer_size()} readings")

    # DGS2 Status
    dgs2_reading = dgs2.get_latest_reading()
    print(f"\n💨 DGS2 VOC Gas Sensor:")
    print(f"   Status: {'✓ CONNECTED' if dgs2.is_running else '✗ DISCONNECTED'}")
    if dgs2_reading:
        print(f"   Last Reading:")
        print(f"     • VOC (PPB): {dgs2_reading['ppb']}")
        print(f"     • Temperature: {dgs2_reading['temperature']}°C")
        print(f"     • Humidity: {dgs2_reading['humidity']}%")
    print(f"   Buffer: {dgs2.get_buffer_size()} readings")

    print()


def countdown_timer(duration: int, message: str) -> None:
    """Display a countdown timer"""
    print(f"\n⏳ {message}")
    print("   ", end="", flush=True)

    end_time = time.time() + duration
    while time.time() < end_time:
        remaining = int(end_time - time.time())
        mins, secs = divmod(remaining, 60)
        print(f"\r   {mins:02d}:{secs:02d} remaining", end="", flush=True)
        time.sleep(1)

    print("\r   ✓ Done!          \n")


def main():
    """Main control function"""
    logger.info("🚀 Food Monitoring System Starting...")

    print_separator("🍎 FOOD MONITORING SYSTEM - MASTER CONTROL")

    # Initialize sensors
    print("🔧 Initializing sensors...\n")

    bme688 = BME688Sensor()
    dgs2 = DGS2Sensor()
    calibrator = DataCalibrator(bme688, dgs2)
    anomaly_detector = AnomalyDetector(window_size=10)

    # Start sensors
    print("✓ Starting BME688 Environmental Sensor...")
    bme688.start()

    print("✓ Starting DGS2 VOC Gas Sensor...")
    dgs2.start()

    # Wait for initial connections
    time.sleep(3)

    # Show initial status
    print_separator("📊 INITIAL SENSOR STATUS")
    print_sensor_status(bme688, dgs2)

    # Warmup and baseline collection phase
    print_separator("🔥 WARMUP & BASELINE COLLECTION PHASE")
    print(f"Duration: {WARMUP_DURATION // 60} minutes\n")
    print("During this phase:")
    print("  • Sensors are warming up and stabilizing")
    print("  • Initial readings are being collected")
    print("  • VOC baseline is being established")
    print("  • Data is NOT being logged to CSV yet\n")

    countdown_timer(WARMUP_DURATION, f"Warming up sensors for {WARMUP_DURATION // 60} minutes...")

    # Show status after warmup
    print_separator("📊 STATUS AFTER WARMUP")
    print_sensor_status(bme688, dgs2)
    print(f"✓ VOC Baseline: {calibrator.voc_baseline if calibrator.voc_baseline else 'Calculating...'}\n")

    # Production phase
    print_separator("✅ ENTERING PRODUCTION MODE")
    print("Starting data logging and calibration...\n")
    print("📊 Real-Time Data Updates (every 60 seconds):")
    print("   • Stats update to API every 2 seconds (fresh from in-memory buffer)")
    print("   • Graphs update to API every 5 seconds (fresh from in-memory buffer)")
    print("   • CSV logging every 60 seconds (for permanent records)\n")
    print("Data Storage:")
    print("   ✓ Real-time stats/graphs: IN-MEMORY ONLY (NOT persisted, cleared on restart)")
    print("   ✓ Permanent records: CSV files only\n")

    logger.info("✓ Baseline established, starting data logging")

    minute_count = 0
    anomaly_log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'anomalies.csv')
    
    # Ensure anomaly CSV exists with headers
    try:
        with open(anomaly_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            # Check if file is empty (new file)
            f.seek(0, 2)  # Seek to end
            if f.tell() == 0:  # File is empty
                writer.writerow(['timestamp', 'anomaly_type', 'details', 'temperature', 'humidity', 'pressure', 'voc_ppb', 'overall_aqi'])
    except Exception as e:
        logger.error(f"Error creating anomaly log: {e}")
    
    try:
        while True:
            # Process readings every minute
            start_time = time.time()

            # Wait for minute to complete
            while time.time() - start_time < 60:
                time.sleep(1)

            minute_count += 1

            # Process and log readings
            combined_data = calibrator.process_minute()

            if combined_data:
                # Add timestamp
                combined_data['timestamp'] = datetime.utcnow().isoformat() + 'Z'
                
                # Detect anomalies
                anomalies = anomaly_detector.detect_anomalies(combined_data)
                
                # Log anomalies to CSV (smart logging - only log abnormalities)
                if anomalies:
                    logger.warning(f"🚨 Anomalies detected: {list(anomalies.keys())}")
                    try:
                        with open(anomaly_log_file, 'a', newline='') as f:
                            writer = csv.writer(f)
                            for anomaly_type, details in anomalies.items():
                                writer.writerow([
                                    combined_data.get('timestamp', ''),
                                    anomaly_type,
                                    json.dumps(details),
                                    combined_data.get('temperature', ''),
                                    combined_data.get('humidity', ''),
                                    combined_data.get('pressure', ''),
                                    combined_data.get('voc_ppb', ''),
                                    combined_data.get('overall_aqi', '')
                                ])
                    except Exception as e:
                        logger.error(f"Error logging anomaly: {e}")
                
                # Update in-memory real-time buffer for API
                # This data will be lost on restart - API reads fresh from memory each call
                realtime_data.update_buffer(combined_data)
                
                print(f"[Minute {minute_count}] ", end="")
                if combined_data.get('temperature'):
                    print(f"T={combined_data['temperature']}°C | ", end="")
                if combined_data.get('humidity'):
                    print(f"H={combined_data['humidity']}% | ", end="")
                if combined_data.get('voc_ppb'):
                    print(f"VOC={combined_data['voc_ppb']} ppb | ", end="")
                if combined_data.get('overall_aqi'):
                    print(f"Indoor Air Quality={combined_data['overall_aqi']}", end="")
                if anomalies:
                    print(f" | 🚨 ANOMALIES: {', '.join(anomalies.keys())}", end="")
                print()

    except KeyboardInterrupt:
        print("\n\n⏹️  Shutting down sensors...\n")

        logger.info("Stopping sensors...")
        bme688.stop()
        dgs2.stop()
        
        # Clear in-memory buffers
        realtime_data.clear_buffer()

        print("✓ All sensors stopped")
        print("✓ Data saved to CSV files (permanent logging)")
        print(f"  • bme688_readings.csv")
        print(f"  • dgs2_readings.csv")
        print(f"  • calibrated_readings.csv")
        print("\n✓ Real-time in-memory buffers cleared (not persisted)\n")

        logger.info("✓ System shutdown complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
