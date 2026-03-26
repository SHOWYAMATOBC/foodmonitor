# Food Monitoring System - Backend Refactoring Guide

## Overview

This is a **production-ready Python backend** for a Raspberry Pi 5-based food monitoring system. It reads from two sensors (BME688 environmental + DDS2-970650 VOC gas), applies calibration, aggregates data, and provides clean JSON output.

---

## Architecture

### Module Structure

```
backend/python/
├── bme688_reader.py      # BME688 environmental sensor reader
├── dds2_reader.py        # DDS2-970650 VOC gas sensor reader
├── data_fusion.py        # Combines and calibrates sensor data
├── main.py              # Orchestrates all sensors and APIs
├── combined_data.csv    # Aggregated sensor data (60s windows)
├── bme688_data.csv      # Raw BME688 readings
├── dds2_data.csv        # Raw DDS2 readings
└── requirements.txt     # Python dependencies
```

---

## Installation

### 1. Install Dependencies

```bash
cd /home/hritik2144/foodmonitor/backend/python
pip install -r requirements.txt
```

### 2. Enable I2C on Raspberry Pi (for BME688)

```bash
sudo raspi-config
# Navigate to: Interfacing Options → I2C → Enable
```

### 3. Connect Sensors

**BME688 (I2C):**
- VCC → 3.3V
- GND → GND
- SCL → GPIO3 (I2C Clock)
- SDA → GPIO2 (I2C Data)
- Address: 0x77

**DDS2-970650 (USB-UART):**
- USB connector to Raspberry Pi
- Serial port: `/dev/ttyUSB0`
- Baud rate: 9600

---

## Sensor Specifications

### BME688 (Environmental)

**Output (CSV):**
```
timestamp, temperature_c, humidity_percent, pressure_hpa, gas_resistance_ohm
2026-03-25T14:30:00.123456Z, 22.50, 45.30, 1013.25, 50000
```

**Readings:**
- Temperature: ±1°C accuracy
- Humidity: ±3% RH accuracy
- Pressure: ±1 hPa accuracy
- Gas Resistance: Raw ADC value (used for AQI calculation)

### DDS2-970650 (VOC Gas Sensor)

**Output (CSV):**
```
timestamp, sensor_sn, ppb, temperature, humidity, adc_gas, adc_temp, adc_hum
2026-03-25T14:30:00.123456Z, SN12345, 125.50, 22.50, 45.30, 1024, 512, 768
```

**Readings:**
- PPB (Parts Per Billion): VOC concentration
- Temperature: Scaled by 100 (divide by 100 for °C)
- Humidity: Scaled by 100 (divide by 100 for %)
- ADC values: Raw sensor ADC readings

---

## Calibration

### VOC Calibration (DDS2)

**Warm-up Phase:**
- Duration: 15 minutes
- Purpose: Sensor stabilization and baseline establishment
- Status: `is_warming_up` flag indicates warm-up state
- Remaining time: `get_warmup_time_remaining()` in seconds

**Baseline Calculation:**
- Samples 100+ readings during warm-up
- Computes average as baseline PPB reference
- Formula: `voc_calibrated = |ppb_raw - baseline_ppb|`

**Usage:**
```python
reader = DDS2Reader()
reader.start()

# Wait for warm-up (15 minutes)
while reader.is_warming_up:
    time.sleep(60)
    print(f"Warming up: {reader.get_warmup_time_remaining()} seconds remaining")

# Now sensor is calibrated
assert reader.is_calibrated()
```

### AQI Calculation (BME688)

**Formula:**
```
baseline_resistance = gas_resistance at power-on (clean air)
aqi_raw = (baseline_resistance / current_resistance) * 100
aqi_normalized = clip(aqi_raw * 5, 0, 500)
```

**AQI Scale:**
- 0-50: Good
- 51-100: Moderate
- 101-200: Unhealthy for sensitive groups
- 201-500: Unhealthy/Hazardous

**Usage:**
```python
reader = BME688Reader()
reader.start()

time.sleep(2)
aqi = reader.calculate_aqi()
print(f"AQI: {aqi}")
```

---

## Data Aggregation

### Aggregation Window

- **Window:** 60 seconds
- **Buffer:** In-memory (last 60 readings)
- **Output:** `combined_data.csv`

### Aggregated Metrics

```csv
timestamp, temp_avg, hum_avg, pressure_avg, voc_avg, voc_max, voc_min, voc_rate, bme688_count, dds2_count
```

**Calculations:**
- `temp_avg`: Average temperature over 60s
- `voc_max`: Maximum PPB over 60s
- `voc_rate`: Rate of change in PPB/minute
- `bme688_count`: Number of valid readings from BME688
- `dds2_count`: Number of valid readings from DDS2

---

## Data Fusion

### Combined Output Format

```json
{
  "timestamp": "2026-03-25T14:30:00.123456Z",
  "temperature": 22.50,
  "humidity": 45.30,
  "pressure": 1013.25,
  "voc": 125.50,
  "aqi": 87.5,
  "data_quality": "excellent",
  "calibrated": true
}
```

### Data Quality Levels

- **Excellent:** Both sensors + VOC calibrated
- **Good:** Both sensors + VOC warming up
- **Fair:** Only one sensor available
- **Poor:** Insufficient data

---

## API Usage

### Get Current Readings

