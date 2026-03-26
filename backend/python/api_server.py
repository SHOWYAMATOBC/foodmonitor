#!/usr/bin/env python3
"""WebSocket-Only API Server - Real-time streaming only"""

import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import threading
import time

import realtime_data

API_HOST = '0.0.0.0'
API_PORT = 5000

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('API')

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

connected_clients = set()
last_broadcast = {'sensor': 0, 'graph': 0, 'stats': 0, 'status': 0}


# ============================================================================
# WEBSOCKET HANDLERS - ONLY REAL-TIME STREAMING
# ============================================================================

@socketio.on('connect')
def handle_connect():
    client_id = request.sid
    connected_clients.add(client_id)
    logger.info(f"✓ WebSocket connected: {client_id} (total: {len(connected_clients)})")


@socketio.on('disconnect')
def handle_disconnect():
    client_id = request.sid
    connected_clients.discard(client_id)
    logger.info(f"✗ WebSocket disconnected: {client_id} (total: {len(connected_clients)})")


# ============================================================================
# BACKGROUND BROADCASTER - ALL DATA VIA WEBSOCKET
# ============================================================================

def broadcast_realtime_data():
    """Stream ALL data via WebSocket - NO polling needed"""
    logger.info("🔄 WebSocket broadcaster started (real-time only)")
    
    while True:
        try:
            now = time.time()
            
            # Sensor data every 2s
            if (now - last_broadcast['sensor']) >= 2:
                reading = realtime_data.get_current_reading()
                if reading and connected_clients:
                    socketio.emit('sensor_data_stream', {
                        'success': True,
                        'data': reading
                    }, to=list(connected_clients))
                last_broadcast['sensor'] = now
            
            # Stats every 2s
            if (now - last_broadcast['stats']) >= 2:
                reading = realtime_data.get_current_reading()
                if reading and connected_clients:
                    socketio.emit('stats_stream', {
                        'success': True,
                        'data': {
                            'temperature': reading.get('temperature'),
                            'humidity': reading.get('humidity'),
                            'pressure': reading.get('pressure'),
                            'voc_ppb': reading.get('voc_ppb'),
                            'overall_aqi': reading.get('overall_aqi'),
                            'gas_aqi': reading.get('gas_aqi')
                        },
                        'timestamp': reading.get('timestamp')
                    }, to=list(connected_clients))
                last_broadcast['stats'] = now
            
            # Sensor status every 5s
            if (now - last_broadcast['status']) >= 5:
                reading = realtime_data.get_current_reading()
                if connected_clients:
                    socketio.emit('sensor_status_stream', {
                        'success': True,
                        'data': {
                            'bme688': 'connected' if reading else 'disconnected',
                            'dgs2': 'connected' if reading else 'disconnected'
                        }
                    }, to=list(connected_clients))
                last_broadcast['status'] = now
            
            # Graph data every 5s
            if (now - last_broadcast['graph']) >= 5:
                history = realtime_data.get_graph_history()
                if history and connected_clients:
                    socketio.emit('graph_data_stream', {
                        'success': True,
                        'data': history[-50:]
                    }, to=list(connected_clients))
                last_broadcast['graph'] = now
            
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Broadcaster error: {e}")
            time.sleep(1)


@app.route('/api/health', methods=['GET'])
def health():
    """Minimal health endpoint"""
    return jsonify({'status': 'ok', 'clients': len(connected_clients)})


def run():
    logger.info(f"🚀 Starting WebSocket-only server on {API_HOST}:{API_PORT}")
    logger.info("✓ REAL-TIME STREAMING ONLY (WebSocket)")
    logger.info("✓ NO HTTP POLLING")
    
    thread = threading.Thread(target=broadcast_realtime_data, daemon=True)
    thread.start()
    
    socketio.run(app, host=API_HOST, port=API_PORT, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        logger.error(f"Fatal: {e}", exc_info=True)
        exit(1)
