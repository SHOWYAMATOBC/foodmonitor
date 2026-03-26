#!/usr/bin/env python3
"""
Data Fusion Module

Combines BME688 and DDS2 sensor data, applies calibration, and provides
clean aggregated output for API consumption.

Output Format:
{
    "timestamp": ISO timestamp,
    "temperature": degrees Celsius,
    "humidity": percentage,
    "pressure": hPa,
    "voc": calibrated PPB,
    "aqi": air quality index (0-500),
    "status": calibration status,
    "data_quality": data availability status
}
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from collections import deque

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('DataFusion')

# Aggregation configuration
AGGREGATION_WINDOW = 60  # seconds
BUFFER_SIZE = 60


class DataFusion:
    """Fuses BME688 and DDS2 sensor data"""

    def __init__(self, bme688_reader=None, dds2_reader=None):
        """
        Initialize data fusion

        Args:
            bme688_reader: BME688Reader instance
            dds2_reader: DDS2Reader instance
        """
        self.bme688_reader = bme688_reader
        self.dds2_reader = dds2_reader

        # Aggregation buffers
        self.combined_buffer = deque(maxlen=BUFFER_SIZE)
        self.last_aggregated_reading = None

    def combine_latest_readings(self) -> Optional[Dict]:
        """
        Combine latest readings from both sensors

        Returns:
            Combined data dictionary or None if insufficient data
        """
        if not self.bme688_reader or not self.dds2_reader:
            logger.error("Sensor readers not initialized")
            return None

        # Get latest from both sensors
        bme688_data = self.bme688_reader.get_latest_reading()
        dds2_data = self.dds2_reader.get_latest_reading()

        # Handle partial data
        if not bme688_data and not dds2_data:
            logger.warning("No data available from either sensor")
            return None

        combined = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'temperature': bme688_data['temperature_c'] if bme688_data else None,
            'humidity': bme688_data['humidity_percent'] if bme688_data else None,
            'pressure': bme688_data['pressure_hpa'] if bme688_data else None,
            'voc': dds2_data['ppb'] if dds2_data else None,
            'aqi': self.bme688_reader.calculate_aqi() if bme688_data else None,
            'calibration_status': {
                'bme688': 'ok' if bme688_data else 'unavailable',
                'dds2_warmup': self.dds2_reader.is_warming_up,
                'dds2_calibrated': self.dds2_reader.is_calibrated(),
                'voc_baseline': round(self.dds2_reader.baseline_ppb, 2) if self.dds2_reader.baseline_ppb else None
            },
            'data_quality': self._assess_data_quality(bme688_data, dds2_data)
        }

        return combined

    def _assess_data_quality(self, bme688_data: Optional[Dict], dds2_data: Optional[Dict]) -> str:
        """
        Assess overall data quality

        Returns:
            'excellent', 'good', 'fair', or 'poor'
        """
        score = 0
        max_score = 4

        if bme688_data:
            score += 2
        if dds2_data:
            score += 2

        if self.dds2_reader and self.dds2_reader.is_calibrated():
            score += 1
        if self.dds2_reader and self.dds2_reader.is_warming_up:
            score -= 1

        if score >= 4:
            return 'excellent'
        elif score >= 3:
            return 'good'
        elif score >= 2:
            return 'fair'
        else:
            return 'poor'

    def get_current_readings(self) -> Optional[Dict]:
        """
        Get clean, calibrated combined readings for API

        Returns:
            Clean reading dictionary or None
        """
        combined = self.combine_latest_readings()

        if not combined:
            return None

        # Return only essential fields for API
        clean_reading = {
            'timestamp': combined['timestamp'],
            'temperature': combined['temperature'],
            'humidity': combined['humidity'],
            'pressure': combined['pressure'],
            'voc': combined['voc'],
            'aqi': combined['aqi'],
            'data_quality': combined['data_quality'],
            'calibrated': combined['calibration_status']['dds2_calibrated']
        }

        self.last_aggregated_reading = clean_reading
        return clean_reading

    def get_aggregated_readings(self, seconds: int = 60) -> Optional[Dict]:
        """
        Get aggregated readings over specified period

        Args:
            seconds: Aggregation window (default 60)

        Returns:
            Aggregated data or None
        """
        if not self.bme688_reader or not self.dds2_reader:
            return None

        # Get averaged data from both sensors
        bme688_avg = self.bme688_reader.get_average_readings(seconds)
        dds2_avg = self.dds2_reader.get_average_readings()

        if not bme688_avg and not dds2_avg:
            return None

        aggregated = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'aggregation_window_seconds': seconds,
            'temperature_avg': bme688_avg['temperature_c'] if bme688_avg else None,
            'humidity_avg': bme688_avg['humidity_percent'] if bme688_avg else None,
            'pressure_avg': bme688_avg['pressure_hpa'] if bme688_avg else None,
            'voc_avg': dds2_avg['ppb_avg'] if dds2_avg else None,
            'voc_max': dds2_avg['ppb_max'] if dds2_avg else None,
            'voc_min': dds2_avg['ppb_min'] if dds2_avg else None,
            'bme688_readings_count': bme688_avg['readings_count'] if bme688_avg else 0,
            'dds2_readings_count': dds2_avg['readings_count'] if dds2_avg else 0
        }

        # Calculate VOC rate of change if we have history
        if len(self.combined_buffer) >= 2:
            latest = self.combined_buffer[-1]
            previous = self.combined_buffer[0]
            if latest.get('voc') and previous.get('voc'):
                time_diff = (
                    datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00')) -
                    datetime.fromisoformat(previous['timestamp'].replace('Z', '+00:00'))
                ).total_seconds()
                if time_diff > 0:
                    aggregated['voc_rate_change_ppb_per_minute'] = round(
                        (latest['voc'] - previous['voc']) / (time_diff / 60), 2
                    )

        return aggregated

    def add_to_buffer(self) -> None:
        """Add current reading to aggregation buffer"""
        reading = self.combine_latest_readings()
        if reading:
            self.combined_buffer.append(reading)

    def get_status_summary(self) -> Dict:
        """Get overall system status"""
        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'bme688': {
                'running': self.bme688_reader.is_running if self.bme688_reader else False,
                'has_data': self.bme688_reader.get_latest_reading() is not None if self.bme688_reader else False,
                'buffer_size': len(self.bme688_reader.buffer) if self.bme688_reader else 0
            },
            'dds2': {
                'running': self.dds2_reader.is_running if self.dds2_reader else False,
                'has_data': self.dds2_reader.get_latest_reading() is not None if self.dds2_reader else False,
                'warming_up': self.dds2_reader.is_warming_up if self.dds2_reader else False,
                'calibrated': self.dds2_reader.is_calibrated() if self.dds2_reader else False,
                'warmup_remaining_seconds': self.dds2_reader.get_warmup_time_remaining() if self.dds2_reader else None,
                'buffer_size': len(self.dds2_reader.buffer) if self.dds2_reader else 0
            },
            'combined_buffer_size': len(self.combined_buffer)
        }

    def get_json_output(self, include_status: bool = True) -> str:
        """
        Get current readings as formatted JSON

        Args:
            include_status: Include system status in output

        Returns:
            JSON string
        """
        reading = self.get_current_readings()

        if not reading:
            return json.dumps({'error': 'No data available'}, indent=2)

        output = {
            'data': reading
        }

        if include_status:
            output['status'] = self.get_status_summary()

        return json.dumps(output, indent=2)

    def save_aggregated_to_csv(self, filename: str = 'combined_data.csv') -> None:
        """
        Save aggregated readings to CSV

        Args:
            filename: Output CSV filename
        """
        try:
            import os
            import csv

            aggregated = self.get_aggregated_readings()
            if not aggregated:
                logger.warning("No aggregated data to save")
                return

            file_exists = os.path.isfile(filename)

            with open(filename, 'a', newline='') as csvfile:
                fieldnames = [
                    'timestamp', 'temperature_avg', 'humidity_avg', 'pressure_avg',
                    'voc_avg', 'voc_max', 'voc_min', 'voc_rate_change_ppb_per_minute',
                    'bme688_readings_count', 'dds2_readings_count'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                # Filter only relevant fields for CSV
                csv_row = {k: v for k, v in aggregated.items() if k in fieldnames}
                writer.writerow(csv_row)

            logger.debug(f"Saved aggregated data to {filename}")

        except Exception as e:
            logger.error(f"Failed to save aggregated data: {e}")


# Example usage
if __name__ == "__main__":
    print("Data Fusion module loaded successfully")
    print("Usage: Import DataFusion and pass BME688Reader and DDS2Reader instances")
