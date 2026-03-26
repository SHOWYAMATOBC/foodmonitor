#!/usr/bin/env python3
"""
Data Calibrator and Fusion Module
Combines BME688 and DGS2 sensor data with calibration
Produces averaged readings every minute with AQI calculation

⚠️  IMPORTANT: 
The AQI calculated here is based on VOC (gas resistance + volatile organic compounds) 
and is NOT the official EPA Air Quality Index, which is based on PM2.5, PM10, NO2, SO2, CO, O3.

Our "AQI" represents local air quality relative to pollutants detected by gas sensors,
useful for indoor air quality monitoring but not directly comparable to outdoor AQI readings.

ADAPTIVE SAMPLING STRATEGY:
- Normal: 1 reading per minute
- Anomaly Detected: Switches to 1 reading per 30 seconds
- Behavior: Detects sudden VOC spikes, resistance drops, humidity jumps
"""

import os
import csv
import time
import logging
import numpy as np
from datetime import datetime
from collections import deque
from typing import Dict, Optional, List

# Configuration
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALIBRATION_CSV_FILENAME = os.path.join(BASE_DIR, 'data', 'calibrated_readings.csv')
BASELINE_PICKLE_FILE = 'voc_baseline.txt'
BUFFER_DURATION = 60  # seconds

# Adaptive Sampling Configuration
NORMAL_SAMPLING_INTERVAL = 60  # seconds
ANOMALY_SAMPLING_INTERVAL = 30  # seconds
ANOMALY_DURATION = 300  # Stay in anomaly mode for 5 minutes
VOC_SPIKE_THRESHOLD = 50  # ppb increase in 1 minute = anomaly
RESISTANCE_DROP_THRESHOLD = 15000  # Ohm drop in 1 minute = anomaly
HUMIDITY_SPIKE_THRESHOLD = 10  # % increase in 1 minute = anomaly

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] Calibrator - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('Calibrator')


class AnomalyDetector:
    """Detects abnormal sensor behavior for adaptive sampling"""
    
    def __init__(self):
        """Initialize anomaly detector"""
        self.voc_history = deque(maxlen=10)  # Last 10 VOC readings
        self.resistance_history = deque(maxlen=10)
        self.humidity_history = deque(maxlen=10)
        self.anomaly_detected = False
        self.anomaly_start_time = None
        self.in_anomaly_mode = False
    
    def detect_anomaly(self, current_reading: Dict) -> bool:
        """
        Detect abnormal behavior in sensor readings
        
        Returns:
            True if anomaly detected, False otherwise
        """
        try:
            voc = current_reading.get('voc_ppb')
            resistance = current_reading.get('gas_resistance')
            humidity = current_reading.get('humidity')
            
            # Add to history
            if voc is not None and voc > 0:
                self.voc_history.append(voc)
            if resistance is not None and resistance > 0:
                self.resistance_history.append(resistance)
            if humidity is not None:
                self.humidity_history.append(humidity)
            
            # Need at least 2 readings to detect change
            if len(self.voc_history) < 2:
                return False
            
            anomaly_detected = False
            reasons = []
            
            # Check VOC spike
            if len(self.voc_history) >= 2:
                voc_change = self.voc_history[-1] - self.voc_history[-2]
                if voc_change > VOC_SPIKE_THRESHOLD:
                    anomaly_detected = True
                    reasons.append(f"VOC spike: +{voc_change:.1f} ppb")
            
            # Check resistance drop
            if len(self.resistance_history) >= 2:
                resistance_change = self.resistance_history[-2] - self.resistance_history[-1]
                if resistance_change > RESISTANCE_DROP_THRESHOLD:
                    anomaly_detected = True
                    reasons.append(f"Resistance drop: -{resistance_change:.0f} Ω")
            
            # Check humidity spike
            if len(self.humidity_history) >= 2:
                humidity_change = abs(self.humidity_history[-1] - self.humidity_history[-2])
                if humidity_change > HUMIDITY_SPIKE_THRESHOLD:
                    anomaly_detected = True
                    reasons.append(f"Humidity jump: ±{humidity_change:.1f}%")
            
            # State transition logic
            if anomaly_detected and not self.in_anomaly_mode:
                self.anomaly_start_time = datetime.utcnow()
                self.in_anomaly_mode = True
                logger.warning(f"🚨 ANOMALY DETECTED - Switching to high-frequency sampling: {', '.join(reasons)}")
            
            elif self.in_anomaly_mode:
                # Check if we should exit anomaly mode
                elapsed = (datetime.utcnow() - self.anomaly_start_time).total_seconds()
                if elapsed > ANOMALY_DURATION:
                    self.in_anomaly_mode = False
                    logger.info("✓ Anomaly period ended - returning to normal sampling")
            
            return self.in_anomaly_mode
            
        except Exception as e:
            logger.warning(f"Error in anomaly detection: {e}")
            return False
    
    def get_sampling_interval(self) -> int:
        """Get current sampling interval based on anomaly state"""
        return ANOMALY_SAMPLING_INTERVAL if self.in_anomaly_mode else NORMAL_SAMPLING_INTERVAL
    
    def get_status(self) -> str:
        """Get anomaly detector status"""
        if self.in_anomaly_mode:
            elapsed = (datetime.utcnow() - self.anomaly_start_time).total_seconds()
            remaining = max(0, ANOMALY_DURATION - elapsed)
            return f"🚨 HIGH-FREQ MODE ({int(remaining)}s remaining)"
        return "✓ Normal sampling"


