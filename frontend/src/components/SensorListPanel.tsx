import React, { useState } from 'react';
import { XMarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

interface Sensor {
  id: string;
  name: string;
  type: string;
  isConnected: boolean;
  lastSeen: string;
  signalStrength?: number;
}

interface SensorInfoModalProps {
  sensor: Sensor | null;
  onClose: () => void;
}

const SensorInfoModal: React.FC<SensorInfoModalProps> = ({ sensor, onClose }) => {
  if (!sensor) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full mx-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">{sensor.name}</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <XMarkIcon className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">Type:</span>
            <span className="font-medium">{sensor.type}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-600">ID:</span>
            <span className="font-mono text-xs">{sensor.id}</span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-600">Status:</span>
            <span className={`font-medium ${sensor.isConnected ? 'text-green-600' : 'text-red-600'}`}>
              {sensor.isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-gray-600">Last Seen:</span>
            <span className="font-medium">{sensor.lastSeen}</span>
          </div>

          {sensor.signalStrength !== undefined && (
            <div className="flex justify-between">
              <span className="text-gray-600">Signal Strength:</span>
              <span className="font-medium">{sensor.signalStrength}%</span>
            </div>
          )}
        </div>

        <button
          onClick={onClose}
          className="mt-6 w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
};

interface SensorListPanelProps {
  sensors?: Sensor[];
  onRefresh?: () => void;
  onGetList?: () => void;
}

const SensorListPanel: React.FC<SensorListPanelProps> = ({ 
  sensors, 
  onRefresh,
  onGetList
}) => {
  const [selectedSensor, setSelectedSensor] = useState<Sensor | null>(null);

  // Mock sensors data if not provided
  const defaultSensors: Sensor[] = [
    { id: 'DGS2-001', name: 'Main Sensor', type: 'DGS2 970', isConnected: true, lastSeen: 'now', signalStrength: 85 },
    { id: 'TEMP-001', name: 'Temperature', type: 'DHT22', isConnected: true, lastSeen: '2s ago', signalStrength: 92 },
    { id: 'CO2-001', name: 'CO2 Monitor', type: 'MH-Z19', isConnected: false, lastSeen: '5m ago', signalStrength: 0 },
    { id: 'CAM-001', name: 'Camera Feed', type: 'USB', isConnected: true, lastSeen: 'now', signalStrength: 100 },
    { id: 'DGS2-002', name: 'Secondary Sensor', type: 'DGS2 970', isConnected: true, lastSeen: '1s ago', signalStrength: 78 },
  ];

  const displaySensors = sensors || defaultSensors;

  return (
    <div className="bg-white rounded-lg shadow h-full flex flex-col">
      {/* Header with Action Buttons */}
      <div className="p-3 border-b border-gray-200 flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-800">Sensors</h3>
        
        {/* Action Buttons - Top Right */}
        <div className="flex items-center gap-2">
          <button
            onClick={onGetList}
            className="px-2 py-1 bg-indigo-500 text-white text-xs rounded hover:bg-indigo-600 transition-colors"
          >
            Get List
          </button>
          <button
            onClick={onRefresh}
            className="p-1.5 hover:bg-gray-100 rounded transition-colors"
            title="Refresh"
          >
            <ArrowPathIcon className="h-4 w-4 text-gray-600 hover:text-gray-800" />
          </button>
        </div>
      </div>

      {/* Scrollable Sensors List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {displaySensors.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            <p>No sensors connected</p>
          </div>
        ) : (
          displaySensors.map((sensor) => (
            <button
              key={sensor.id}
              onClick={() => setSelectedSensor(sensor)}
              className="w-full text-left p-2.5 hover:bg-gray-50 rounded border border-gray-200 transition-colors cursor-pointer"
            >
              <div className="flex items-center gap-2">
                {/* Status Dot */}
                <div
                  className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${
                    sensor.isConnected ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />

                {/* Sensor Info */}
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-gray-800 truncate">{sensor.name}</div>
                  <div className="text-xs text-gray-400 truncate">{sensor.type}</div>
                </div>

                {/* Last Seen */}
                <div className="text-xs text-gray-400 flex-shrink-0">{sensor.lastSeen}</div>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-2 border-t border-gray-200 bg-gray-50">
        <div className="text-xs text-gray-600">
          Connected: {displaySensors.filter(s => s.isConnected).length}/{displaySensors.length}
        </div>
      </div>

      {/* Sensor Info Modal */}
      <SensorInfoModal sensor={selectedSensor} onClose={() => setSelectedSensor(null)} />
    </div>
  );
};

export default SensorListPanel;
