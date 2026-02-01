import React, { useEffect, useState } from 'react';
import { XMarkIcon } from '@heroicons/react/24/outline';

interface WifiNetwork {
  ssid: string;
  rssi?: number;
  secure?: boolean;
}

interface WifiPanelProps {
  visible: boolean;
  onClose: () => void;
}

const WifiPanel: React.FC<WifiPanelProps> = ({ visible, onClose }) => {
  const [status, setStatus] = useState<{ ssid?: string; ip?: string; connected: boolean }>({ connected: false });
  const [ping, setPing] = useState<number | null>(null);
  const [scanResults, setScanResults] = useState<WifiNetwork[]>([]);
  const [connecting, setConnecting] = useState(false);
  const [ssidInput, setSsidInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');

  useEffect(() => {
    if (!visible) return;
    // Try to fetch wifi status from backend; fallback to mock
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/wifi/status');
        if (!res.ok) throw new Error('no status');
        const data = await res.json();
        setStatus({ ssid: data.ssid, ip: data.ip, connected: data.connected });
        setPing(typeof data.ping === 'number' ? data.ping : null);
      } catch (err) {
        // mock
        setStatus({ ssid: 'My_Home_WiFi', ip: '192.168.4.2', connected: true });
        setPing(24);
      }
    };
    fetchStatus();
  }, [visible]);

  const handleScan = async () => {
    try {
      const res = await fetch('/api/wifi/scan');
      if (!res.ok) throw new Error('scan failed');
      const data = await res.json();
      setScanResults(data);
    } catch (err) {
      // mock scan
      setScanResults([
        { ssid: 'My_Home_WiFi', rssi: -40, secure: true },
        { ssid: 'OfficeNet', rssi: -65, secure: true },
        { ssid: 'OpenGuest', rssi: -80, secure: false }
      ]);
    }
  };

  const handleConnect = async (ssid?: string) => {
    const target = ssid ?? ssidInput;
    if (!target) return;
    setConnecting(true);
    try {
      const res = await fetch('/api/wifi/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ssid: target, password: passwordInput })
      });
      if (!res.ok) throw new Error('connect failed');
      const data = await res.json();
      setStatus({ ssid: data.ssid, ip: data.ip, connected: data.connected });
      setPing(data.ping ?? null);
    } catch (err) {
      // mock success
      setTimeout(() => {
        setStatus({ ssid: target, ip: '192.168.4.5', connected: true });
        setPing(42);
        setConnecting(false);
      }, 1200);
    }
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-2xl bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">Wi‑Fi Panel</h3>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-500">
              {status.connected ? (
                <>
                  <div>SSID: <strong>{status.ssid}</strong></div>
                  <div>IP: {status.ip}</div>
                  <div>Ping: {ping ?? '—'} ms</div>
                </>
              ) : (
                <div className="text-red-500">Not connected</div>
              )}
            </div>
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-full">
              <XMarkIcon className="h-5 w-5 text-gray-600" />
            </button>
          </div>
        </div>

        <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="font-medium mb-2">Available networks</h4>
            <div className="space-y-2">
              {scanResults.length === 0 ? (
                <div className="text-sm text-gray-500">No scan yet</div>
              ) : (
                scanResults.map(net => (
                  <div key={net.ssid} className="flex items-center justify-between bg-gray-50 p-2 rounded">
                    <div>
                      <div className="font-medium">{net.ssid}</div>
                      <div className="text-xs text-gray-400">RSSI: {net.rssi ?? '—'}</div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => { setSsidInput(net.ssid); handleConnect(net.ssid); }} className="px-3 py-1 bg-blue-500 text-white rounded">Connect</button>
                    </div>
                  </div>
                ))
              )}
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={handleScan} className="px-3 py-2 bg-indigo-600 text-white rounded">Scan</button>
              <button onClick={() => { setScanResults([]); }} className="px-3 py-2 bg-gray-200 rounded">Clear</button>
            </div>
          </div>

          <div>
            <h4 className="font-medium mb-2">Manual connect</h4>
            <div className="space-y-2">
              <input value={ssidInput} onChange={e => setSsidInput(e.target.value)} placeholder="SSID" className="w-full p-2 border rounded" />
              <input value={passwordInput} onChange={e => setPasswordInput(e.target.value)} placeholder="Password" type="password" className="w-full p-2 border rounded" />
              <div className="flex gap-2">
                <button onClick={() => handleConnect()} disabled={connecting} className="px-3 py-2 bg-green-600 text-white rounded">{connecting ? 'Connecting...' : 'Connect'}</button>
                <button onClick={() => { setSsidInput(''); setPasswordInput(''); }} className="px-3 py-2 bg-gray-200 rounded">Reset</button>
              </div>
            </div>
            <div className="mt-4">
              <h4 className="font-medium">Notes</h4>
              <p className="text-sm text-gray-500">This panel will call backend endpoints like <code>/api/wifi/scan</code>, <code>/api/wifi/status</code> and <code>/api/wifi/connect</code>. Currently using mock responses.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WifiPanel;
