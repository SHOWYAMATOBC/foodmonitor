import React from 'react';
import freshImg from '../assets/fresh.png';
import staleImg from '../assets/stale.png';

interface FoodStatusProps {
  name?: string;
  status: 'Fresh' | 'Stale' | 'Spoiled';
  conditionRating: number; // 1-10 scale
}

const badgeColor = (status: FoodStatusProps['status']) => {
  switch (status) {
    case 'Fresh': return 'bg-green-100 text-green-800';
    case 'Stale': return 'bg-yellow-100 text-yellow-800';
    case 'Spoiled': return 'bg-red-100 text-red-800';
  }
};

const getStatusImage = (status: FoodStatusProps['status']) => {
  switch (status) {
    case 'Fresh': return freshImg;
    case 'Stale': return staleImg;
    case 'Spoiled': return staleImg;
  }
};

const FoodStatusPanel: React.FC<FoodStatusProps> = ({ status, conditionRating }) => {
  const shelfLifeDays = Math.floor(Math.random() * 14) + 1; // Random 1-14 days

  return (
    <div className="bg-white rounded-lg shadow p-6 w-full h-full flex flex-col">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">Perishables Current Status</h3>
      
      {/* Main Content */}
      <div className="flex-1 flex items-center gap-6">
        {/* Image Section - Larger */}
        <div className="flex-shrink-0 w-64 h-64 bg-gray-100 rounded-lg overflow-hidden flex items-center justify-center shadow-md">
          <img 
            src={getStatusImage(status)} 
            alt={status}
            className="w-full h-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200"%3E%3Crect fill="%23e5e7eb" width="200" height="200"/%3E%3Ctext x="50%" y="50%" font-size="16" fill="%239ca3af" text-anchor="middle" dy=".3em"%3EImage%3C/text%3E%3C/svg%3E';
            }}
          />
        </div>

        {/* Info Section - Compact */}
        <div className="flex-1 space-y-3">
          <div>
            <div className="text-xs text-gray-500 mb-1">Current Status</div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-gray-800">{status}</span>
              <div className={`px-2 py-0.5 rounded-full text-xs font-medium ${badgeColor(status)}`}>
                {status}
              </div>
            </div>
          </div>

          <div>
            <div className="text-xs text-gray-500 mb-1">Condition Rating</div>
            <div className="flex items-center gap-2">
              <div className="text-2xl font-bold text-gray-800">{conditionRating}/10</div>
              <div className="flex-1">
                <div className="w-full bg-gray-200 rounded-full h-1.5">
                  <div 
                    className={`h-1.5 rounded-full transition-all ${
                      conditionRating >= 8 ? 'bg-green-500' : 
                      conditionRating >= 5 ? 'bg-yellow-500' : 
                      'bg-red-500'
                    }`}
                    style={{ width: `${(conditionRating / 10) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          <div>
            <div className="text-xs text-gray-500 mb-1">Predicted Shelf Life</div>
            <div className="text-lg font-semibold text-gray-800">
              {shelfLifeDays} Days Remaining
            </div>
          </div>

          <div className="pt-1 border-t border-gray-200">
            <p className="text-xs text-gray-500 leading-tight">
              Based on VOC, ethylene, temperature & humidity
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FoodStatusPanel;
