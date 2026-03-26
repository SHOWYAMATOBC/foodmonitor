#!/usr/bin/env python3
"""
Food Monitoring System - Backend Orchestrator

Coordinates BME688 and DDS2 sensors, performs data fusion, and exposes
clean API endpoints for sensor data.

This is the main entry point for the backend system.
"""

import sys
import time
import json
import logging
import threading
import signal
from datetime import datetime
from typing import Dict, Optional

# Import sensor readers and data fusion
from bme688_reader import BME688Reader
from dgs2_reader import DDS2Reader
from data_fusion import DataFusion

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('Main')

# Configuration
AGGREGATION_INTERVAL = 60  # Save aggregated data every 60 seconds
SENSOR_CHECK_TIMEOUT = 5  # Timeout for sensor connection checks (seconds)


# ============================================================================
# SENSOR CONNECTION VALIDATION
# ============================================================================

def check_bme688_connection() -> bool:
    """
    Check if BME688 sensor is connected and responding
    
    Returns:
        bool: True if connected, False otherwise
    """
    try:
        logger.info("Checking BME688 sensor connection...")
        reader = BME688Reader()
        
        # Try to read one sample with timeout
        start_time = time.time()
        reader.start()
        
        # Wait up to SENSOR_CHECK_TIMEOUT seconds for first reading
        while time.time() - start_time < SENSOR_CHECK_TIMEOUT:
            data = reader.get_latest_reading()
            if data:
                logger.info("✅ BME688: Connected")
                reader.stop()
                return True
            time.sleep(0.5)
        
        logger.warning("⚠️  BME688: No response (timeout)")
        reader.stop()
        return False
        
    except Exception as e:
        logger.warning(f"❌ BME688: Not Connected - {str(e)}")
        return False


def check_dds2_connection() -> bool:
    """
    Check if DDS2 sensor is connected and responding
    
    Returns:
        bool: True if connected, False otherwise
    """
    try:
        logger.info("Checking DDS2 sensor connection...")
        reader = DDS2Reader()
        
        # Try to read one sample with timeout
        start_time = time.time()
        reader.start()
        
        # Wait up to SENSOR_CHECK_TIMEOUT seconds for first reading
        while time.time() - start_time < SENSOR_CHECK_TIMEOUT:
            data = reader.get_latest_reading()
            if data:
                logger.info("✅ DDS2: Connected")
                reader.stop()
                return True
            time.sleep(0.5)
        
        logger.warning("⚠️  DDS2: No response (timeout)")
        reader.stop()
        return False
        
    except Exception as e:
        logger.warning(f"❌ DDS2: Not Connected - {str(e)}")
        return False


