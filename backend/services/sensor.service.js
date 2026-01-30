/**
 * Sensor Service
 * 
 * Business logic for handling sensor data:
 * - Storing readings in memory
 * - Logging to CSV file
 * - Broadcasting to WebSocket clients
 */

const fs = require('fs');
const path = require('path');
const { getDataStore, addReading } = require('../storage/data.store');
const { broadcastToClients } = require('../websocket/ws.server');

// CSV log file path
const CSV_LOG_PATH = path.join(__dirname, '../logs/sensor_readings.csv');

/**
 * Initialize CSV log file if it doesn't exist
 */
function initializeCsvLog() {
  const logsDir = path.join(__dirname, '../logs');
  
  if (!fs.existsSync(logsDir)) {
    fs.mkdirSync(logsDir, { recursive: true });
  }
  
  if (!fs.existsSync(CSV_LOG_PATH)) {
    const header = 'timestamp,sensor_sn,ppb,temperature,humidity,adc_gas,adc_temp,adc_hum\n';
    fs.writeFileSync(CSV_LOG_PATH, header);
    console.log(`[INFO] CSV log file created at ${CSV_LOG_PATH}`);
  }
}

/**
 * Append sensor reading to CSV log file
 * 
 * @param {Object} sensorData - Sensor reading object
 */
function appendToCSVLog(sensorData) {
  try {
    const {
      timestamp,
      sensor_sn,
      ppb,
      temperature,
      humidity,
      adc_gas,
      adc_temp,
      adc_hum
    } = sensorData;
    
    const csvLine = `${timestamp},${sensor_sn},${ppb},${temperature},${humidity},${adc_gas},${adc_temp},${adc_hum}\n`;
    fs.appendFileSync(CSV_LOG_PATH, csvLine);
  } catch (error) {
    console.error(`[ERROR] Failed to write to CSV log: ${error.message}`);
  }
}

/**
 * Handle incoming sensor data from Python reader
 * 
 * 1. Store in memory
 * 2. Log to CSV
 * 3. Broadcast via WebSocket
 * 
 * @param {Object} sensorData - Sensor reading object
 * @returns {Object} Result with reading count
 */
function handleSensorData(sensorData) {
  try {
    // Add timestamp if not present
    if (!sensorData.timestamp) {
      sensorData.timestamp = new Date().toISOString();
    }
    
    // Store in memory
    addReading(sensorData);
    
    // Log to CSV
    appendToCSVLog(sensorData);
    
    // Broadcast to WebSocket clients
    broadcastToClients(sensorData);
    
    // Get current count
    const store = getDataStore();
    
    console.log(`[SENSOR] PPB: ${sensorData.ppb} | Temp: ${sensorData.temperature}°C | Humidity: ${sensorData.humidity}%`);
    
    return {
      success: true,
      readingCount: store.readings.length
    };
  } catch (error) {
    console.error(`[ERROR] Error handling sensor data: ${error.message}`);
    throw error;
  }
}

/**
 * Get the most recent sensor reading
 * 
 * @returns {Object|null} Latest reading or null if no readings
 */
function getLatestReading() {
  const store = getDataStore();
  
  if (store.readings.length === 0) {
    return null;
  }
  
  return store.readings[store.readings.length - 1];
}

/**
 * Get all stored sensor readings
 * 
 * @returns {Array} Array of all readings
 */
function getAllReadings() {
  const store = getDataStore();
  return [...store.readings];
}

// Initialize CSV log on module load
initializeCsvLog();

module.exports = {
  handleSensorData,
  getLatestReading,
  getAllReadings,
  appendToCSVLog
};
