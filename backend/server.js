/**
 * DGS2 Backend Server
 * 
 * Main Express server with WebSocket support for real-time sensor data streaming
 * Runs on Raspberry Pi and communicates with Python sensor reader process
 */

const express = require('express');
const cors = require('cors');
const http = require('http');
const path = require('path');
require('dotenv').config();

const { setupWebSocket } = require('./websocket/ws.server');
const { initializeStorage } = require('./storage/data.store');
const sensorRoutes = require('./routes/sensor.routes');

// Configuration
const PORT = process.env.PORT || 3001;
const HOST = process.env.HOST || '0.0.0.0';

// Initialize Express app
const app = express();
const server = http.createServer(app);

// Initialize data storage
initializeStorage();

// Middleware
app.use(cors());
app.use(express.json());

// Logging middleware
app.use((req, res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`);
  next();
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// API Routes
app.use('/api/sensor', sensorRoutes);

// Setup WebSocket
setupWebSocket(server);

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Not found' });
});

// Error handler
app.use((err, req, res, next) => {
  console.error(`[ERROR] ${err.message}`);
  res.status(500).json({ error: 'Internal server error' });
});

// Start server
server.listen(PORT, HOST, () => {
  console.log(`
╔═══════════════════════════════════════╗
║   DGS2 Backend Server Started         ║
╚═══════════════════════════════════════╝
  
  Server: http://${HOST}:${PORT}
  WebSocket: ws://${HOST}:${PORT}
  Environment: ${process.env.NODE_ENV || 'development'}
  Timestamp: ${new Date().toISOString()}
  `);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('[INFO] SIGTERM received, shutting down gracefully');
  server.close(() => {
    console.log('[INFO] Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('[INFO] SIGINT received, shutting down gracefully');
  server.close(() => {
    console.log('[INFO] Server closed');
    process.exit(0);
  });
});
