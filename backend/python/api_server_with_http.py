#!/usr/bin/env python3
"""
Food Monitoring System - Flask API Server (Optimized)
WebSocket-first architecture for real-time streaming
Minimal HTTP fallback endpoints
Optimized for low memory/CPU usage
"""

import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO
import threading
import time

import realtime_data

# === CONFIGURATION ===
API_HOST = '0.0.0.0'
API_PORT = 5000
WS_BROADCAST_SENSOR_INTERVAL = 2  # seconds
WS_BROADCAST_GRAPH_INTERVAL = 5   # seconds

# === LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] API - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('API')

# === FLASK & WEBSOCKET SETUP ===
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25)

# === GLOBAL STATE ===
connected_clients = set()
last_broadcast_times = {'sensor': 0, 'graph': 0}


# === WEBSOCKET HANDLERS ===

@socketio.on('connect')
def handle_connect():
    """WebSocket client connected"""
    client_id = request.sid
    connected_clients.add(client_id)
    logger.info(f"✓ WebSocket: {client_id} connected (total: {len(connected_clients)})")


@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket client disconnected"""
    client_id = request.sid
    connected_clients.discard(client_id)
    logger.info(f"✗ WebSocket: {client_id} disconnected (total: {len(connected_clients)})")


@socketio.on('request_sensor_update')
def handle_sensor_update_request():
    """Client requests sensor data (on-demand)"""
    reading = realtime_data.get_current_reading()
    if reading:
        socketio.emit('sensor_data_update', {
            'success': True,
            'data': reading,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }, to=request.sid)
    else:
        socketio.emit('sensor_data_update', {
            'success': False,
            'error': 'No data available',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }, to=request.sid)


@socketio.on('request_graph_update')
def handle_graph_update_request(data=None):
    """Client requests graph data (on-demand)"""
    hours = (data or {}).get('hours', 1) if data else 1
    history = realtime_data.get_graph_history()
    
    if history:
        cutoff = datetime.utcnow().replace(tzinfo=None) - timedelta(hours=hours)
        filtered = [r for r in history if _is_recent(r, cutoff)]
        socketio.emit('graph_data_update', {
            'success': True,
            'data': filtered,
            'count': len(filtered),
            'hours': hours,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }, to=request.sid)
    else:
        socketio.emit('graph_data_update', {
            'success': False,
            'data': [],
            'error': 'No data available',
            'count': 0,
            'hours': hours,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }, to=request.sid)


# === HTTP ENDPOINTS (FALLBACK ONLY) ===

@app.route('/api/health', methods=['GET'])
def health_check():
    """Server health - minimal response"""
    return jsonify({'status': 'ok', 'ws': len(connected_clients)})


@app.route('/api/readings/current', methods=['GET'])
def get_current_reading():
    """Fallback: Get latest reading via HTTP"""
    reading = realtime_data.get_current_reading()
    if reading:
        return jsonify({'success': True, 'data': reading})
    return jsonify({'success': False, 'error': 'No data'}), 202


@app.route('/api/graph-data', methods=['GET'])
def get_graph_data():
    """Fallback: Get graph history via HTTP"""
    hours = request.args.get('hours', default=1, type=int)
    history = realtime_data.get_graph_history()
    
    if history:
        cutoff = datetime.utcnow().replace(tzinfo=None) - timedelta(hours=hours)
        filtered = [r for r in history if _is_recent(r, cutoff)]
        return jsonify({'success': True, 'data': filtered, 'count': len(filtered)})
    
    return jsonify({'success': False, 'data': [], 'count': 0}), 202


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Fallback: Get current sensor statistics"""
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
        })
    return jsonify({'error': 'No data available'}), 202


@app.route('/api/sensor-status', methods=['GET'])
def get_sensor_status():
    """Fallback: Get sensor connection status"""
    reading = realtime_data.get_current_reading()
    status = {
        'bme688': 'connected' if reading else 'disconnected',
        'dgs2': 'connected' if reading else 'disconnected'
    }
    return jsonify({
        'success': True,
        'data': status,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    })


# === BACKGROUND BROADCASTER ===

def _is_recent(reading: dict, cutoff_time: datetime) -> bool:
    """O(1) time check if reading is within time range"""
    try:
        ts_str = reading.get('timestamp', '').replace('Z', '+00:00')
        ts = datetime.fromisoformat(ts_str)
        ts_naive = ts.replace(tzinfo=None) if ts.tzinfo else ts
        return ts_naive >= cutoff_time
    except:
        return False


def broadcast_realtime_data():
    """
    Background thread: Continuously broadcasts sensor/graph data via WebSocket
    - Sensor updates every 2 seconds (low overhead)
    - Graph updates every 5 seconds (aggregated)
    - Only broadcasts when clients connected (O(n) where n=clients)
    """
    logger.info("🔄 WebSocket broadcaster started")
    
    while True:
        try:
            current_time = time.time()
            
            # Broadcast sensor data every 2s
            if (current_time - last_broadcast_times['sensor']) >= WS_BROADCAST_SENSOR_INTERVAL and connected_clients:
                reading = realtime_data.get_current_reading()
                if reading:
                    socketio.emit('sensor_data_stream', {
                        'success': True,
                        'data': reading,
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }, to=list(connected_clients))
                last_broadcast_times['sensor'] = current_time
            
            # Broadcast graph data every 5s
            if (current_time - last_broadcast_times['graph']) >= WS_BROADCAST_GRAPH_INTERVAL and connected_clients:
                history = realtime_data.get_graph_history()
                if history:
                    socketio.emit('graph_data_stream', {
                        'success': True,
                        'data': history[-50:],  # Only last 50 for efficiency
                        'count': len(history),
                        'timestamp': datetime.utcnow().isoformat() + 'Z'
                    }, to=list(connected_clients))
                last_broadcast_times['graph'] = current_time
            
            time.sleep(0.5)  # Check every 500ms
        except Exception as e:
            logger.error(f"Broadcaster error: {e}")
            time.sleep(1)


def start_broadcaster():
    """Start background broadcaster thread (daemon)"""
    thread = threading.Thread(target=broadcast_realtime_data, daemon=True)
    thread.start()


# === SERVER STARTUP ===

def run():
    """Start API server with WebSocket support"""
    logger.info(f"🚀 Starting server on {API_HOST}:{API_PORT}")
    logger.info("✓ WebSocket: PRIMARY (real-time streaming)")
    logger.info("✓ HTTP API: FALLBACK ONLY")
    logger.info("✓ Data: In-memory buffers (not persisted)")
    
    start_broadcaster()
    socketio.run(app, host=API_HOST, port=API_PORT, debug=False, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    try:
        run()
    except Exception as e:
        logger.error(f"Fatal: {e}", exc_info=True)
        exit(1)
