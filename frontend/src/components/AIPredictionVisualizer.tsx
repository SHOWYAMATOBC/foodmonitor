import React, { useEffect, useMemo, useState } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface SensorData {
  voc: number;
  temperature: number;
  humidity: number;
  co2: number;
  ethylene: number;
  alcohol: number;
}

interface Props {
  visible: boolean;
  onClose: () => void;
  sensorData: SensorData;
}

const clamp = (v: number, a = 0, b = 1) => Math.max(a, Math.min(b, v));

// Create a single index from sensors (mock model)
const computeIndex = (s: SensorData) => {
  const vocScore = clamp(s.voc / 500, 0, 1) * 0.2;
  const ethScore = clamp(s.ethylene / 100, 0, 1) * 0.35;
  const tempScore = clamp((s.temperature - 10) / 30, 0, 1) * 0.25; // normalized 10..40°C
  const humScore = clamp(s.humidity / 100, 0, 1) * 0.12;
  const co2Score = clamp(s.co2 / 2000, 0, 1) * 0.08;
  return clamp(vocScore + ethScore + tempScore + humScore + co2Score, 0, 1);
};

const AIPredictionVisualizer: React.FC<Props> = ({ visible, onClose, sensorData }) => {
  const [nowIndex, setNowIndex] = useState(() => computeIndex(sensorData));
  const [predicted, setPredicted] = useState<number[]>([nowIndex, nowIndex + 0.05, nowIndex + 0.12, nowIndex + 0.2, nowIndex + 0.32]);

  useEffect(() => {
    setNowIndex(computeIndex(sensorData));
  }, [sensorData]);

  // slowly animate predicted series toward a new forecast whenever nowIndex changes
  useEffect(() => {
    let cancelled = false;
    const target = [nowIndex, nowIndex + 0.05, nowIndex + 0.12, nowIndex + 0.2, nowIndex + 0.32].map(v => clamp(v));
    // animate in 20 steps
    const steps = 20;
    const start = predicted;
    let step = 0;
    const id = setInterval(() => {
      step++;
      const t = step / steps;
      const next = start.map((sVal, i) => sVal + (target[i] - sVal) * t);
      if (!cancelled) setPredicted(next.map(v => clamp(v)));
      if (step >= steps) {
        clearInterval(id);
      }
    }, 60);
    return () => { cancelled = true; clearInterval(id); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nowIndex]);

  const labels = useMemo(() => ['Now', '+1d', '+2d', '+3d', '+4d'], []);

  const data = useMemo(() => ({
    labels,
    datasets: [
      {
        label: 'Spoilage index (0 fresh → 1 spoiled)',
        data: predicted,
        borderColor: 'rgba(99,102,241,1)',
        backgroundColor: 'rgba(99,102,241,0.2)',
        tension: 0.3,
        pointRadius: 4
      }
    ]
  }), [labels, predicted]);

  const options: ChartOptions<'line'> = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { min: 0, max: 1 }
    },
    plugins: {
      legend: { display: false }
    }
  }), []);

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="w-full max-w-5xl bg-gradient-to-b from-white/80 to-white/95 rounded-lg shadow-2xl overflow-hidden">
        <div className="flex items-start justify-between p-4 border-b">
          <div>
            <h3 className="text-xl font-semibold text-gray-800">AI prediction visualizer</h3>
            <p className="text-sm text-gray-500">Live model output driven by incoming sensor data — animated to show confidence and trend.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-600">Current index: <strong>{nowIndex.toFixed(2)}</strong></div>
            <button onClick={onClose} className="px-3 py-1 bg-gray-100 rounded">Close</button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4">
          <div className="h-80 p-2 bg-black/5 rounded">
            <Line data={data as any} options={options as any} />
          </div>

          <div className="h-80 p-4 relative bg-gradient-to-tr from-sky-900 to-indigo-700 rounded text-white overflow-hidden">
            {/* Animated techy background */}
            <svg className="absolute inset-0 w-full h-full" viewBox="0 0 600 400" preserveAspectRatio="none" aria-hidden>
              <defs>
                <linearGradient id="g1" x1="0" x2="1">
                  <stop offset="0%" stopColor="#7c3aed" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.2" />
                </linearGradient>
              </defs>
              <g fill="none" stroke="url(#g1)" strokeWidth="2">
                <path className="wave1" d="M0 300 C150 200 450 400 600 300" />
                <path className="wave2" d="M0 250 C150 150 450 350 600 250" />
              </g>
            </svg>

            <div className="relative z-10">
              <h4 className="text-lg font-semibold">Model explanation</h4>
              <p className="text-sm mt-2 text-sky-200">The model combines multiple sensor streams into a spoilage index. You can see the predicted trajectory on the left.</p>

              <div className="mt-4 grid grid-cols-2 gap-2">
                <div className="p-2 bg-white/5 rounded">
                  <div className="text-xs text-sky-200">VOC</div>
                  <div className="text-xl font-semibold">{sensorData.voc}</div>
                </div>
                <div className="p-2 bg-white/5 rounded">
                  <div className="text-xs text-sky-200">Ethylene</div>
                  <div className="text-xl font-semibold">{sensorData.ethylene}</div>
                </div>
                <div className="p-2 bg-white/5 rounded">
                  <div className="text-xs text-sky-200">Temperature</div>
                  <div className="text-xl font-semibold">{sensorData.temperature}°C</div>
                </div>
                <div className="p-2 bg-white/5 rounded">
                  <div className="text-xs text-sky-200">Humidity</div>
                  <div className="text-xl font-semibold">{sensorData.humidity}%</div>
                </div>
              </div>
            </div>
            <style>{`
              .wave1 { stroke-dasharray: 400; stroke-dashoffset: 0; animation: dash 6s linear infinite; }
              .wave2 { stroke-dasharray: 300; stroke-dashoffset: 0; animation: dash 4s linear infinite reverse; }
              @keyframes dash { from { stroke-dashoffset: 0; } to { stroke-dashoffset: -700; } }
            `}</style>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AIPredictionVisualizer;
