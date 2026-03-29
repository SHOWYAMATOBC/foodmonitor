# Backend API Endpoints (Current)

Source: backend/python/api_server.py

## Base
- Host: `0.0.0.0`
- Port: `5000`
- Server type: Flask + Flask-SocketIO

## HTTP Endpoints

### `GET /api/health`
Returns a minimal health payload:

```json
{
  "status": "ok",
  "clients": 0
}
```

- `status`: API server health flag.
- `clients`: currently connected WebSocket clients.

## WebSocket Handlers

### `connect`
- Triggered when a client connects.
- Tracks `request.sid` in server memory.

### `disconnect`
- Triggered when a client disconnects.
- Removes `request.sid` from server memory.

## WebSocket Streams Emitted by Server

### `sensor_data_stream` (every ~2s)
Payload:
```json
{
  "success": true,
  "data": { "...": "latest sensor reading" }
}
```
Emitted only when current reading exists.

### `stats_stream` (every ~2s)
Payload:
```json
{
  "success": true,
  "data": {
    "temperature": null,
    "humidity": null,
    "pressure": null,
    "voc_ppb": null,
    "overall_aqi": null,
    "gas_aqi": null
  },
  "timestamp": null
}
```
Emitted only when current reading exists.

### `sensor_status_stream` (every ~5s)
Payload:
```json
{
  "success": true,
  "data": {
    "bme688": "connected|disconnected",
    "dgs2": "connected|disconnected"
  }
}
```
Currently status is inferred from whether an in-memory reading exists.

### `graph_data_stream` (every ~5s)
Payload:
```json
{
  "success": true,
  "data": [ { "...": "history item" } ]
}
```
Emitted only when history exists.

---

## Current Note
`realtime_data` import has been removed from server startup path. The API now runs without that module and uses local in-process placeholders for current/history data.
