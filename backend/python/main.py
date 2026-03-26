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

# Import sensor readers and data fusion
from bme688_reader import BME688Reader
from backend.python.dgs2_reader import DDS2Reader
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


class SensorSystem:
    """Main sensor system orchestrator"""

    def __init__(self):
        """Initialize sensor system"""
        self.bme688_reader = BME688Reader()
        self.dds2_reader = DDS2Reader()
        self.data_fusion = DataFusion(self.bme688_reader, self.dds2_reader)

        self.is_running = False
        self.aggregation_thread = None

    def start(self) -> None:
        """Start all sensors and aggregation loop"""
        logger.info("=" * 60)
        logger.info("FOOD MONITORING SYSTEM - STARTING")
        logger.info("=" * 60)

        # Start sensors
        logger.info("Starting BME688 sensor...")
        self.bme688_reader.start()

        logger.info("Starting DDS2 sensor...")
        self.dds2_reader.start()

        self.is_running = True

        # Start aggregation thread
        self.aggregation_thread = threading.Thread(
            target=self._aggregation_loop,
            daemon=True
        )
        self.aggregation_thread.start()

        logger.info("All sensors started successfully")
        logger.info("=" * 60)

    def stop(self) -> None:
        """Stop all sensors"""
        logger.info("=" * 60)
        logger.info("SHUTTING DOWN SENSOR SYSTEM")
        logger.info("=" * 60)

        self.is_running = False

        logger.info("Stopping DDS2 sensor...")
        self.dds2_reader.stop()

        logger.info("Stopping BME688 sensor...")
        self.bme688_reader.stop()

        if self.aggregation_thread:
            self.aggregation_thread.join(timeout=5)

        logger.info("All sensors stopped")
        logger.info("=" * 60)

    def _aggregation_loop(self) -> None:
        """Background thread: periodic aggregation and CSV saving"""
        while self.is_running:
            try:
                # Add current reading to buffer
                self.data_fusion.add_to_buffer()

                # Save aggregated data periodically
                if self.data_fusion.combined_buffer and len(self.data_fusion.combined_buffer) >= AGGREGATION_INTERVAL:
                    logger.info("Saving aggregated data...")
                    self.data_fusion.save_aggregated_to_csv()

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error in aggregation loop: {e}")
                time.sleep(1)

    def get_current_data(self) -> Dict:
        """Get current sensor readings"""
        return self.data_fusion.get_current_readings()

    def get_aggregated_data(self) -> Dict:
        """Get aggregated sensor data"""
        return self.data_fusion.get_aggregated_readings()

    def get_status(self) -> Dict:
        """Get system status"""
        return self.data_fusion.get_status_summary()

    def print_current_readings(self) -> None:
        """Print current readings to console"""
        data = self.get_current_data()

        if data:
            print("\n" + "=" * 60)
            print(f"CURRENT READINGS - {data['timestamp']}")
            print("=" * 60)
            print(f"Temperature:     {data['temperature']}°C")
            print(f"Humidity:        {data['humidity']}%")
            print(f"Pressure:        {data['pressure']} hPa")
            print(f"VOC (PPB):       {data['voc']} ppb")
            print(f"AQI Score:       {data['aqi']}")
            print(f"Data Quality:    {data['data_quality']}")
            print(f"Calibrated:      {data['calibrated']}")
            print("=" * 60 + "\n")
        else:
            print("No data available yet...")

    def print_status(self) -> None:
        """Print system status"""
        status = self.get_status()

        print("\n" + "=" * 60)
        print("SYSTEM STATUS")
        print("=" * 60)
        print(f"Timestamp: {status['timestamp']}")
        print("\nBME688:")
        print(f"  Running:       {status['bme688']['running']}")
        print(f"  Data:          {status['bme688']['has_data']}")
        print(f"  Buffer Size:   {status['bme688']['buffer_size']}")

        print("\nDDS2:")
        print(f"  Running:       {status['dds2']['running']}")
        print(f"  Data:          {status['dds2']['has_data']}")
        print(f"  Warming Up:    {status['dds2']['warming_up']}")
        print(f"  Calibrated:    {status['dds2']['calibrated']}")
        if status['dds2']['warmup_remaining_seconds']:
            mins = status['dds2']['warmup_remaining_seconds'] // 60
            secs = status['dds2']['warmup_remaining_seconds'] % 60
            print(f"  Warmup Remaining: {mins}m {secs}s")
        print(f"  Buffer Size:   {status['dds2']['buffer_size']}")

        print(f"\nCombined Buffer: {status['combined_buffer_size']}")
        print("=" * 60 + "\n")

    def print_json_output(self) -> None:
        """Print current readings as JSON"""
        json_output = self.data_fusion.get_json_output(include_status=False)
        print("\n" + "=" * 60)
        print("JSON OUTPUT")
        print("=" * 60)
        print(json_output)
        print("=" * 60 + "\n")

    def interactive_loop(self) -> None:
        """Interactive CLI for monitoring"""
        print("\n" + "=" * 60)
        print("FOOD MONITORING SYSTEM - INTERACTIVE MODE")
        print("=" * 60)
        print("\nAvailable commands:")
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
                            print("AGGREGATED DATA")
                            print("=" * 60)
                            print(json.dumps(agg_data, indent=2))
                            print("=" * 60 + "\n")
                        else:
                            print("No aggregated data available yet\n")
                    elif command == 'q':
                        break
                    else:
                        print("Invalid command\n")

                except KeyboardInterrupt:
                    break
                except EOFError:
                    break

        except Exception as e:
            logger.error(f"Error in interactive loop: {e}")

    def run_continuous(self, print_interval: int = 10) -> None:
        """Run continuously with periodic status printing"""
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
        # Start all sensors
        system.start()

        # Wait for sensors to start
        time.sleep(2)

        # Print initial status
        system.print_status()

        # Run interactive mode
        system.interactive_loop()

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        system.stop()


if __name__ == "__main__":
    main()
