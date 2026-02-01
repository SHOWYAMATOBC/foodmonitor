import React from 'react';
import { Line as LineChart } from 'react-chartjs-2';
import { ChartData, ChartOptions } from 'chart.js';
import { AiOutlineClose } from 'react-icons/ai';
import type { ComponentType } from 'react';

// Wrap/cast the icon to React.ComponentType so TypeScript treats it as a
// valid JSX component (returns Element | null). This avoids TS2786.
const CloseIcon = AiOutlineClose as unknown as ComponentType<{ size?: number | string }>;

interface FullScreenGraphProps {
  title: string;
  data: ChartData<'line'>;
  options: ChartOptions<'line'>;
  onClose: () => void;
}

const FullScreenGraph: React.FC<FullScreenGraphProps> = ({
  title,
  data,
  options,
  onClose
}) => {
  return (
    <div className="fixed inset-0 z-50 bg-white">
      <div className="h-full p-6 flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-bold text-gray-800">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <CloseIcon size={24} />
          </button>
        </div>
        <div className="flex-grow min-h-0">
          <div className="h-full">
            <LineChart data={data} options={{ ...options, maintainAspectRatio: false }} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default FullScreenGraph;