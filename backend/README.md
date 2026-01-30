# DGS2 Backend Server

A complete Node.js backend for the DGS2 970-Series Digital Gas Sensor running on Raspberry Pi.

## Overview

This backend reads sensor data from a DGS2 digital gas sensor connected via USB-UART and provides:
- REST API endpoints for sensor data
- Real-time WebSocket streaming
- CSV logging
- In-memory data storage with ring buffer

## Architecture

```
┌─────────────────────────────────────────┐
│   DGS2 Digital Gas Sensor               │
│   (/dev/ttyUSB0)                        │
└────────────────┬────────────────────────┘
                 │ UART 9600 baud
                 ▼
┌─────────────────────────────────────────┐
│   Python Sensor Reader                  │
│   (sensor_reader.py)                    │
└────────────────┬────────────────────────┘
                 │ HTTP POST
                 ▼
┌─────────────────────────────────────────┐
│   Node.js Express Backend                │
│   ├─ REST API                            │
│   ├─ WebSocket Server                    │
│   ├─ CSV Logging                         │
│   └─ In-Memory Storage                   │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   React Frontend     Other Clients
   (WebSocket)        (REST/WebSocket)
```

## Features

- **UART Communication**: Direct serial connection to DGS2 sensor at 9600 baud
- **Real-time WebSocket**: Push sensor readings to connected clients
- **REST API**: Query current and historical readings
- **CSV Logging**: All readings logged to `logs/sensor_readings.csv`
- **Ring Buffer**: Maintains up to 10,000 readings in memory
- **Production-Ready**: Error handling, logging, graceful shutdown
- **Raspberry Pi Optimized**: Minimal dependencies, Linux-compatible

## Folder Structure

```
dgs2-backend/
├── server.js                      # Main Express server
├── package.json                   # Node.js dependencies
├── routes/
│   └── sensor.routes.js           # REST API endpoints
├── services/
│   └── sensor.service.js          # Business logic
├── websocket/
│   └── ws.server.js               # WebSocket server
├── storage/
│   └── data.store.js              # In-memory data store
├── python/
│   └── sensor_reader.py           # Python sensor reader
├── logs/                          # CSV log files (auto-created)
└── README.md                      # This file
```

## Installation

### Prerequisites

- Raspberry Pi running Linux (Debian/Ubuntu)
- Node.js 16+ (`curl -sL https://deb.nodesource.com/setup_18.x | sudo bash -`)
- Python 3.7+
- DGS2 sensor connected via USB-UART adapter

### Setup

1. **Clone and navigate to backend**
```bash
cd dgs2-backend
```

2. **Install Node.js dependencies**
```bash
npm install
```

3. **Install Python dependencies**
```bash
pip3 install pyserial requests
```

4. **Verify sensor connection**
```bash
ls -la /dev/ttyUSB*
# Should show: /dev/ttyUSB0
```

## Running

### Option 1: Separate Terminals (Recommended for Development)

**Terminal 1 - Start Node.js server:**
```bash
npm start
```

Expected output:
```
╔═══════════════════════════════════════╗
║   DGS2 Backend Server Started         ║
╚═══════════════════════════════════════╝

  Server: http://0.0.0.0:3001
  WebSocket: ws://0.0.0.0:3001
```

**Terminal 2 - Start Python sensor reader:**
```bash
python3 python/sensor_reader.py
```

Expected output:
```
[2024-01-30 10:30:45] INFO - DGS2 Sensor Reader Starting
[2024-01-30 10:30:45] INFO - Connected to /dev/ttyUSB0 at 9600 baud
[2024-01-30 10:30:45] INFO - Starting continuous measurements...
```

### Option 2: Using Process Manager (Production)

Install PM2:
```bash
sudo npm install -g pm2
```

Create `ecosystem.config.js`:
```javascript
module.exports = {
  apps: [
    {
      name: 'dgs2-backend',
      script: './server.js',
      instances: 1,
      exec_mode: 'cluster'
    },
    {
      name: 'dgs2-sensor',
      script: './python/sensor_reader.py',
      interpreter: 'python3',
      instances: 1
    }
  ]
};
```

Start with PM2:
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

## API Endpoints

### Health Check
```
GET /health
```
Response:
```json
{
  "status": "ok",
  "timestamp": "2024-01-30T10:30:45.123Z",
  "uptime": 12345.67
}
```

