import React from 'react';
import { useNavigate } from 'react-router-dom';

const StartPage: React.FC = () => {
  const navigate = useNavigate();

  const handleStart = () => {
    // Simulate backend startup
    console.log('Simulating backend startup...');
    setTimeout(() => {
      navigate('/dashboard');
    }, 1500);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-r from-green-400 to-blue-500">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-white mb-8">
          Fruit & Vegetable Freshness Monitor
        </h1>
        <button
          onClick={handleStart}
          className="px-8 py-4 bg-white text-green-600 rounded-lg shadow-lg hover:shadow-xl transition-all duration-300 text-xl font-semibold"
        >
          Start Project
        </button>
      </div>
    </div>
  );
};

export default StartPage;