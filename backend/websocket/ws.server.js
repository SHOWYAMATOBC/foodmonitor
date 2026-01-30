/**
 * WebSocket Server
 * 
 * Real-time WebSocket server for broadcasting sensor data to connected clients
 * Clients receive updates immediately as new sensor readings arrive
 */

const WebSocket = require('ws');

// Track connected WebSocket clients
let wsServer = null;
let connectedClients = new Set();

/**
 * Setup WebSocket server
 * 
 * @param {http.Server} httpServer - HTTP server instance
 */
function setupWebSocket(httpServer) {
  wsServer = new WebSocket.Server({ 
    server: httpServer,
    path: '/ws'
  });
  
  wsServer.on('connection', (ws, req) => {
    const clientIp = req.socket.remoteAddress;
    console.log(`[WS] Client connected from ${clientIp}`);
    
    // Add client to set
    connectedClients.add(ws);
    
    // Send welcome message
    ws.send(JSON.stringify({
      type: 'connection',
      message: 'Connected to DGS2 sensor server',
      timestamp: new Date().toISOString(),
      clientCount: connectedClients.size
    }));
    
    // Handle incoming messages (echo back or process commands)
    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data);
        console.log(`[WS] Received from ${clientIp}:`, message.type || 'unknown');
        
        // Handle ping/pong
        if (message.type === 'ping') {
          ws.send(JSON.stringify({
            type: 'pong',
            timestamp: new Date().toISOString()
          }));
        }
      } catch (error) {
        console.error(`[WS] Error processing message: ${error.message}`);
      }
    });
    
    // Handle client disconnect
    ws.on('close', () => {
      connectedClients.delete(ws);
      console.log(`[WS] Client disconnected from ${clientIp}. Remaining: ${connectedClients.size}`);
    });
    
    // Handle errors
    ws.on('error', (error) => {
      console.error(`[WS] Error with client ${clientIp}: ${error.message}`);
    });
  });
  
  console.log('[WS] WebSocket server initialized on ws://0.0.0.0:3001/ws');
}

/**
 * Broadcast sensor data to all connected WebSocket clients
 * 
 * @param {Object} sensorData - Sensor reading to broadcast
 */
function broadcastToClients(sensorData) {
  if (!wsServer) {
    console.warn('[WS] WebSocket server not initialized');
    return;
  }
  
  const payload = JSON.stringify({
    type: 'sensor_reading',
    data: sensorData,
    timestamp: new Date().toISOString()
  });
  
  let successCount = 0;
  let failCount = 0;
  
  connectedClients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      try {
        client.send(payload);
        successCount++;
      } catch (error) {
        console.error(`[WS] Failed to send to client: ${error.message}`);
        failCount++;
      }
    }
  });
  
  if (connectedClients.size > 0) {
    console.log(`[WS] Broadcasted to ${successCount}/${connectedClients.size} clients`);
  }
}

/**
 * Get count of connected WebSocket clients
 * 
 * @returns {number} Number of connected clients
 */
function getConnectedClientCount() {
  return connectedClients.size;
}

module.exports = {
  setupWebSocket,
  broadcastToClients,
  getConnectedClientCount
};
