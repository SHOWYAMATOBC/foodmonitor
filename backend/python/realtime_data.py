#!/usr/bin/env python3
"""
Real-Time Data Buffer Module
Shared inter-process communication via temporary file
Used by master.py and api_server.py

Data is stored in /tmp/realtime_buffer.json (cleared on restart)
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

BUFFER_FILE = '/tmp/realtime_buffer.json'
MAX_GRAPH_HISTORY = 100

def update_buffer(data: Dict) -> None:
    """Update real-time buffer to temporary file for inter-process communication"""
    try:
        if not data:
            return
        
        # Read existing buffer
        buffer_data = {'current_reading': None, 'graph_history': []}
        if os.path.exists(BUFFER_FILE):
            try:
                with open(BUFFER_FILE, 'r') as f:
                    buffer_data = json.load(f)
            except:
                pass
        
        # Update current reading
        buffer_data['current_reading'] = data.copy()
        
        # Add to history and keep only latest 100
        if 'graph_history' not in buffer_data:
            buffer_data['graph_history'] = []
        buffer_data['graph_history'].append(data.copy())
        if len(buffer_data['graph_history']) > MAX_GRAPH_HISTORY:
            buffer_data['graph_history'] = buffer_data['graph_history'][-MAX_GRAPH_HISTORY:]
        
        # Write to temporary file
        with open(BUFFER_FILE, 'w') as f:
            json.dump(buffer_data, f)
    except Exception as e:
        print(f"Error updating buffer: {e}")

def get_current_reading() -> Optional[Dict]:
    """Get current reading from buffer file"""
    try:
        if os.path.exists(BUFFER_FILE):
            with open(BUFFER_FILE, 'r') as f:
                data = json.load(f)
                return data.get('current_reading')
    except:
        pass
    return None

def get_graph_history() -> List[Dict]:
    """Get graph history from buffer file"""
    try:
        if os.path.exists(BUFFER_FILE):
            with open(BUFFER_FILE, 'r') as f:
                data = json.load(f)
                return data.get('graph_history', [])
    except:
        pass
    return []

def clear_buffer() -> None:
    """Clear buffer file"""
    try:
        if os.path.exists(BUFFER_FILE):
            os.remove(BUFFER_FILE)
    except:
        pass
