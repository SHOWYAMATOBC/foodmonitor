import React, { useState } from 'react';
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
  ChartData,
  ChartOptions
} from 'chart.js';
import { AiOutlineFullscreen } from 'react-icons/ai';
import type { ComponentType } from 'react';
import TimeRangeSelector, { TimeRange } from './TimeRangeSelector';
import FullScreenGraph from './FullScreenGraph';

// Wrap/cast the icon to React.ComponentType so TypeScript treats it as a
// valid JSX component (returns Element | null). This avoids TS2786.
const FullscreenIcon = AiOutlineFullscreen as unknown as ComponentType<{ size?: number | string }>;
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface LiveGraphsProps {
  data: {
    labels: string[];
    co2: number[];
    ethylene: number[];
    alcohol: number[];
    voc: number[];
    temperature: number[];
    humidity: number[];
  };
}

const LiveGraphs: React.FC<LiveGraphsProps> = ({ data }) => {
  const [selectedRange, setSelectedRange] = useState<TimeRange>('1D');
  const [fullScreenGraph, setFullScreenGraph] = useState<{
    title: string;
    data: ChartData<'line'>;
    options: ChartOptions<'line'>;
  } | null>(null);
  const commonOptions: ChartOptions<'line'> = {
    responsive: true,
    animation: false,
    maintainAspectRatio: false,
    scales: {
      x: {
        grid: { display: true },
        reverse: true,  // Display time backwards (from now to past)
        ticks: {
          maxRotation: 0,  // Keep labels horizontal
          minRotation: 0,
          autoSkip: true,
          maxTicksLimit: 8,
          font: {
            size: 11,
            weight: (ctx) => ctx.tick.value === data.labels.length - 1 ? 'bold' : 'normal' // Bold "now"
          }
        }
      },
      y: {
        beginAtZero: true,
        grid: { 
          color: 'rgba(0, 0, 0, 0.1)'
        }
      }
    },
    plugins: {
      legend: {
        display: false
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          title: (tooltipItems) => {
            const item = tooltipItems[0];
            return item.label;
          }
        }
      }
    },
    interaction: {
      mode: 'nearest',
      axis: 'x',
      intersect: false
    }
  };

  const createDataset = (label: string, data: number[], color: string, labels: string[]): ChartData<'line'> => ({
    labels,
    datasets: [
      {
        label,
        data,
        borderColor: color,
        backgroundColor: color,
        tension: 0.3,
      }
    ]
  });

  const openFullScreen = (title: string, data: ChartData<'line'>) => {
    setFullScreenGraph({
      title,
      data,
      options: commonOptions
    });
  };

  return (
    <div className="space-y-6 p-4">
      <TimeRangeSelector selectedRange={selectedRange} onRangeChange={setSelectedRange} />
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-gray-700 font-medium">CO₂ Levels (ppm)</h3>
            <button
              onClick={() => openFullScreen('CO₂ Levels (ppm)', createDataset('CO₂', data.co2, 'rgb(75, 192, 192)', data.labels))}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <FullscreenIcon size={20} />
            </button>
          </div>
          <div className="h-48">
            <Line data={createDataset('CO₂', data.co2, 'rgb(75, 192, 192)', data.labels)} options={commonOptions} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-gray-700 font-medium">Ethylene Levels (ppb)</h3>
            <button
              onClick={() => openFullScreen('Ethylene Levels (ppb)', createDataset('Ethylene', data.ethylene, 'rgb(153, 102, 255)', data.labels))}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <FullscreenIcon size={20} />
            </button>
          </div>
          <div className="h-48">
            <Line data={createDataset('Ethylene', data.ethylene, 'rgb(153, 102, 255)', data.labels)} options={commonOptions} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-gray-700 font-medium">Alcohol Levels (ppm)</h3>
            <button
              onClick={() => openFullScreen('Alcohol Levels (ppm)', createDataset('Alcohol', data.alcohol, 'rgb(255, 159, 64)', data.labels))}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <FullscreenIcon size={20} />
            </button>
          </div>
          <div className="h-48">
            <Line data={createDataset('Alcohol', data.alcohol, 'rgb(255, 159, 64)', data.labels)} options={commonOptions} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-gray-700 font-medium">VOC Index</h3>
            <button
              onClick={() => openFullScreen('VOC Index', createDataset('VOC', data.voc, 'rgb(255, 99, 132)', data.labels))}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <FullscreenIcon size={20} />
            </button>
          </div>
          <div className="h-48">
            <Line data={createDataset('VOC', data.voc, 'rgb(255, 99, 132)', data.labels)} options={commonOptions} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-gray-700 font-medium">Temperature (°C)</h3>
            <button
              onClick={() => openFullScreen('Temperature (°C)', createDataset('Temperature', data.temperature, 'rgb(255, 205, 86)', data.labels))}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <FullscreenIcon size={20} />
            </button>
          </div>
          <div className="h-48">
            <Line data={createDataset('Temperature', data.temperature, 'rgb(255, 205, 86)', data.labels)} options={commonOptions} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-gray-700 font-medium">Humidity (%)</h3>
            <button
              onClick={() => openFullScreen('Humidity (%)', createDataset('Humidity', data.humidity, 'rgb(54, 162, 235)', data.labels))}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <FullscreenIcon size={20} />
            </button>
          </div>
          <div className="h-48">
            <Line data={createDataset('Humidity', data.humidity, 'rgb(54, 162, 235)', data.labels)} options={commonOptions} />
          </div>
        </div>
      </div>

      {fullScreenGraph && (
        <FullScreenGraph
          title={fullScreenGraph.title}
          data={fullScreenGraph.data}
          options={fullScreenGraph.options}
          onClose={() => setFullScreenGraph(null)}
        />
      )}
    </div>
  );
};

export default LiveGraphs;