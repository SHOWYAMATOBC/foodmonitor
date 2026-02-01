import React from 'react';

interface FoodStatusProps {
  name: string;
  status: 'Fresh' | 'Stale' | 'Spoiled';
  predictedSpoilDate: string; // ISO date or formatted string
}

const badgeColor = (status: FoodStatusProps['status']) => {
  switch (status) {
    case 'Fresh': return 'bg-green-100 text-green-800';
    case 'Stale': return 'bg-yellow-100 text-yellow-800';
    case 'Spoiled': return 'bg-red-100 text-red-800';
  }
};

const FoodStatusPanel: React.FC<FoodStatusProps> = ({ name, status, predictedSpoilDate }) => {
  return (
    <div className="bg-white rounded-lg shadow p-4 mt-6 max-w-xl">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-lg font-semibold">{name}</h4>
          <div className="text-sm text-gray-500">Estimated freshness and spoil date</div>
        </div>
        <div className={`px-3 py-1 rounded-full text-sm ${badgeColor(status)}`}>{status}</div>
      </div>

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <div className="text-sm text-gray-500">Predicted spoil date</div>
          <div className="text-lg font-medium">{predictedSpoilDate}</div>
        </div>
        <div>
          <div className="text-sm text-gray-500">Notes</div>
          <div className="text-sm text-gray-700">Prediction based on recent sensor trends (VOC, ethylene, temperature and humidity). Integrate ML model for accurate results.</div>
        </div>
      </div>
    </div>
  );
};

export default FoodStatusPanel;
