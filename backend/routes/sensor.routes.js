/**
 * Sensor Routes
 * 
 * REST API endpoints for sensor data:
 * - POST /api/sensor/data - Receive sensor readings from Python reader
 * - GET /api/sensor/latest - Get the most recent reading
 * - GET /api/sensor/all - Get all readings since server start
 */

const express = require('express');
const router = express.Router();
const { 
  handleSensorData, 
  getLatestReading, 
  getAllReadings 
} = require('../services/sensor.service');

/**
 * POST /api/sensor/data
 * 
 * Receive sensor data from Python sensor reader process
 * Stores in memory and broadcasts via WebSocket
 * 
 * Expected payload:
 * {
 *   "timestamp": "2024-01-30T10:30:45.123Z",
 *   "sensor_sn": "ABC123",
 *   "ppb": 45.2,
 *   "temperature": 23.45,
 *   "humidity": 65.32,
 *   "adc_gas": 1234,
 *   "adc_temp": 5678,
 *   "adc_hum": 9012
 * }
 */
router.post('/data', (req, res) => {
  try {
    const sensorData = req.body;
    
    // Validate required fields
    const requiredFields = ['timestamp', 'sensor_sn', 'ppb', 'temperature', 'humidity'];
    const missing = requiredFields.filter(field => !(field in sensorData));
    
    if (missing.length > 0) {
      return res.status(400).json({
        error: 'Missing required fields',
        missing: missing
      });
    }
    
    // Process the sensor data
    const result = handleSensorData(sensorData);
    
    res.status(200).json({
      success: true,
      message: 'Sensor data received and broadcasted',
      readingCount: result.readingCount
    });
  } catch (error) {
    console.error(`[ERROR] Failed to process sensor data: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/sensor/latest
 * 
 * Returns the most recent sensor reading
 * 
 * Response:
 * {
 *   "timestamp": "2024-01-30T10:30:45.123Z",
 *   "sensor_sn": "ABC123",
 *   "ppb": 45.2,
 *   "temperature": 23.45,
 *   "humidity": 65.32,
 *   "adc_gas": 1234,
 *   "adc_temp": 5678,
 *   "adc_hum": 9012
 * }
 */
router.get('/latest', (req, res) => {
  try {
    const latest = getLatestReading();
    
    if (!latest) {
      return res.status(404).json({ error: 'No readings available yet' });
    }
    
    res.json(latest);
  } catch (error) {
    console.error(`[ERROR] Failed to retrieve latest reading: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/sensor/all
 * 
 * Returns all readings stored since server start
 * 
 * Response:
 * {
 *   "count": 150,
 *   "readings": [
 *     { ...sensor data... },
 *     ...
 *   ]
 * }
 */
router.get('/all', (req, res) => {
  try {
    const readings = getAllReadings();
    
    res.json({
      count: readings.length,
      readings: readings
    });
  } catch (error) {
    console.error(`[ERROR] Failed to retrieve all readings: ${error.message}`);
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
