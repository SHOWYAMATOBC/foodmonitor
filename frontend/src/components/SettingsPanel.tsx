import React, { useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface SettingsPanelProps {
  visible: boolean;
  onClose: () => void;
}

const SettingsPanel: React.FC<SettingsPanelProps> = ({ visible, onClose }) => {
  const [wifiAutoConnect, setWifiAutoConnect] = useState(true);
  const [cameraEnabled, setCameraEnabled] = useState(true);
  const [dataUploadInterval, setDataUploadInterval] = useState(60);

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end p-6">
      <div className="w-96 bg-white rounded-lg shadow-lg">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">Settings</h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full">
            <XMarkIcon className="h-5 w-5 text-gray-600" />
          </button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <h4 className="font-medium">Network</h4>
            <div className="mt-2 text-sm text-gray-600">Scan for available Wi‑Fi networks and connect the Raspberry Pi if cellular is not desired.</div>
            <div className="mt-2 flex gap-2">
              <button className="px-3 py-2 bg-indigo-600 text-white rounded">Scan</button>
              <button className="px-3 py-2 bg-gray-200 rounded">Manage Known Networks</button>
            </div>
          </div>

          <div>
            <h4 className="font-medium">Camera</h4>
            <label className="flex items-center gap-2 mt-2">
              <input type="checkbox" checked={cameraEnabled} onChange={() => setCameraEnabled(!cameraEnabled)} />
              <span className="text-sm">Enable camera feed</span>
            </label>
          </div>

          <div>
            <h4 className="font-medium">Connectivity</h4>
            <label className="flex items-center gap-2 mt-2">
              <input type="checkbox" checked={wifiAutoConnect} onChange={() => setWifiAutoConnect(!wifiAutoConnect)} />
              <span className="text-sm">Auto-connect to known Wi‑Fi</span>
            </label>
            <div className="mt-2 text-sm">If disabled, the device will prefer cellular when Wi‑Fi is lost.</div>
          </div>

          <div>
            <h4 className="font-medium">Data</h4>
            <div className="mt-2 flex items-center gap-2">
              <input type="number" value={dataUploadInterval} onChange={e => setDataUploadInterval(Number(e.target.value))} className="w-24 p-1 border rounded" />
              <span className="text-sm">seconds between uploads</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPanel;
