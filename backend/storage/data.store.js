/**
 * Data Storage
 * 
 * In-memory storage for sensor readings
 * Maintains a ring buffer to prevent unbounded memory growth
 */

const MAX_READINGS = 10000; // Maximum readings to keep in memory

// In-memory data store
let dataStore = {
  readings: [],
  metadata: {
    initialized: null,
    totalReadingsReceived: 0
  }
};

/**
 * Initialize the data store
 */
function initializeStorage() {
  dataStore.metadata.initialized = new Date().toISOString();
  console.log('[STORE] Data storage initialized');
}

/**
 * Add a sensor reading to the store
 * 
 * Implements a ring buffer: when max readings reached,
 * removes the oldest reading before adding new one
 * 
 * @param {Object} reading - Sensor reading object
 */
function addReading(reading) {
  // Add reading
  dataStore.readings.push(reading);
  dataStore.metadata.totalReadingsReceived++;
  
  // Implement ring buffer - remove oldest if over max
  if (dataStore.readings.length > MAX_READINGS) {
    const removed = dataStore.readings.shift();
    console.log(`[STORE] Ring buffer limit reached, removed oldest reading from ${removed.timestamp}`);
  }
}

/**
 * Get the current data store object
 * 
 * @returns {Object} Data store with readings and metadata
 */
function getDataStore() {
  return dataStore;
}

/**
 * Get all readings
 * 
 * @returns {Array} Array of sensor readings
 */
function getAllReadings() {
  return [...dataStore.readings];
}

/**
 * Get latest reading
 * 
 * @returns {Object|null} Latest reading or null
 */
function getLatestReading() {
  if (dataStore.readings.length === 0) {
    return null;
  }
  return dataStore.readings[dataStore.readings.length - 1];
}

/**
 * Get readings within a time range
 * 
 * @param {Date} startTime - Start of time range
 * @param {Date} endTime - End of time range
 * @returns {Array} Filtered readings
 */
function getReadingsByTimeRange(startTime, endTime) {
  const start = new Date(startTime).getTime();
  const end = new Date(endTime).getTime();
  
  return dataStore.readings.filter(reading => {
    const readingTime = new Date(reading.timestamp).getTime();
    return readingTime >= start && readingTime <= end;
  });
}

/**
 * Clear all readings (for testing or reset)
 */
function clearReadings() {
  const count = dataStore.readings.length;
  dataStore.readings = [];
  console.log(`[STORE] Cleared ${count} readings`);
}

/**
 * Get storage statistics
 * 
 * @returns {Object} Storage stats
 */
function getStorageStats() {
  return {
    currentReadings: dataStore.readings.length,
    maxCapacity: MAX_READINGS,
    totalProcessed: dataStore.metadata.totalReadingsReceived,
    initialized: dataStore.metadata.initialized
  };
}

module.exports = {
  initializeStorage,
  addReading,
  getDataStore,
  getAllReadings,
  getLatestReading,
  getReadingsByTimeRange,
  clearReadings,
  getStorageStats
};
