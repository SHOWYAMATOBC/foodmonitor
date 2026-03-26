# 🚀 Quick Start Guide

## Installation (One-time)

```bash
# Navigate to python directory
cd /home/hritik2144/foodmonitor/backend/python

# Install dependencies
pip install -r requirements.txt

# Verify sensors are connected
# - BME688: I2C address 0x77
# - DGS2: Serial port /dev/ttyUSB0
```

## Starting the System

```bash
cd /home/hritik2144/foodmonitor/backend/python
python3 master.py
```

## What to Expect

### ✅ Everything Working

```
🍎 FOOD MONITORING SYSTEM - MASTER CONTROL
============================================================

🔧 Initializing sensors...

✓ Starting BME688 Environmental Sensor...
✓ Starting DGS2 VOC Gas Sensor...

📡 SENSOR STATUS:

🌡️  BME688 Environmental Sensor:
   Status: ✓ CONNECTED
   Last Reading:
     • Temperature: 24.50°C
     • Humidity: 45.32%
     • Pressure: 1013.25 hPa
     • Gas Resistance: 65432 Ω
   Buffer: 0 readings

💨 DGS2 VOC Gas Sensor:
   Status: ✓ CONNECTED
   Last Reading:
     • VOC (PPB): 145.50
     • Temperature: 23.80°C
     • Humidity: 46.12%
   Buffer: 0 readings

🔥 WARMUP & BASELINE COLLECTION PHASE
Duration: 5 minutes

⏳ Warming up sensors for 5 minutes...
   04:59 remaining

[Wait 5 minutes...]

✅ ENTERING PRODUCTION MODE

[Minute 1] T=24.15°C | H=45.70% | VOC=42.50 ppb | AQI=126.38
[Minute 2] T=24.18°C | H=45.68% | VOC=40.80 ppb | AQI=124.16
```

## Key Points

### 5-Minute Warmup
- **Don't worry if no readings appear initially**
- Sensors are warming up and establishing baseline
- Baseline will be saved for future runs
- After 5 minutes, logging starts automatically

### Real-Time Readings
- New line every 60 seconds (after warmup)
- Shows: Temperature, Humidity, VOC, AQI
- All readings are averaged from 60 seconds of data
- All data is automatically saved to CSV files

### Stopping the System
```
Press Ctrl+C

Output:
⏹️  Shutting down sensors...

✓ All sensors stopped
✓ Data saved to CSV files
  • bme688_readings.csv
  • dgs2_readings.csv
  • calibrated_readings.csv
```

## Output Files

After running for 5+ minutes, you'll have:

1. **bme688_readings.csv** - Raw environmental data
2. **dgs2_readings.csv** - Raw VOC data
3. **calibrated_readings.csv** - Combined, calibrated data

All files are in the same directory (`/home/hritik2144/foodmonitor/backend/python/`)

## Troubleshooting

### Error: "Cannot initialize BME688"
```
✓ Check I2C connection
✓ Run: i2cdetect -y 1
✓ Should show 0x77
```

### Error: "Cannot connect to DGS2"
```
✓ Check USB cable is connected
✓ Run: ls -la /dev/ttyUSB*
✓ Verify it shows /dev/ttyUSB0
```

### Error: "No readings from either sensor"
```
✓ Wait longer (sensors need time to connect)
✓ Check both sensors show status as CONNECTED
✓ Restart the system
```

### CSV files are empty
```
✓ Wait for 5+ minutes after startup
✓ First CSV entries appear after warmup
✓ Check the calibrated_readings.csv file
```

## Tips

💡 **First Run**: Let it run for at least 10 minutes to collect good baseline data

💡 **Baseline Persistence**: VOC baseline is saved automatically, so future runs will be more accurate

💡 **Monitor Console**: The real-time console output is great for seeing what's happening

💡 **Check CSV Files**: Open the CSV files in a spreadsheet to see the data

💡 **Leave Running**: The system works best when left running for extended periods

## Next Steps

After verifying everything works:
1. ✅ Review the CSV files
2. ✅ Check the calibrated_readings.csv for good data
3. ✅ Integrate with your frontend
4. ✅ Set up automated logging/monitoring
5. ✅ Add alerting for high AQI values

---

**Enjoy monitoring your food! 🍎🍊🥗**