class DataCalibrator:
    """Combines and calibrates sensor data with adaptive sampling and exception handling"""

    def __init__(self, bme688_sensor=None, dgs2_sensor=None):
        """Initialize data calibrator with exception handling"""
        try:
            self.bme688_sensor = bme688_sensor
            self.dgs2_sensor = dgs2_sensor
            
            # Sensor status tracking
            self.bme688_started = False
            self.dgs2_started = False
            self.bme688_failed = False
            self.dgs2_failed = False
            self.startup_time = datetime.utcnow()

            # VOC Calibration
            self.voc_baseline = self._load_baseline()
            self.baseline_samples = deque(maxlen=12)  # 60 seconds of samples
            self.calibration_complete = False
            self.calibration_start_time = None
            
            # Adaptive Sampling
            self.anomaly_detector = AnomalyDetector()
            self.last_high_freq_save_time = None
            
            # Validate sensor connections
            self._validate_sensors()
            
        except Exception as e:
            logger.error(f"❌ Fatal error in calibrator initialization: {e}")
            raise

    def _validate_sensors(self) -> None:
        """Validate that sensors are properly initialized"""
        try:
            if self.bme688_sensor is None:
                logger.warning("⚠️  BME688 sensor not provided")
            else:
                if hasattr(self.bme688_sensor, 'is_running'):
                    self.bme688_started = True
                    logger.info("✓ BME688 sensor initialized")
                else:
                    logger.warning("⚠️  BME688 sensor missing required attributes")
            
            if self.dgs2_sensor is None:
                logger.warning("⚠️  DGS2 sensor not provided")
            else:
                if hasattr(self.dgs2_sensor, 'is_running'):
                    self.dgs2_started = True
                    logger.info("✓ DGS2 sensor initialized")
                else:
                    logger.warning("⚠️  DGS2 sensor missing required attributes")
            
            if not self.bme688_started and not self.dgs2_started:
                logger.error("❌ No sensors initialized - system cannot function")
                
        except Exception as e:
            logger.error(f"Error validating sensors: {e}")

    def _load_baseline(self) -> Optional[float]:
        """Load VOC baseline from persistent storage"""
        try:
            if os.path.exists(BASELINE_PICKLE_FILE):
                with open(BASELINE_PICKLE_FILE, 'r') as f:
                    baseline = float(f.read().strip())
                    logger.info(f"✓ Loaded VOC baseline: {baseline:.2f} ppb")
                    return baseline
        except Exception as e:
            logger.warning(f"Could not load baseline: {e}")
        return None

    def _save_baseline(self, baseline: float) -> None:
        """Save VOC baseline to persistent storage"""
        try:
            with open(BASELINE_PICKLE_FILE, 'w') as f:
                f.write(str(baseline))
            logger.info(f"✓ Saved VOC baseline: {baseline:.2f} ppb")
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")

    def get_gas_resistance_aqi(self, gas_resistance: float) -> Optional[float]:
        """
        Calculate air quality index from gas resistance (BME688)
        
        BME688 gas sensor detects VOCs, but resistance doesn't directly map to AQI.
        This uses a more realistic mapping:
        - Higher resistance = cleaner air (lower pollution)
        - Lower resistance = more VOCs detected (higher pollution)
        
        Baseline: ~100-200 Ohms for clean air on BME688
        """
        if gas_resistance <= 0:
            return None

        # Use a more realistic baseline for BME688
        # In clean air, typical readings are 100-200 kohms
        # As air gets dirtier, resistance drops (more conductive pollutants)
        CLEAN_AIR_BASELINE = 100000  # 100 kohms - typical clean air reading
        
        # If first reading is much higher than baseline, use it as reference
        if not hasattr(self, '_gas_baseline'):
            # Initialize with current reading as reference
            self._gas_baseline = max(gas_resistance, CLEAN_AIR_BASELINE)
            logger.debug(f"Initialized gas baseline: {self._gas_baseline} Ω")

        # Calculate ratio: baseline / current
        # Ratio > 1 means gas_resistance dropped (more pollution)
        # Ratio = 1 means no change
        ratio = self._gas_baseline / gas_resistance

        # Map to a more realistic AQI scale (0-500)
        # Exponential mapping to handle wide range of resistance values
        if ratio <= 0.5:
            aqi = 0  # Very clean (very high resistance)
        elif ratio <= 1:
            aqi = ratio * 100  # 0-100 (clean to moderate)
        elif ratio <= 2:
            aqi = 100 + (ratio - 1) * 100  # 100-200 (moderate to unhealthy)
        else:
            aqi = 200 + min(300, (ratio - 2) * 150)  # 200-500 (unhealthy+)

        return round(min(500, max(0, aqi)), 2)


    def get_voc_ppb_aqi(self, ppb: float) -> Optional[float]:
        """
        Calculate AQI from VOC PPB (DGS2 sensor)
        
        Real-world VOC levels:
        - Indoor baseline: 300-500 ppb (normal)
        - Outdoor: 50-200 ppb
        - After cooking/smoking: 800-1500 ppb
        
        Mapping to AQI (0-500):
        0-50 ppb: Good (0-50 AQI)
        50-200 ppb: Moderate (50-150 AQI)
        200-500 ppb: Unhealthy (150-300 AQI)
        500+ ppb: Very Unhealthy (300-500 AQI)
        """
        if ppb is None or ppb < 0:
            return None

        # More realistic and conservative mapping
        if ppb <= 50:
            # Outdoor/very clean
            aqi = (ppb / 50) * 50
        elif ppb <= 200:
            # Normal indoor conditions
            aqi = 50 + ((ppb - 50) / 150) * 100
        elif ppb <= 500:
            # Elevated VOC (cooking, ventilation issues)
            aqi = 150 + ((ppb - 200) / 300) * 150
        else:
            # High VOC (smoking, chemicals)
            aqi = 300 + min(200, ((ppb - 500) / 500) * 200)

        return round(min(500, max(0, aqi)), 2)

    def combine_readings(self, bme688_reading: Optional[Dict], dgs2_reading: Optional[Dict]) -> Optional[Dict]:
        """Combine readings from both sensors with exception handling"""
        try:
            if not bme688_reading and not dgs2_reading:
                logger.warning("⚠️  No readings available from either sensor")
                return None

            combined = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'temperature': None,
                'humidity': None,
                'pressure': None,
                'gas_resistance': None,
                'voc_ppb': None,
                'data_sources': {
                    'bme688': bme688_reading is not None,
                    'dgs2': dgs2_reading is not None
                },
                'data_quality': 'degraded'
            }

            # Extract BME688 data with error handling
            if bme688_reading:
                try:
                    combined['temperature'] = bme688_reading.get('temperature_c')
                    combined['humidity'] = bme688_reading.get('humidity_percent')
                    combined['pressure'] = bme688_reading.get('pressure_hpa')
                    combined['gas_resistance'] = bme688_reading.get('gas_resistance_ohm')
                except Exception as e:
                    logger.warning(f"⚠️  Error extracting BME688 data: {e}")
                    self.bme688_failed = True
            else:
                # Fallback to DGS2 for temperature/humidity if BME688 unavailable
                if dgs2_reading:
                    combined['temperature'] = dgs2_reading.get('temperature')
                    combined['humidity'] = dgs2_reading.get('humidity')

            # Extract DGS2 data with error handling
            if dgs2_reading:
                try:
                    combined['voc_ppb'] = dgs2_reading.get('ppb')
                except Exception as e:
                    logger.warning(f"⚠️  Error extracting DGS2 data: {e}")
                    self.dgs2_failed = True

            # Average temperature and humidity if both available
            if bme688_reading and dgs2_reading:
                try:
                    temp_bme = bme688_reading.get('temperature_c')
                    temp_dgs2 = dgs2_reading.get('temperature')
                    if temp_bme is not None and temp_dgs2 is not None:
                        combined['temperature'] = round((temp_bme + temp_dgs2) / 2, 2)
                    
                    hum_bme = bme688_reading.get('humidity_percent')
                    hum_dgs2 = dgs2_reading.get('humidity')
                    if hum_bme is not None and hum_dgs2 is not None:
                        combined['humidity'] = round((hum_bme + hum_dgs2) / 2, 2)
                    
                    combined['data_quality'] = 'excellent'  # Both sensors working
                except Exception as e:
                    logger.warning(f"⚠️  Error averaging sensor data: {e}")
            elif bme688_reading and not dgs2_reading:
                combined['data_quality'] = 'good'  # BME688 working
            elif dgs2_reading and not bme688_reading:
                combined['data_quality'] = 'good'  # DGS2 working

            # Calculate AQI values with exception handling
            if combined['gas_resistance']:
                try:
                    combined['gas_aqi'] = self.get_gas_resistance_aqi(combined['gas_resistance'])
                except Exception as e:
                    logger.warning(f"⚠️  Error calculating gas AQI: {e}")
                    
            if combined['voc_ppb']:
                try:
                    combined['voc_aqi'] = self.get_voc_ppb_aqi(combined['voc_ppb'])
                except Exception as e:
                    logger.warning(f"⚠️  Error calculating VOC AQI: {e}")

            # Overall AQI (average of available AQI values)
            aqi_values = []
            if combined.get('gas_aqi'):
                aqi_values.append(combined['gas_aqi'])
            if combined.get('voc_aqi'):
                aqi_values.append(combined['voc_aqi'])

            if aqi_values:
                combined['overall_aqi'] = round(sum(aqi_values) / len(aqi_values), 2)

            # Detect anomalies for adaptive sampling
            try:
                combined['is_anomaly'] = self.anomaly_detector.detect_anomaly(combined)
                combined['sampling_mode'] = "HIGH-FREQ" if combined['is_anomaly'] else "NORMAL"
            except Exception as e:
                logger.warning(f"⚠️  Error in anomaly detection: {e}")
                combined['sampling_mode'] = "NORMAL"

            return combined
            
        except Exception as e:
            logger.error(f"❌ Critical error in combine_readings: {e}")
            return None


    def calibrate_voc_baseline(self, ppb: float) -> None:
        """Collect samples for VOC baseline calibration"""
        if ppb is not None:
            self.baseline_samples.append(ppb)

            if len(self.baseline_samples) >= 12:  # 60 seconds of data
                self.voc_baseline = sum(self.baseline_samples) / len(self.baseline_samples)
                self._save_baseline(self.voc_baseline)
                self.calibration_complete = True
                logger.info(f"✓ VOC baseline calibration complete: {self.voc_baseline:.2f} ppb")

    def apply_voc_calibration(self, ppb: float) -> float:
        """Apply VOC calibration formula"""
        if self.voc_baseline is None:
            return ppb

        # Return the difference from baseline
        return abs(ppb - self.voc_baseline)

    def log_to_csv(self, data: Dict, is_high_frequency: bool = False) -> bool:
        """
        Log calibrated data to CSV file with exception handling
        
        Args:
            data: Data to log
            is_high_frequency: If True, use high-frequency CSV
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if is_high_frequency:
                filename = os.path.join(BASE_DIR, 'data', 'calibrated_readings_high_freq.csv')
            else:
                filename = CALIBRATION_CSV_FILENAME
                
            file_exists = os.path.isfile(filename)

            with open(filename, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'temperature', 'humidity', 'pressure', 'voc_ppb', 
                             'gas_aqi', 'voc_aqi', 'overall_aqi', 'sampling_mode', 'data_quality']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                csv_data = {k: data.get(k) for k in fieldnames}
                writer.writerow(csv_data)

            if not is_high_frequency:
                logger.info(
                    f"📊 Calibrated reading saved: "
                    f"T={data.get('temperature')}°C, "
                    f"H={data.get('humidity')}%, "
                    f"VOC={data.get('voc_ppb')}ppb, "
                    f"AQI={data.get('overall_aqi')} [{data.get('data_quality')}]"
                )
            
            return True
            
        except IOError as e:
            logger.error(f"❌ File I/O error writing to CSV: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error logging to CSV: {e}")
            return False

    def process_minute(self) -> Optional[Dict]:
        """
        Process and combine data from the last minute with exception handling
        """
        try:
            bme688_reading = None
            dgs2_reading = None

            # Get readings with error handling
            try:
                if self.bme688_sensor and not self.bme688_failed:
                    bme688_reading = self.bme688_sensor.get_average_reading()
                    if bme688_reading is None:
                        logger.warning("⚠️  BME688 returned None - sensor may have failed")
            except AttributeError:
                logger.error("❌ BME688 sensor missing get_average_reading() method")
                self.bme688_failed = True
            except Exception as e:
                logger.error(f"❌ Error reading BME688: {e}")
                self.bme688_failed = True

            try:
                if self.dgs2_sensor and not self.dgs2_failed:
                    dgs2_reading = self.dgs2_sensor.get_average_reading()
                    if dgs2_reading is None:
                        logger.warning("⚠️  DGS2 returned None - sensor may have failed")
            except AttributeError:
                logger.error("❌ DGS2 sensor missing get_average_reading() method")
                self.dgs2_failed = True
            except Exception as e:
                logger.error(f"❌ Error reading DGS2: {e}")
                self.dgs2_failed = True

            if not bme688_reading and not dgs2_reading:
                logger.warning("❌ No readings from either sensor - check sensor status")
                return None

            combined = self.combine_readings(bme688_reading, dgs2_reading)

            if combined:
                # Calibrate VOC if we're in calibration phase
                if not self.calibration_complete and dgs2_reading:
                    try:
                        self.calibrate_voc_baseline(dgs2_reading['ppb'])
                    except Exception as e:
                        logger.warning(f"⚠️  Error during VOC calibration: {e}")

                # Apply calibration if available
                if combined['voc_ppb'] and self.calibration_complete:
                    try:
                        combined['voc_ppb_calibrated'] = self.apply_voc_calibration(combined['voc_ppb'])
                    except Exception as e:
                        logger.warning(f"⚠️  Error applying VOC calibration: {e}")

                # Log to CSV
                self.log_to_csv(combined, is_high_frequency=False)
            
            return combined
            
        except Exception as e:
            logger.error(f"❌ Critical error in process_minute: {e}")
            return None
    
    def process_high_frequency_reading(self, current_reading: Dict) -> bool:
        """
        Process high-frequency reading during anomaly mode
        
        Args:
            current_reading: Current sensor reading
            
        Returns:
            True if logged successfully
        """
        try:
            if current_reading and self.anomaly_detector.in_anomaly_mode:
                return self.log_to_csv(current_reading, is_high_frequency=True)
            return False
        except Exception as e:
            logger.error(f"❌ Error processing high-frequency reading: {e}")
            return False
    
    def get_system_health(self) -> Dict:
        """Get overall system health status"""
        try:
            health = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'uptime_seconds': (datetime.utcnow() - self.startup_time).total_seconds(),
                'bme688': {
                    'initialized': self.bme688_started,
                    'failed': self.bme688_failed,
                    'status': 'OPERATIONAL' if (self.bme688_started and not self.bme688_failed) else 'FAILED' if self.bme688_failed else 'NOT INITIALIZED'
                },
                'dgs2': {
                    'initialized': self.dgs2_started,
                    'failed': self.dgs2_failed,
                    'status': 'OPERATIONAL' if (self.dgs2_started and not self.dgs2_failed) else 'FAILED' if self.dgs2_failed else 'NOT INITIALIZED'
                },
                'calibration': {
                    'complete': self.calibration_complete,
                    'baseline_ppb': round(self.voc_baseline, 2) if self.voc_baseline else None
                },
                'sampling': {
                    'mode': self.anomaly_detector.get_status(),
                    'interval_seconds': self.anomaly_detector.get_sampling_interval()
                }
            }
            return health
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {'error': str(e)}

    def print_status(self) -> None:
        """Print calibration status with health information"""
        try:
            health = self.get_system_health()
            
            print("\n" + "=" * 70)
            print("📊 CALIBRATOR STATUS & SYSTEM HEALTH")
            print("=" * 70)
            
            print(f"\n⏱️  Uptime: {int(health['uptime_seconds'])} seconds")
            
            # BME688 Status
            bme_status = health['bme688']
            bme_icon = "✓" if bme_status['status'] == 'OPERATIONAL' else "⚠️ " if bme_status['status'] == 'FAILED' else "○"
            print(f"\n🌡️  BME688 Environmental Sensor:")
            print(f"   Status: {bme_icon} {bme_status['status']}")
            
            if self.bme688_sensor and not self.bme688_failed:
                bme_latest = self.bme688_sensor.get_latest_reading()
                if bme_latest:
                    print(f"   Buffer Size: {self.bme688_sensor.get_buffer_size()} readings")
                    print(f"   Last Reading:")
                    print(f"     • Temperature: {bme_latest['temperature_c']}°C")
                    print(f"     • Humidity: {bme_latest['humidity_percent']}%")
                    print(f"     • Pressure: {bme_latest['pressure_hpa']} hPa")
                    print(f"     • Gas Resistance: {bme_latest['gas_resistance_ohm']:.0f} Ω")

            # DGS2 Status
            dgs2_status = health['dgs2']
            dgs2_icon = "✓" if dgs2_status['status'] == 'OPERATIONAL' else "⚠️ " if dgs2_status['status'] == 'FAILED' else "○"
            print(f"\n💨 DGS2 VOC Sensor:")
            print(f"   Status: {dgs2_icon} {dgs2_status['status']}")
            
            if self.dgs2_sensor and not self.dgs2_failed:
                dgs2_latest = self.dgs2_sensor.get_latest_reading()
                if dgs2_latest:
                    print(f"   Buffer Size: {self.dgs2_sensor.get_buffer_size()} readings")
                    print(f"   Last Reading:")
                    print(f"     • VOC: {dgs2_latest['ppb']} ppb")
                    print(f"     • Temperature: {dgs2_latest['temperature']}°C")
                    print(f"     • Humidity: {dgs2_latest['humidity']}%")

            # Calibration Status
            cal = health['calibration']
            cal_icon = "✓" if cal['complete'] else "⏳"
            print(f"\n🔧 VOC Calibration: {cal_icon} {'Complete' if cal['complete'] else 'In Progress'}")
            if cal['baseline_ppb'] is not None:
                print(f"   Baseline: {cal['baseline_ppb']} ppb")

            # Sampling Mode
            sampling = health['sampling']
            print(f"\n⚡ Sampling Mode: {sampling['mode']}")
            print(f"   Interval: {sampling['interval_seconds']} seconds")
            
            print("\n" + "=" * 70 + "\n")
            
        except Exception as e:
            logger.error(f"Error printing status: {e}")

