#!/usr/bin/env python3
"""
BME688 Sensor Connection Check

This script checks if the BME688 sensor is connected and returns a single reading.
Run this standalone to verify BME688 connectivity and functionality.

Usage:
    python3 check_bme688.py
"""

import sys
import time
import logging
from bme688_reader import BME688Reader

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('BME688_Check')

SENSOR_CHECK_TIMEOUT = 10  # Timeout in seconds


def check_bme688_connection() -> bool:
    """
    Check if BME688 sensor is connected and responding
    
    Returns:
        bool: True if connected and data received, False otherwise
    """
    try:
        logger.info("=" * 60)
        logger.info("🔍 BME688 SENSOR CONNECTION CHECK")
        logger.info("=" * 60)
        
        logger.info("Initializing BME688 sensor reader...")
        reader = BME688Reader()
        
        logger.info("Starting sensor thread...")
        reader.start()
        
        # Wait for a reading with timeout
        logger.info(f"Waiting for sensor reading (timeout: {SENSOR_CHECK_TIMEOUT}s)...")
        start_time = time.time()
        
        while time.time() - start_time < SENSOR_CHECK_TIMEOUT:
            data = reader.get_latest_reading()
            
            if data:
                logger.info("=" * 60)
                logger.info("✅ BME688 SENSOR: CONNECTED & RESPONDING")
                logger.info("=" * 60)
                
                # Print the reading
                print("\n" + "=" * 60)
                print("📊 BME688 SENSOR READING")
                print("=" * 60)
                
                if isinstance(data, dict):
                    for key, value in data.items():
                        print(f"  {key}: {value}")
                else:
                    print(f"  Raw Data: {data}")
                
                print("=" * 60 + "\n")
                
                reader.stop()
                logger.info("✅ Check completed successfully")
                logger.info("=" * 60 + "\n")
                return True
            
            time.sleep(0.5)
        
        logger.warning("=" * 60)
        logger.warning("⚠️  BME688 SENSOR: NO RESPONSE (TIMEOUT)")
        logger.warning("=" * 60)
        logger.warning("The sensor did not provide data within the timeout period.")
        logger.warning("Possible issues:")
        logger.warning("  - Sensor not connected to GPIO/I2C")
        logger.warning("  - I2C bus not enabled on Raspberry Pi")
        logger.warning("  - Power supply issue")
        logger.warning("  - Sensor hardware failure")
        logger.warning("=" * 60 + "\n")
        
        reader.stop()
        return False
        
    except ImportError as e:
        logger.error("=" * 60)
        logger.error("❌ IMPORT ERROR")
        logger.error("=" * 60)
        logger.error(f"Failed to import BME688Reader: {str(e)}")
        logger.error("Make sure bme688_reader.py exists in the same directory")
        logger.error("=" * 60 + "\n")
        return False
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ BME688 SENSOR: NOT CONNECTED")
        logger.error("=" * 60)
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 60 + "\n")
        return False


def main():
    """Main entry point"""
    try:
        result = check_bme688_connection()
        
        if result:
            logger.info("✅ BME688 is working correctly!")
            sys.exit(0)
        else:
            logger.error("❌ BME688 check failed. Please verify hardware connections.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⚠️  Check interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
