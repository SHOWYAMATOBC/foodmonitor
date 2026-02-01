import React, { useState, useEffect } from 'react';
import SensorPanel from './SensorPanel';
import LiveGraphs from './LiveGraphs';
import CameraFeed from './CameraFeed';
import MapView from './MapView';
import WifiPanel from './WifiPanel';
import SettingsPanel from './SettingsPanel';
import FoodStatusPanel from './FoodStatusPanel';
import AIPredictionVisualizer from './AIPredictionVisualizer';
import { Cog6ToothIcon } from '@heroicons/react/24/outline';

// Mock data generator
const generateMockData = () => {
  return {
    voc: Math.floor(Math.random() * 500),
    temperature: +(20 + Math.random() * 10).toFixed(1),
    humidity: +(40 + Math.random() * 30).toFixed(1),
    co2: Math.floor(400 + Math.random() * 600),
    ethylene: +(Math.random() * 100).toFixed(2),
    alcohol: +(Math.random() * 50).toFixed(2)
  };
};

const generateTimeLabels = (count: number, interval: number) => {
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
  const [sensorData, setSensorData] = useState(generateMockData());
  const [showCamera, setShowCamera] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [showWifi, setShowWifi] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showPrediction, setShowPrediction] = useState(false);
  const [graphData, setGraphData] = useState(() => {
    const labels = generateTimeLabels(12, 1); // 12 hours, 1-hour interval
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
    const interval = setInterval(() => {
      const newData = generateMockData();
      setSensorData(newData);
      
      setGraphData(prev => {
        const updateArray = (arr: number[], value: number) => {
          const newArr = [...arr];
          newArr.shift();
          newArr.push(value);
          return newArr;
        };

        const now = new Date();
        const newLabel = now.toLocaleTimeString('en-US', { hour12: false });

        // Shift labels left and add "now" at the end
        const newLabels = prev.labels.map((label, i) => {
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
    }, 5000); // Simulating hourly updates every 5 seconds for demonstration

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
            <button
              onClick={() => setShowCamera(!showCamera)}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
            >
              {showCamera ? 'Hide Camera' : 'Show Camera'}
            </button>
            <button
              onClick={() => setShowWifi(true)}
              className="px-4 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
            >
              Wi‑Fi
            </button>
            <button
              onClick={() => setShowPrediction(true)}
              className="px-4 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors"
            >
              Predict
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

        {/* Food status panel below the sensor metrics */}
        <FoodStatusPanel name="Apples" status="Fresh" predictedSpoilDate={new Date(Date.now() + 5 * 24 * 3600 * 1000).toLocaleDateString()} />

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