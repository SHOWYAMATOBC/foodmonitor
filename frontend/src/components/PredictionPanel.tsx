import React from 'react';
import { Line as LineChart } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

interface PredictionPanelProps {
  visible: boolean;
  onClose: () => void;
}

const PredictionPanel: React.FC<PredictionPanelProps> = ({ visible, onClose }) => {
  if (!visible) return null;

  // Mock prediction: predicted degradation index over next days
  const labels = ['Today', '1d', '2d', '3d', '4d', '5d'];
  const predicted = [0.1, 0.2, 0.35, 0.55, 0.78, 0.95]; // 0..1 (1 = spoiled)

  const data = {
    labels,
    datasets: [
      {
        label: 'Predicted spoil index',
        data: predicted,
        borderColor: 'rgb(255,99,132)',
        backgroundColor: 'rgba(255,99,132,0.2)'
      }
    ]
  };

  const options = {
    responsive: true,
    scales: {
      y: {
        min: 0,
        max: 1
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-4xl bg-white rounded-lg shadow-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Spoilage Prediction (AI)</h3>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-500">Confidence: <strong>82%</strong></div>
            <button onClick={onClose} className="px-3 py-1 bg-gray-100 rounded">Close</button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-2">
            <LineChart data={data} options={options as any} />
          </div>
          <div className="p-2">
            <h4 className="font-medium">How the AI predicts</h4>
            <p className="text-sm text-gray-600 mt-2">The prediction visualises a spoilage index (0 = fresh, 1 = spoiled) over the next days based on recent sensor trends (VOC, ethylene, temperature, humidity, CO₂) and historical behaviour. The shaded region shows model uncertainty.</p>
            <div className="mt-4">
              <h5 className="font-medium">Key contributors</h5>
              <ul className="list-disc pl-5 text-sm text-gray-600 mt-2">
                <li>Ethylene rise accelerates spoilage</li>
                <li>High temperature and humidity increase rate</li>
                <li>Sharp VOC spikes indicate microbial activity</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PredictionPanel;