```python
from main import SensorSystem

system = SensorSystem()
system.start()

# Get current readings
data = system.get_current_data()
print(data)
# Output: { "timestamp": "...", "temperature": 22.5, ... }

system.stop()
```

### Get Aggregated Data

```python
aggregated = system.get_aggregated_data()
print(aggregated)
# Output: { "temperature_avg": 22.3, "voc_avg": 125.2, "voc_max": 150.0, ... }
```

### Get System Status

```python
status = system.get_status()
print(status)
# Output: { "bme688": { "running": true, "has_data": true }, ... }
```

### Get JSON Output

```python
json_output = system.data_fusion.get_json_output(include_status=True)
print(json_output)
```

---

## Running the System

### Interactive Mode (Recommended for Testing)

```bash
cd /home/hritik2144/foodmonitor/backend/python
python3 main.py
```

**Commands:**
- `r` - Print current readings
- `s` - Print system status
- `j` - Print JSON output
- `a` - Print aggregated data
- `q` - Quit

### Continuous Mode (For Production)

```bash
python3 main.py --continuous --interval 10
```

### Run Individual Sensors

```bash
# Test BME688 only
python3 bme688_reader.py

# Test DDS2 only
python3 dds2_reader.py
```

---

## Error Handling

### Missing Sensors

The system **gracefully degrades**:
- If BME688 fails: Temperature/humidity/pressure unavailable, AQI = None
- If DDS2 fails: VOC data unavailable, system continues with BME688 data
- Both sensors fail: Returns `data_quality: "poor"`

### Serial Connection Issues (DDS2)

- Automatic retry on connection failure
- Checks for `/dev/ttyUSB0` existence
- Validates serial data format

### I2C Connection Issues (BME688)

- Checks I2C bus at startup
- Handles missing sensor gracefully
- Returns `None` for unavailable readings

---

## Performance Specifications

### Threading Model

```
Main Thread
├── BME688 Reader Thread (reads every 2s)
├── DDS2 Reader Thread (reads ~1s in continuous mode)
└── Aggregation Thread (saves every 60s)
```

### Memory Usage

- BME688 Buffer: ~30 readings × 5 fields = ~1.2 KB
- DDS2 Buffer: ~30 readings × 8 fields = ~1.9 KB
- Combined Buffer: ~30 readings × 10 fields = ~3.2 KB
- **Total: ~6.3 KB** (negligible on RPi)

### CSV File Sizes

- `bme688_data.csv`: ~50 bytes per reading (1 hour = 1.8 MB)
- `dds2_data.csv`: ~60 bytes per reading (1 hour = 2.2 MB)
- `combined_data.csv`: ~80 bytes per reading (1 hour = 288 KB)

---

## Troubleshooting

### BME688 Not Detected

```bash
# Check I2C bus
i2cdetect -y 1

# Should show: 0x77 (BME688 address)
# If not found: Check connections, enable I2C
```

### DDS2 Not Detected

```bash
# Check USB device
ls -la /dev/ttyUSB*

# If not found: Reconnect USB, check permissions
sudo usermod -a -G dialout $USER  # Add user to dialout group
```

### Calibration Not Starting

```bash
# Ensure DDS2 is connected and responding
# Check serial connection with miniterm
python3 -m serial.tools.miniterm /dev/ttyUSB0 9600

# You should see PPB readings appearing
```

---

## File Reference

### bme688_reader.py

**Classes:**
- `BME688Reader` - Main sensor reader

**Key Methods:**
- `start()` - Begin reading in background thread
- `stop()` - Stop sensor
- `get_latest_reading()` - Get last sensor reading
- `get_average_readings(seconds)` - Get averaged readings
- `calculate_aqi()` - Calculate air quality index
- `get_buffer_data()` - Get all buffered readings

### dds2_reader.py

**Classes:**
- `DDS2Reader` - VOC sensor reader with calibration

**Key Methods:**
- `start()` - Begin reading + warm-up
- `stop()` - Stop sensor
- `get_latest_reading()` - Get last reading
- `get_average_readings()` - Get averaged readings
- `is_calibrated()` - Check calibration status
- `get_warmup_time_remaining()` - Get remaining warm-up time

### data_fusion.py

**Classes:**
- `DataFusion` - Combines and calibrates sensor data

**Key Methods:**
- `combine_latest_readings()` - Merge latest from both sensors
- `get_current_readings()` - Clean API output
- `get_aggregated_readings(seconds)` - Get aggregated metrics
- `save_aggregated_to_csv(filename)` - Save to CSV
- `get_json_output(include_status)` - Get JSON string
- `get_status_summary()` - Get system status

### main.py

**Classes:**
- `SensorSystem` - Main orchestrator

**Key Methods:**
- `start()` - Start all sensors
- `stop()` - Stop all sensors
- `get_current_data()` - Current readings
- `get_aggregated_data()` - Aggregated data
- `get_status()` - System status
- `interactive_loop()` - Interactive CLI

---

## Future Enhancements

- [ ] Machine Learning for spoilage prediction
- [ ] REST API endpoints with Flask/FastAPI
- [ ] WebSocket real-time data streaming
- [ ] Cloud sync (AWS/Azure/GCP)
- [ ] Data visualization dashboard
- [ ] Predictive shelf-life calculation
- [ ] Multi-location support

---

## License

Proprietary - Food Monitoring System

---

## Support

For issues or questions, refer to the sensor datasheets:
- BME688: https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme688/
- DDS2-970650: Contact manufacturer for datasheet
