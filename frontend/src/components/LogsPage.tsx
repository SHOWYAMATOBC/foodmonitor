import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

type LogKey = 'dgs2_log' | 'bme688_log' | 'anomaly_log' | 'combined_log';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000';

const logOptions: Array<{ key: LogKey; label: string; endpoint: string; deleteEndpoint: string; fileName: string }> = [
  { key: 'dgs2_log', label: 'dgs2_log', endpoint: '/api/dgs2_log', deleteEndpoint: '/api/dgs2_log/delete', fileName: 'dgs2_readings.csv' },
  { key: 'bme688_log', label: 'bme688_log', endpoint: '/api/bme688_log', deleteEndpoint: '/api/bme688_log/delete', fileName: 'bme688_readings.csv' },
  { key: 'anomaly_log', label: 'anomaly_log', endpoint: '/api/anomaly_log', deleteEndpoint: '/api/anomaly_log/delete', fileName: 'anomalies.csv' },
  { key: 'combined_log', label: 'combined_log', endpoint: '/api/combined_log', deleteEndpoint: '/api/combined_log/delete', fileName: 'combined.csv' }
];

const fallbackCsvByLog: Record<LogKey, string> = {
  dgs2_log: 'timestamp,ppb,temperature,humidity\n',
  bme688_log: 'timestamp,temperature_c,humidity_percent,pressure_hpa,gas_resistance_ohm\n',
  anomaly_log: 'timestamp,anomaly_type,details,temperature,humidity,pressure,voc_ppb,overall_aqi\n',
  combined_log: 'timestamp,temperature,humidity,pressure,voc_ppb,gas_aqi,voc_aqi,overall_aqi,sampling_mode,data_quality\n'
};

type LogRow = Record<string, unknown>;

