import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import SensorPanel from './SensorPanel';
import LiveGraphs from './LiveGraphs';
import CameraFeed from './CameraFeed';
import MapView from './MapView';
import WifiPanel from './WifiPanel';
import SettingsPanel from './SettingsPanel';
import FoodStatusPanel from './FoodStatusPanel';
import SensorListPanel from './SensorListPanel';
import AIPredictionVisualizer from './AIPredictionVisualizer';
import { Cog6ToothIcon } from '@heroicons/react/24/outline';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

const initialSensorData = {
  voc: 0,
  temperature: 0,
  humidity: 0,
  co2: 0,
  ethylene: 0,
  alcohol: 0
};

const generateTimeLabels = (count: number) => {
  const labels = [];
  for (let i = 0; i < count; i++) {
    if (i === count - 1) {
      labels.push('now');
    } else {
      labels.push(`${count - 1 - i}h`);
    }
  }
  return labels;
};

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [sensorData, setSensorData] = useState(initialSensorData);
  const [showCamera] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [showWifi, setShowWifi] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showPrediction, setShowPrediction] = useState(false);
  const [graphData, setGraphData] = useState(() => {
    const labels = generateTimeLabels(12); // 12 hours, 1-hour interval
    return {
      labels,
      co2: Array(12).fill(0),
      ethylene: Array(12).fill(0),
      alcohol: Array(12).fill(0),
      voc: Array(12).fill(0),
      temperature: Array(12).fill(0),
      humidity: Array(12).fill(0)
    };
  });

  useEffect(() => {
    const toNumber = (value: unknown, fallback = 0): number => {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : fallback;
    };

    const fetchMetric = async (endpoint: string, key: string): Promise<number> => {
      try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`);
        if (!response.ok) {
          return 0;
        }

        const data = await response.json();
        const latest = data?.latest;
        if (!latest) {
          return 0;
        }

        return toNumber(latest[key]);
      } catch {
        return 0;
      }
    };

    const pollStats = async () => {
      const [vocAqi, tempC, humidityPercent, pressureHpa, vocPpb] = await Promise.all([
        fetchMetric('/api/voc_aqi', 'voc_aqi'),
        fetchMetric('/api/temp_c', 'temp_c'),
        fetchMetric('/api/humidity_percent', 'humidity_percent'),
        fetchMetric('/api/pressure_hpa', 'pressure_hpa'),
        fetchMetric('/api/voc_ppb', 'voc_ppb')
      ]);

      const newData = {
        voc: vocAqi,
        temperature: tempC,
        humidity: humidityPercent,
        co2: vocPpb,
        ethylene: pressureHpa,
        alcohol: 0
      };

      setSensorData(newData);

      setGraphData(prev => {
        // Shift labels left and add "now" at the end
        const newLabels = prev.labels.map((_, i) => {
          if (i === prev.labels.length - 1) return 'now';
          const nextLabel = prev.labels[i + 1];
          if (nextLabel === 'now') return '1h';
          const match = nextLabel.match(/(\d+)h/);
          if (match) {
            const hours = parseInt(match[1]) + 1;
            return `${hours}h`;
          }
          return nextLabel;
        });

        const updateArrayWithHistory = (arr: number[], value: number) => {
          const newArr = [...arr];
          newArr.shift();
          newArr.push(value);
          return newArr;
        };

        return {
          labels: newLabels,
          co2: updateArrayWithHistory(prev.co2, newData.co2),
          ethylene: updateArrayWithHistory(prev.ethylene, newData.ethylene),
          alcohol: updateArrayWithHistory(prev.alcohol, newData.alcohol),
          voc: updateArrayWithHistory(prev.voc, newData.voc),
          temperature: updateArrayWithHistory(prev.temperature, newData.temperature),
          humidity: updateArrayWithHistory(prev.humidity, newData.humidity)
        };
      });
    };

    pollStats();
    const interval = setInterval(pollStats, 60000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-800">
            Freshness Monitoring Dashboard
          </h1>
          <div className="flex gap-4 items-center">
            <div className="relative group">
              <button
                disabled
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors opacity-75 cursor-not-allowed"
              >
                {showCamera ? 'Hide Camera' : 'Show Camera'}
              </button>
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                Coming soon
              </div>
            </div>
            <div className="relative group">
              <button
                disabled
                className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors opacity-75 cursor-not-allowed"
              >
                Wi‑Fi
              </button>
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                Coming soon
              </div>
            </div>
            <button
              onClick={() => setShowPrediction(true)}
              className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
            >
              Predict
            </button>
            <button
              onClick={() => navigate('/logs')}
              className="px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              Logs
            </button>
            <button
              onClick={() => setShowMap(!showMap)}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors"
            >
              {showMap ? 'Hide Location' : 'Track Me'}
            </button>
            {/* settings icon placed to the right */}
            <button onClick={() => setShowSettings(true)} className="p-2 ml-2 hover:bg-gray-100 rounded-full">
              <Cog6ToothIcon className="h-6 w-6 text-gray-700" />
            </button>
          </div>
        </div>

        <SensorPanel data={sensorData} />

        {/* Two Column Layout: Left (Food Status Main) + Right (Sensors Compact) */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mt-8">
          {/* Left Column: Food Status - MAIN WINDOW (3 columns) */}
          <div className="lg:col-span-3 h-96">
            <FoodStatusPanel 
              status="Fresh" 
              conditionRating={8}
            />
          </div>

          {/* Right Column: Sensor List - COMPACT (2 columns) */}
          <div className="lg:col-span-2 h-96">
            <SensorListPanel 
              onRefresh={() => console.log('Refresh sensors')}
              onGetList={() => console.log('Get sensor list')}
            />
          </div>
        </div>

        {showCamera && (
          <div className="my-8 max-w-screen-xl mx-auto">
            <CameraFeed />
          </div>
        )}

        {showMap && (
          <div className="my-8 max-w-screen-xl mx-auto">
            <MapView show={showMap} onClose={() => setShowMap(false)} />
          </div>
        )}

        <WifiPanel visible={showWifi} onClose={() => setShowWifi(false)} />
        <SettingsPanel visible={showSettings} onClose={() => setShowSettings(false)} />

        <LiveGraphs data={graphData} />
        <AIPredictionVisualizer visible={showPrediction} onClose={() => setShowPrediction(false)} sensorData={sensorData} />
      </div>
    </div>
  );
};

export default Dashboard;