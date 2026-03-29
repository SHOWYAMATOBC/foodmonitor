import React from 'react';

interface SensorData {
  voc: number;
  temperature: number;
  humidity: number;
  co2: number;
  ethylene: number;
  alcohol: number;
}

interface SensorPanelProps {
  data: SensorData;
}

const SensorPanel: React.FC<SensorPanelProps> = ({ data }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 p-4">
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-gray-500 text-sm font-medium">VOC AQI</h3>
        <p className="text-2xl font-bold">{data.voc}</p>
        <p className="text-sm text-gray-400">Air Quality</p>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-gray-500 text-sm font-medium">Temperature</h3>
        <p className="text-2xl font-bold">{data.temperature}°C</p>
        <p className="text-sm text-gray-400">Celsius</p>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-gray-500 text-sm font-medium">Humidity</h3>
        <p className="text-2xl font-bold">{data.humidity}%</p>
        <p className="text-sm text-gray-400">Relative</p>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-gray-500 text-sm font-medium">VOC</h3>
        <p className="text-2xl font-bold">{data.co2}</p>
        <p className="text-sm text-gray-400">ppb</p>
      </div>

      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-gray-500 text-sm font-medium">Pressure</h3>
        <p className="text-2xl font-bold">{data.ethylene}</p>
        <p className="text-sm text-gray-400">hPa</p>
      </div>
    </div>
  );
};

export default SensorPanel;