const LogsPage: React.FC = () => {
  const navigate = useNavigate();
  const [isBusyByLog, setIsBusyByLog] = useState<Record<LogKey, boolean>>({
    dgs2_log: false,
    bme688_log: false,
    anomaly_log: false,
    combined_log: false
  });
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [openLogLabel, setOpenLogLabel] = useState<string>('');
  const [openLogRows, setOpenLogRows] = useState<LogRow[]>([]);

  const fetchLogRows = async (logKey: LogKey): Promise<LogRow[]> => {
    const selected = logOptions.find(option => option.key === logKey);
    if (!selected) {
      return [];
    }

    const response = await fetch(`${API_BASE_URL}${selected.endpoint}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json,text/csv;q=0.9,*/*;q=0.8'
      }
    });

    if (!response.ok) {
      return [];
    }

    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const data = await response.json();
      const rows = Array.isArray(data) ? data : data?.rows;
      if (Array.isArray(rows)) {
        return rows as LogRow[];
      }
      return [];
    }

    const csvText = await response.text();
    const lines = csvText.trim().split('\n');
    if (lines.length < 2) {
      return [];
    }

    const headers = lines[0].split(',').map(h => h.trim());
    return lines.slice(1).map(line => {
      const values = line.split(',');
      const row: LogRow = {};
      headers.forEach((header, index) => {
        row[header] = values[index] ?? '';
      });
      return row;
    });
  };

  const openLogInPage = async (logKey: LogKey) => {
    const selected = logOptions.find(option => option.key === logKey);
    if (!selected) {
      return;
    }

    setLogBusy(logKey, true);
    setStatusMessage('');

    try {
      const rows = await fetchLogRows(logKey);
      setOpenLogLabel(selected.fileName);
      setOpenLogRows(rows);
      setStatusMessage(`Opened ${selected.fileName} (${rows.length} rows)`);
    } catch {
      setOpenLogLabel(selected.fileName);
      setOpenLogRows([]);
      setStatusMessage(`Failed to open ${selected.fileName}`);
    } finally {
      setLogBusy(logKey, false);
    }
  };

  const setLogBusy = (logKey: LogKey, busy: boolean) => {
    setIsBusyByLog(prev => ({ ...prev, [logKey]: busy }));
  };

  const downloadLog = async (logKey: LogKey) => {
    const selected = logOptions.find(option => option.key === logKey);
    if (!selected) {
      return;
    }

    setLogBusy(logKey, true);
    setStatusMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}${selected.endpoint}`, {
        method: 'GET',
        headers: {
          Accept: 'text/csv,application/json;q=0.9,*/*;q=0.8'
        }
      });

      let csvContent = '';

      if (response.ok) {
        const contentType = response.headers.get('content-type') || '';

        if (contentType.includes('application/json')) {
          const data = await response.json();
          const rows = Array.isArray(data) ? data : data?.rows;

          if (Array.isArray(rows) && rows.length > 0 && typeof rows[0] === 'object') {
            const headers = Object.keys(rows[0]);
            const csvRows = [headers.join(',')];
            rows.forEach((row: Record<string, unknown>) => {
              const line = headers
                .map((header) => {
                  const raw = row[header] ?? '';
                  const escaped = String(raw).replace(/"/g, '""');
                  return `"${escaped}"`;
                })
                .join(',');
              csvRows.push(line);
            });
            csvContent = csvRows.join('\n');
          } else {
            csvContent = fallbackCsvByLog[logKey];
          }
        } else {
          csvContent = await response.text();
        }
      } else {
        csvContent = fallbackCsvByLog[logKey];
      }

      if (!csvContent.trim()) {
        csvContent = fallbackCsvByLog[logKey];
      }

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = selected.fileName;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);

      setStatusMessage(`Downloaded ${selected.fileName}`);
    } catch (_error) {
      const csvContent = fallbackCsvByLog[logKey];
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = selected.fileName;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);

      setStatusMessage(`Downloaded fallback ${selected.fileName}`);
    } finally {
      setLogBusy(logKey, false);
    }
  };

  const deleteLog = async (logKey: LogKey) => {
    const selected = logOptions.find(option => option.key === logKey);
    if (!selected) {
      return;
    }

    setLogBusy(logKey, true);
    setStatusMessage('');

    try {
      const response = await fetch(`${API_BASE_URL}${selected.deleteEndpoint}`, {
        method: 'DELETE'
      });

      const data = await response.json();
      if (!response.ok || data?.success === false) {
        setStatusMessage(`Failed to delete ${selected.fileName}`);
      } else {
        if (openLogLabel === selected.fileName) {
          setOpenLogRows([]);
        }
        setStatusMessage(data?.message || `Deleted ${selected.fileName}`);
      }
    } catch {
      setStatusMessage(`Failed to delete ${selected.fileName}`);
    } finally {
      setLogBusy(logKey, false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
          <h1 className="text-3xl font-bold text-gray-800">Logs</h1>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Back to Dashboard
          </button>
        </div>

        <div className="bg-white rounded-xl shadow p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Log Files</h2>

          <div className="space-y-3 mb-6">
            {logOptions.map((option) => (
              <div key={option.key} className="border border-gray-300 rounded-lg p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div>
                    <p className="font-semibold text-gray-800">{option.label}</p>
                    <button
                      onClick={() => openLogInPage(option.key)}
                      disabled={isBusyByLog[option.key]}
                      className="text-sm text-blue-600 hover:text-blue-800 underline disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {option.fileName}
                    </button>
                  </div>

                  <div className="flex gap-2">
                    <button
                      onClick={() => downloadLog(option.key)}
                      disabled={isBusyByLog[option.key]}
                      className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                    >
                      {isBusyByLog[option.key] ? 'Working...' : 'Download CSV'}
                    </button>
                    <button
                      onClick={() => deleteLog(option.key)}
                      disabled={isBusyByLog[option.key]}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {statusMessage && <p className="mt-4 text-sm text-emerald-700">{statusMessage}</p>}

          <div className="mt-6 border-t pt-5">
            <h3 className="text-base font-semibold text-gray-800 mb-3">
              {openLogLabel ? `Opened File: ${openLogLabel}` : 'Opened File: None'}
            </h3>

            {openLogRows.length === 0 ? (
              <p className="text-sm text-gray-500">Click a CSV filename above to open and preview it here.</p>
            ) : (
              <div className="overflow-auto max-h-[420px] border border-gray-200 rounded-lg">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      {Object.keys(openLogRows[0]).map((header) => (
                        <th key={header} className="text-left px-3 py-2 font-semibold text-gray-700 border-b">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {openLogRows.map((row, index) => (
                      <tr key={index} className="odd:bg-white even:bg-gray-50">
                        {Object.keys(openLogRows[0]).map((header) => (
                          <td key={`${index}-${header}`} className="px-3 py-2 border-b text-gray-700 whitespace-nowrap">
                            {String(row[header] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
