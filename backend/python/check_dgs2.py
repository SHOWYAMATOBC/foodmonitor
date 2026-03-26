#!/usr/bin/env python3
"""
DDS2-970650 Sensor Connection Check

This script checks if the DDS2-970650 sensor is connected and returns a single reading.
Run this standalone to verify DDS2 connectivity and functionality.

Usage:
    python3 check_dgs2.py
"""

import sys
import time
import logging
from dgs2_reader import DDS2Reader

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('DDS2_Check')

SENSOR_CHECK_TIMEOUT = 15  # Timeout in seconds (DDS2 may take longer to initialize)


def check_dds2_connection() -> bool:
    """
    Check if DDS2 sensor is connected and responding
    
    Returns:
        bool: True if connected and data received, False otherwise
    """
    try:
        logger.info("=" * 60)
        logger.info("🔍 DDS2-970650 SENSOR CONNECTION CHECK")
        logger.info("=" * 60)
        
        logger.info("Initializing DDS2 sensor reader...")
        reader = DDS2Reader()
        
        logger.info("Starting sensor thread...")
        reader.start()
        
        # Wait for a reading with timeout
        logger.info(f"Waiting for sensor reading (timeout: {SENSOR_CHECK_TIMEOUT}s)...")
        logger.info("⏳ DDS2 may require warmup time (up to 15 seconds)...")
        
        start_time = time.time()
        
        while time.time() - start_time < SENSOR_CHECK_TIMEOUT:
            data = reader.get_latest_reading()
            
            if data:
                logger.info("=" * 60)
                logger.info("✅ DDS2-970650 SENSOR: CONNECTED & RESPONDING")
                logger.info("=" * 60)
                
                # Print the reading
                print("\n" + "=" * 60)
                print("📊 DDS2-970650 SENSOR READING")
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
            
            # Print progress every 2 seconds
            elapsed = int(time.time() - start_time)
            if elapsed % 2 == 0 and elapsed > 0:
                remaining = SENSOR_CHECK_TIMEOUT - elapsed
                logger.info(f"⏳ Still waiting... ({remaining}s remaining)")
            
            time.sleep(0.5)
        
        logger.warning("=" * 60)
        logger.warning("⚠️  DDS2-970650 SENSOR: NO RESPONSE (TIMEOUT)")
        logger.warning("=" * 60)
        logger.warning("The sensor did not provide data within the timeout period.")
        logger.warning("Possible issues:")
        logger.warning("  - Sensor not connected to USB/Serial port")
        logger.warning("  - USB driver not installed or recognized")
        logger.warning("  - Serial port permissions issue (try: sudo chmod 666 /dev/ttyUSB*)")
        logger.warning("  - Sensor in sleep mode or not powered")
        logger.warning("  - Warmup timeout (DDS2 may require 15-30 seconds)")
        logger.warning("=" * 60 + "\n")
        
        reader.stop()
        return False
        
    except ImportError as e:
        logger.error("=" * 60)
        logger.error("❌ IMPORT ERROR")
        logger.error("=" * 60)
        logger.error(f"Failed to import DDS2Reader: {str(e)}")
        logger.error("Make sure dgs2_reader.py exists in the same directory")
        logger.error("=" * 60 + "\n")
        return False
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("❌ DDS2-970650 SENSOR: NOT CONNECTED")
        logger.error("=" * 60)
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 60 + "\n")
        return False


def main():
    """Main entry point"""
    try:
        result = check_dds2_connection()
        
        if result:
            logger.info("✅ DDS2-970650 is working correctly!")
            sys.exit(0)
        else:
            logger.error("❌ DDS2-970650 check failed. Please verify hardware connections.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⚠️  Check interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
