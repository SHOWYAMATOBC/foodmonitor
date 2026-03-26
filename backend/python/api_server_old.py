#!/usr/bin/env python3
"""
Food Monitoring System - Flask API Server
Provides RESTful API endpoints for frontend consumption
Runs on port 5000

Data Sources:
- Real-time stats/graphs: IN-MEMORY buffers (from realtime_data module)
- Permanent records: CSV files (logging only)

WebSocket Support:
- Real-time data streaming via SocketIO
- Eliminates flickering from polling
- Direct streaming of sensor readings and graphs
"""

import os
import sys
import csv
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, disconnect
import threading
import time

# Import shared in-memory buffer module
import realtime_data

# Configuration
API_HOST = '0.0.0.0'
API_PORT = 5000

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] API - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('API')

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication
socketio = SocketIO(app, cors_allowed_origins="*")

# Global state
sensor_status = {
    'bme688': {'status': 'UNKNOWN', 'last_update': None},
    'dgs2': {'status': 'UNKNOWN', 'last_update': None}
}

# WebSocket client tracking
connected_clients = set()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'api_version': '1.0'
    }), 200


@app.route('/api/readings/current', methods=['GET'])
def get_current_reading():
    """Get latest REAL-TIME sensor reading from in-memory buffer"""
    try:
        # Read from in-memory buffer (NOT persisted)
        reading = realtime_data.get_current_reading()
        
        if reading:
            return jsonify({
                'success': True,
                'data': reading,
                'source': 'realtime-buffer',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'No real-time data available (system warming up)',
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }), 202  # Accepted but no data yet
            
    except Exception as e:
        logger.error(f"Error getting current reading: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/graph-data', methods=['GET'])
def get_graph_data():
    """Get real-time graph data from in-memory history buffer"""
    try:
        hours = request.args.get('hours', default=1, type=int)
        
        # Get data from in-memory history buffer (NOT persisted)
        history = realtime_data.get_graph_history()
        
        if history:
            # Filter by time range
            cutoff_time = datetime.utcnow().replace(tzinfo=None) - timedelta(hours=hours)
            filtered = []
            for reading in history:
                try:
                    ts_str = reading.get('timestamp', '').replace('Z', '+00:00')
                    ts = datetime.fromisoformat(ts_str)
                    ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                    if ts_naive >= cutoff_time:
                        filtered.append(reading)
                except:
                    continue
            
            return jsonify({
                'success': True,
                'data': filtered,
                'count': len(filtered),
                'hours': hours,
                'source': 'realtime-buffer'
            }), 200
        else:
            return jsonify({
                'success': False,
                'data': [],
                'error': 'No graph data available yet (system warming up)',
                'count': 0,
                'hours': hours,
                'source': 'realtime-buffer'
            }), 202  # Accepted but no data yet
            
    except Exception as e:
        logger.error(f"Error getting graph data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get sensor statistics"""
    try:
        reading = realtime_data.get_current_reading()
        
        if reading:
            return jsonify({
                'success': True,
                'data': {
                    'temperature': reading.get('temperature'),
                    'humidity': reading.get('humidity'),
                    'pressure': reading.get('pressure'),
                    'voc_ppb': reading.get('voc_ppb'),
                    'overall_aqi': reading.get('overall_aqi'),
                    'gas_aqi': reading.get('gas_aqi'),
                    'voc_aqi': reading.get('voc_aqi')
                },
                'timestamp': reading.get('timestamp')
            }), 200
        else:
            return jsonify({'error': 'No data available'}), 202
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sensor-status', methods=['GET'])
def get_sensor_status():
    """Get sensor connection status"""
    try:
        reading = realtime_data.get_current_reading()
        
        status = {
            'bme688': 'connected' if reading else 'disconnected',
            'dgs2': 'connected' if reading else 'disconnected'
        }
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
    except Exception as e:
        logger.error(f"Error getting sensor status: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# WebSocket Handlers - Real-time streaming without flickering
# ============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    from flask import request as flask_request
    client_id = flask_request.sid
    connected_clients.add(client_id)
    logger.info(f"✓ WebSocket client connected: {client_id} (total: {len(connected_clients)})")
    emit('connect_response', {'status': 'connected', 'message': 'Successfully connected to real-time data stream'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    from flask import request as flask_request
    client_id = flask_request.sid
    connected_clients.discard(client_id)
    logger.info(f"✗ WebSocket client disconnected: {client_id} (total: {len(connected_clients)})")


@socketio.on('request_sensor_update')
def handle_sensor_update():
    """Handle request for sensor data update"""
    reading = realtime_data.get_current_reading()
    if reading:
        emit('sensor_data_update', {
            'success': True,
            'data': reading,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    else:
        emit('sensor_data_update', {
            'success': False,
            'error': 'No data available',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })


@socketio.on('request_graph_update')
def handle_graph_update(data):
    """Handle request for graph data"""
    hours = data.get('hours', 1) if data else 1
    history = realtime_data.get_graph_history()
    
    if history:
        cutoff_time = datetime.utcnow().replace(tzinfo=None) - timedelta(hours=hours)
        filtered = []
        for reading in history:
            try:
                ts_str = reading.get('timestamp', '').replace('Z', '+00:00')
                ts = datetime.fromisoformat(ts_str)
                ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
                if ts_naive >= cutoff_time:
                    filtered.append(reading)
            except:
                continue
        
        emit('graph_data_update', {
            'success': True,
            'data': filtered,
            'count': len(filtered),
            'hours': hours,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })
    else:
        emit('graph_data_update', {
            'success': False,
            'data': [],
            'error': 'No graph data available',
            'count': 0,
            'hours': hours,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        })


def emit_realtime_updates():
    """
    Background thread that continuously emits real-time updates to all connected clients
    Frequency: Every 2 seconds for sensor updates, every 5 seconds for graph updates
    """
    last_sensor_emit = 0
    last_graph_emit = 0
    
    logger.info("🔄 Started real-time update broadcaster thread")
    
    while True:
        try:
            current_time = time.time()
            
            # Emit sensor data every 2 seconds
            if current_time - last_sensor_emit >= 2:
                reading = realtime_data.get_current_reading()
                if reading and connected_clients:
                    socketio.emit('sensor_data_stream', {
                        'success': True,
                        'data': reading,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }, to=list(connected_clients))
                    last_sensor_emit = current_time
            
            # Emit graph data every 5 seconds
            if current_time - last_graph_emit >= 5:
                history = realtime_data.get_graph_history()
                if history and connected_clients:
                    socketio.emit('graph_data_stream', {
                        'success': True,
                        'data': history[-50:],  # Send last 50 readings
                        'count': len(history),
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }, to=list(connected_clients))
                    last_graph_emit = current_time
            
            time.sleep(0.5)  # Check every 500ms
        except Exception as e:
            logger.error(f"Error in realtime update broadcaster: {e}")
            time.sleep(1)


def run_broadcaster_thread():
    """Start background thread for real-time updates"""
    thread = threading.Thread(target=emit_realtime_updates, daemon=True)
    thread.start()
    return thread


@app.errorhandler(404)
def not_found(error):
    """404 handler"""
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def server_error(error):
    """500 handler"""
    logger.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


def run_api_server():
    """Run Flask API server with WebSocket support"""
    logger.info(f"🚀 Starting API server on {API_HOST}:{API_PORT}")
    logger.info("✓ Real-time data source: IN-MEMORY buffers (not persisted)")
    logger.info("✓ Permanent records: CSV files only")
    logger.info("✓ WebSocket support enabled for real-time streaming")
    
    # Start background broadcaster thread
    run_broadcaster_thread()
    
    socketio.run(
        app,
        host=API_HOST,
        port=API_PORT,
        debug=False,
        allow_unsafe_werkzeug=True
    )


if __name__ == '__main__':
    try:
        run_api_server()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