### Receive Sensor Data
```
POST /api/sensor/data
```
Request body:
```json
{
  "timestamp": "2024-01-30T10:30:45.123Z",
  "sensor_sn": "DGS2-001",
  "ppb": 45.2,
  "temperature": 23.45,
  "humidity": 65.32,
  "adc_gas": 1234,
  "adc_temp": 5678,
  "adc_hum": 9012
}
```

### Get Latest Reading
```
GET /api/sensor/latest
```
Response:
```json
{
  "timestamp": "2024-01-30T10:30:45.123Z",
  "sensor_sn": "DGS2-001",
  "ppb": 45.2,
  "temperature": 23.45,
  "humidity": 65.32,
  "adc_gas": 1234,
  "adc_temp": 5678,
  "adc_hum": 9012
}
```

### Get All Readings
```
GET /api/sensor/all
```
Response:
```json
{
  "count": 150,
  "readings": [
    { ...reading... },
    { ...reading... }
  ]
}
```

## WebSocket Usage

Connect to `ws://your-pi-ip:3001` (or `ws://localhost:3001` if local)

### Receiving Sensor Data
```javascript
const ws = new WebSocket('ws://localhost:3001');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  if (message.type === 'sensor_reading') {
    console.log('PPB:', message.data.ppb);
    console.log('Temp:', message.data.temperature);
    console.log('Humidity:', message.data.humidity);
  }
};
```

### Ping/Pong (Keep-Alive)
```javascript
// Send ping
ws.send(JSON.stringify({ type: 'ping' }));

// Receive pong
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'pong') {
    console.log('Pong received at', message.timestamp);
  }
};
```

## CSV Log Format

Data is logged to `logs/sensor_readings.csv`:

```csv
timestamp,sensor_sn,ppb,temperature,humidity,adc_gas,adc_temp,adc_hum
2024-01-30T10:30:45.123Z,DGS2-001,45.2,23.45,65.32,1234,5678,9012
2024-01-30T10:30:46.456Z,DGS2-001,46.1,23.46,65.33,1245,5689,9023
```

## Configuration

### Environment Variables

Create a `.env` file:
```
PORT=3001
HOST=0.0.0.0
NODE_ENV=production
```

### Python Sensor Reader

Edit `python/sensor_reader.py` to change:
- `SERIAL_PORT`: Serial device path (default: `/dev/ttyUSB0`)
- `BAUD_RATE`: Serial baud rate (default: `9600`)
- `BACKEND_URL`: Backend API endpoint (default: `http://localhost:3001/api/sensor/data`)

## Troubleshooting

### Serial Port Not Found
```bash
# List available serial ports
ls -la /dev/tty*

# Check USB adapter permissions
sudo usermod -a -G dialout $USER
# Reconnect or restart
```

### Connection Refused (Python to Backend)
- Verify Node.js server is running: `curl http://localhost:3001/health`
- Check firewall settings if connecting from remote Pi
- Verify backend URL in Python script

### No Serial Data
- Test sensor manually: `cat /dev/ttyUSB0`
- Check sensor power connection
- Try resetting USB port: `sudo systemctl restart bluetooth`

### High Memory Usage
- Ring buffer limit is 10,000 readings
- Adjust `MAX_READINGS` in `storage/data.store.js` if needed
- Consider implementing data archival for long-term storage

## Data Retention

The backend keeps the latest 10,000 readings in memory. For:
- **Real-time monitoring**: Use WebSocket
- **Historical data**: Query the CSV file in `logs/`
- **Long-term storage**: Consider adding database support

## Extending

### Add Database Support
Replace `data.store.js` with MongoDB/PostgreSQL queries

### Add Authentication
Use JWT tokens in Express middleware

### Add Data Validation
Implement schema validation in `sensor.service.js`

### Add Rate Limiting
Install `express-rate-limit` package

## Performance Notes

- Single readings ~5KB JSON payload
- 10,000 readings ~50MB in-memory
- CSV file grows ~100KB per day at 1Hz
- WebSocket overhead minimal with binary frames

## License

MIT

## Support

For issues or questions, check:
1. Python sensor reader logs
2. Express server console output
3. Browser DevTools for WebSocket connections
4. CSV logs for data accuracy
