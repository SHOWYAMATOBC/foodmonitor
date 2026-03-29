#!/usr/bin/env python3
"""HTTP Polling API Server - CSV-backed sensor endpoints"""

import logging
import csv
import os
from flask import Flask, jsonify
from flask_cors import CORS

API_HOST = '0.0.0.0'
API_PORT = 5000

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CSV_FILES = {
    'bme688_log': os.path.join(DATA_DIR, 'bme688_readings.csv'),
    'dgs2_log': os.path.join(DATA_DIR, 'dgs2_readings.csv'),
    'anomaly_log': os.path.join(DATA_DIR, 'anomalies.csv'),
    'combined_log': os.path.join(DATA_DIR, 'calibrated_readings.csv')
}

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('API')

app = Flask(__name__)
CORS(app)


def _combined_csv_path() -> str:
    """Return combined CSV path, supporting combined.csv if present."""
    preferred = os.path.join(DATA_DIR, 'combined.csv')
    if os.path.exists(preferred):
        return preferred
    return CSV_FILES['combined_log']


def _read_csv_rows(path: str):
    """Read CSV rows as list[dict]."""
    if not os.path.exists(path):
        return []

    try:
        with open(path, 'r', newline='', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            return list(reader)
    except Exception as e:
        logger.error(f"Failed reading CSV {path}: {e}")
        return []


def _metric_response(metric_name: str, source_column: str):
    """Build standardized metric response from combined CSV rows."""
    rows = _read_csv_rows(_combined_csv_path())

    metric_rows = []
    for row in rows:
        metric_rows.append({
            'timestamp': row.get('timestamp'),
            metric_name: row.get(source_column)
        })

    latest = metric_rows[-1] if metric_rows else None
    payload = {
        'success': True,
        'metric': metric_name,
        'count': len(metric_rows),
        'latest': latest,
        'rows': metric_rows
    }

    return jsonify(payload)


def _log_response(log_key: str):
    """Build standardized log response from CSV file."""
    path = CSV_FILES[log_key]
    rows = _read_csv_rows(path)

    payload = {
        'success': True,
        'log': log_key,
        'file': os.path.basename(path),
        'count': len(rows),
        'rows': rows
    }

    return jsonify(payload)


def _delete_log_file(log_key: str):
    """Delete a log CSV file for a given key."""
    path = CSV_FILES[log_key]

    if not os.path.exists(path):
        return jsonify({
            'success': True,
            'message': f"{os.path.basename(path)} already deleted",
            'file': os.path.basename(path)
        })

    try:
        os.remove(path)
        payload = {
            'success': True,
            'message': f"Deleted {os.path.basename(path)}",
            'file': os.path.basename(path)
        }
        return jsonify(payload)
    except Exception as e:
        logger.error(f"Failed deleting CSV {path}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'file': os.path.basename(path)
        }), 500


@app.route('/api/health', methods=['GET'])
def health():
    """Minimal health endpoint for polling clients."""
    return jsonify({'status': 'ok'})


@app.route('/api/voc_aqi', methods=['GET'])
def get_voc_aqi():
    return _metric_response('voc_aqi', 'voc_aqi')


@app.route('/api/temp_c', methods=['GET'])
def get_temp_c():
    return _metric_response('temp_c', 'temperature')


@app.route('/api/humidity_percent', methods=['GET'])
def get_humidity_percent():
    return _metric_response('humidity_percent', 'humidity')


@app.route('/api/pressure_hpa', methods=['GET'])
def get_pressure_hpa():
    return _metric_response('pressure_hpa', 'pressure')


@app.route('/api/voc_ppb', methods=['GET'])
def get_voc_ppb():
    return _metric_response('voc_ppb', 'voc_ppb')


@app.route('/api/bme688_log', methods=['GET'])
def get_bme688_log():
    return _log_response('bme688_log')


@app.route('/api/dgs2_log', methods=['GET'])
def get_dgs2_log():
    return _log_response('dgs2_log')


@app.route('/api/anomaly_log', methods=['GET'])
def get_anomaly_log():
    return _log_response('anomaly_log')


@app.route('/api/combined_log', methods=['GET'])
def get_combined_log():
    path = _combined_csv_path()
    rows = _read_csv_rows(path)
    payload = {
        'success': True,
        'log': 'combined_log',
        'file': os.path.basename(path),
        'count': len(rows),
        'rows': rows
    }
    return jsonify(payload)


@app.route('/api/bme688_log/delete', methods=['DELETE'])
def delete_bme688_log():
    return _delete_log_file('bme688_log')


@app.route('/api/dgs2_log/delete', methods=['DELETE'])
def delete_dgs2_log():
    return _delete_log_file('dgs2_log')


@app.route('/api/anomaly_log/delete', methods=['DELETE'])
def delete_anomaly_log():
    return _delete_log_file('anomaly_log')


@app.route('/api/combined_log/delete', methods=['DELETE'])
def delete_combined_log():
    path = _combined_csv_path()
    if not os.path.exists(path):
        return jsonify({
            'success': True,
            'message': f"{os.path.basename(path)} already deleted",
            'file': os.path.basename(path)
        })

    try:
        os.remove(path)
        payload = {
            'success': True,
            'message': f"Deleted {os.path.basename(path)}",
            'file': os.path.basename(path)
        }
        return jsonify(payload)
    except Exception as e:
        logger.error(f"Failed deleting CSV {path}: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'file': os.path.basename(path)
        }), 500


def run():
    logger.info(f"🚀 Starting HTTP polling API server on {API_HOST}:{API_PORT}")
    logger.info("✓ Frontend should poll these endpoints every 60 seconds")
    app.run(host=API_HOST, port=API_PORT, debug=False)


if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        logger.error(f"Fatal: {e}", exc_info=True)
        exit(1)