class SensorSystem:
    """Main sensor system orchestrator"""

    def __init__(self):
        """Initialize sensor system"""
        self.bme688_reader = BME688Reader()
        self.dds2_reader = DDS2Reader()
        self.data_fusion = DataFusion(self.bme688_reader, self.dds2_reader)

        self.is_running = False
        self.aggregation_thread = None
        
        # Connection status flags
        self.bme688_connected = False
        self.dds2_connected = False

    def validate_sensors(self) -> None:
        """Validate sensor connections at startup"""
        logger.info("=" * 60)
        logger.info("VALIDATING SENSOR CONNECTIONS")
        logger.info("=" * 60)
        
        # Check BME688
        self.bme688_connected = check_bme688_connection()
        
        # Check DDS2
        self.dds2_connected = check_dds2_connection()
        
        # Print summary
        logger.info("=" * 60)
        logger.info("SENSOR STATUS SUMMARY")
        logger.info("=" * 60)
        
        if self.bme688_connected:
            logger.info("✅ BME688: Connected and ready")
        else:
            logger.warning("❌ BME688: Not connected - will continue without this sensor")
            
        if self.dds2_connected:
            logger.info("✅ DDS2: Connected and ready")
        else:
            logger.warning("❌ DDS2: Not connected - will continue without this sensor")
        
        # Check if at least one sensor is connected
        if not self.bme688_connected and not self.dds2_connected:
            logger.error("❌ CRITICAL: No sensors connected! System will not function properly.")
            logger.error("Please check sensor connections and try again.")
        
        logger.info("=" * 60)

    def start(self) -> None:
        """Start all available sensors and aggregation loop"""
        logger.info("=" * 60)
        logger.info("FOOD MONITORING SYSTEM - STARTING")
        logger.info("=" * 60)

        # Start BME688 if connected
        if self.bme688_connected:
            logger.info("🚀 Starting BME688 sensor thread...")
            self.bme688_reader.start()
            time.sleep(0.5)
        else:
            logger.warning("⏭️  Skipping BME688 (not connected)")

        # Start DDS2 if connected
        if self.dds2_connected:
            logger.info("🚀 Starting DDS2 sensor thread...")
            self.dds2_reader.start()
            time.sleep(0.5)
        else:
            logger.warning("⏭️  Skipping DDS2 (not connected)")

        self.is_running = True

        # Start aggregation/fusion thread
        logger.info("🚀 Starting data fusion thread...")
        self.aggregation_thread = threading.Thread(
            target=self._aggregation_loop,
            daemon=True,
            name="AggregationThread"
        )
        self.aggregation_thread.start()

        logger.info("✅ All available sensors started successfully")
        logger.info("=" * 60)

    def stop(self) -> None:
        """Stop all sensors"""
        logger.info("=" * 60)
        logger.info("SHUTTING DOWN SENSOR SYSTEM")
        logger.info("=" * 60)

        self.is_running = False

        # Stop DDS2 if it was running
        if self.dds2_connected:
            logger.info("Stopping DDS2 sensor...")
            try:
                self.dds2_reader.stop()
                logger.info("✅ DDS2 stopped")
            except Exception as e:
                logger.error(f"Error stopping DDS2: {e}")

        # Stop BME688 if it was running
        if self.bme688_connected:
            logger.info("Stopping BME688 sensor...")
            try:
                self.bme688_reader.stop()
                logger.info("✅ BME688 stopped")
            except Exception as e:
                logger.error(f"Error stopping BME688: {e}")

        # Wait for aggregation thread
        if self.aggregation_thread:
            self.aggregation_thread.join(timeout=5)
            logger.info("✅ Aggregation thread stopped")

        logger.info("✅ All sensors stopped")
        logger.info("=" * 60)

    def _aggregation_loop(self) -> None:
        """Background thread: periodic aggregation and CSV saving"""
        logger.info("Aggregation loop started")
        
        while self.is_running:
            try:
                # Add current reading to buffer (fusion handles missing data)
                self.data_fusion.add_to_buffer()

                # Save aggregated data periodically
                if self.data_fusion.combined_buffer and len(self.data_fusion.combined_buffer) >= AGGREGATION_INTERVAL:
                    logger.info(f"💾 Saving aggregated data ({len(self.data_fusion.combined_buffer)} readings)...")
                    self.data_fusion.save_aggregated_to_csv()
                    logger.info("✅ Data saved successfully")

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}")
                time.sleep(1)

    def get_current_data(self) -> Optional[Dict]:
        """Get current sensor readings"""
        try:
            return self.data_fusion.get_current_readings()
        except Exception as e:
            logger.error(f"Error getting current data: {e}")
            return None

    def get_aggregated_data(self) -> Optional[Dict]:
        """Get aggregated sensor data"""
        try:
            return self.data_fusion.get_aggregated_readings()
        except Exception as e:
            logger.error(f"Error getting aggregated data: {e}")
            return None

    def get_status(self) -> Dict:
        """Get system status"""
        try:
            return self.data_fusion.get_status_summary()
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {}

    def print_current_readings(self) -> None:
        """Print current readings to console"""
        data = self.get_current_data()

        if data:
            print("\n" + "=" * 60)
            print(f"📊 CURRENT READINGS - {data.get('timestamp', 'N/A')}")
            print("=" * 60)
            
            if data.get('temperature') is not None:
                print(f"🌡️  Temperature:     {data['temperature']}°C")
            else:
                print(f"🌡️  Temperature:     N/A (Sensor not connected)")
                
            if data.get('humidity') is not None:
                print(f"💧 Humidity:        {data['humidity']}%")
            else:
                print(f"💧 Humidity:        N/A (Sensor not connected)")
                
            if data.get('pressure') is not None:
                print(f"🔽 Pressure:        {data['pressure']} hPa")
            else:
                print(f"🔽 Pressure:        N/A (Sensor not connected)")
                
            if data.get('voc') is not None:
                print(f"💨 VOC (PPB):       {data['voc']} ppb")
            else:
                print(f"💨 VOC (PPB):       N/A (Sensor not connected)")
                
            if data.get('aqi') is not None:
                print(f"📈 AQI Score:       {data['aqi']}")
            else:
                print(f"📈 AQI Score:       N/A (Sensor not connected)")
                
            print(f"✓ Data Quality:    {data.get('data_quality', 'N/A')}")
            print(f"✓ Calibrated:      {data.get('calibrated', 'N/A')}")
            print("=" * 60 + "\n")
        else:
            print("⏳ No data available yet (sensors still initializing)...\n")

    def print_status(self) -> None:
        """Print system status"""
        status = self.get_status()

        print("\n" + "=" * 60)
        print("📡 SYSTEM STATUS")
        print("=" * 60)
        print(f"Timestamp: {status.get('timestamp', 'N/A')}")
        
        print("\nBME688:")
        if self.bme688_connected:
            print(f"  ✅ Status:         Connected")
            print(f"  🏃 Running:        {status.get('bme688', {}).get('running', 'N/A')}")
            print(f"  📦 Data:           {status.get('bme688', {}).get('has_data', 'N/A')}")
            print(f"  📊 Buffer Size:    {status.get('bme688', {}).get('buffer_size', 'N/A')}")
        else:
            print(f"  ❌ Status:         Not Connected")

        print("\nDDS2:")
        if self.dds2_connected:
            print(f"  ✅ Status:         Connected")
            print(f"  🏃 Running:        {status.get('dds2', {}).get('running', 'N/A')}")
            print(f"  📦 Data:           {status.get('dds2', {}).get('has_data', 'N/A')}")
            print(f"  🔥 Warming Up:     {status.get('dds2', {}).get('warming_up', 'N/A')}")
            print(f"  ✓ Calibrated:      {status.get('dds2', {}).get('calibrated', 'N/A')}")
            if status.get('dds2', {}).get('warmup_remaining_seconds'):
                mins = status['dds2']['warmup_remaining_seconds'] // 60
                secs = status['dds2']['warmup_remaining_seconds'] % 60
                print(f"  ⏱️  Warmup Remaining: {mins}m {secs}s")
            print(f"  📊 Buffer Size:    {status.get('dds2', {}).get('buffer_size', 'N/A')}")
        else:
            print(f"  ❌ Status:         Not Connected")

        print(f"\n📦 Combined Buffer: {status.get('combined_buffer_size', 0)}")
        print("=" * 60 + "\n")

    def print_json_output(self) -> None:
        """Print current readings as JSON"""
        try:
            json_output = self.data_fusion.get_json_output(include_status=False)
            print("\n" + "=" * 60)
            print("📄 JSON OUTPUT")
            print("=" * 60)
            print(json_output)
            print("=" * 60 + "\n")
        except Exception as e:
            logger.error(f"Error printing JSON output: {e}")
            print(f"Error: {e}\n")

    def interactive_loop(self) -> None:
        """Interactive CLI for monitoring"""
        print("\n" + "=" * 60)
        print("🖥️  FOOD MONITORING SYSTEM - INTERACTIVE MODE")
        print("=" * 60)
        print("\n📋 Available commands:")
        print("  r  - Print current readings")
        print("  s  - Print system status")
        print("  j  - Print JSON output")
        print("  a  - Print aggregated data")
        print("  q  - Quit")
        print("=" * 60 + "\n")

        try:
            while self.is_running:
                try:
                    command = input("Enter command (r/s/j/a/q): ").strip().lower()

                    if command == 'r':
                        self.print_current_readings()
                    elif command == 's':
                        self.print_status()
                    elif command == 'j':
                        self.print_json_output()
                    elif command == 'a':
                        agg_data = self.get_aggregated_data()
                        if agg_data:
                            print("\n" + "=" * 60)
                            print("📈 AGGREGATED DATA")
                            print("=" * 60)
                            print(json.dumps(agg_data, indent=2))
                            print("=" * 60 + "\n")
                        else:
                            print("⏳ No aggregated data available yet\n")
                    elif command == 'q':
                        logger.info("User requested exit")
                        break
                    else:
                        print("❌ Invalid command. Please try again.\n")

                except KeyboardInterrupt:
                    break
                except EOFError:
                    break

        except Exception as e:
            logger.error(f"Error in interactive loop: {e}")

    def run_continuous(self, print_interval: int = 10) -> None:
        """Run continuously with periodic reading printing"""
        logger.info(f"Running in continuous mode (print every {print_interval}s)")

        try:
            count = 0
            while self.is_running:
                count += 1

                if count % print_interval == 0:
                    self.print_current_readings()

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal")
    sys.exit(0)


def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize system
    system = SensorSystem()

    try:
        # STEP 1: Validate sensors before starting
        logger.info("\n" + "🔍 STEP 1: SENSOR VALIDATION" + "\n")
        system.validate_sensors()
        
        time.sleep(1)

        # STEP 2: Start all available sensors
        logger.info("\n" + "⚙️  STEP 2: STARTING SENSORS" + "\n")
        system.start()

        # Wait for sensors to initialize
        logger.info("Waiting for sensors to initialize...")
        time.sleep(3)

        # STEP 3: Print initial status
        logger.info("\n" + "📊 STEP 3: INITIAL STATUS" + "\n")
        system.print_status()
        
        time.sleep(1)

        # STEP 4: Enter interactive mode
        logger.info("\n" + "🎯 STEP 4: ENTERING INTERACTIVE MODE" + "\n")
        system.interactive_loop()

    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
    finally:
        logger.info("\n" + "🛑 STEP 5: SHUTDOWN" + "\n")
        system.stop()
        logger.info("✅ System stopped successfully\n")


if __name__ == "__main__":
    main()
