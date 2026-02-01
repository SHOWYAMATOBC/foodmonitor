import React, { useState, useEffect } from 'react';
import { GoogleMap, LoadScript, Marker } from '@react-google-maps/api';

interface MapViewProps {
  show: boolean;
  onClose: () => void;
}

const containerStyle = {
  width: '100%',
  aspectRatio: '16/9',
  borderRadius: '0.5rem'
};

const defaultCenter = {
  lat: 0,
  lng: 0
};

const MapView: React.FC<MapViewProps> = ({ show, onClose }) => {
  const [currentPosition, setCurrentPosition] = useState(defaultCenter);
  const [error, setError] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (show) {
      setLoading(true);
      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            setCurrentPosition({
              lat: position.coords.latitude,
              lng: position.coords.longitude
            });
            setLoading(false);
          },
          (error) => {
            setError('Error getting location: ' + error.message);
            setLoading(false);
          }
        );
      } else {
        setError('Geolocation is not supported by your browser');
        setLoading(false);
      }
    }
  }, [show]);

  if (!show) return null;

  if (loading) {
    return (
      <div className="my-8">
        <div className="bg-white rounded-lg shadow-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-xl text-gray-600">Loading location...</div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="my-8">
        <div className="bg-white rounded-lg shadow-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-xl text-red-600">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="my-8">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <LoadScript googleMapsApiKey={process.env.REACT_APP_GOOGLE_MAPS_API_KEY || ''}>
          <GoogleMap
            mapContainerStyle={containerStyle}
            center={currentPosition}
            zoom={15}
          >
            <Marker position={currentPosition} />
          </GoogleMap>
        </LoadScript>
      </div>
    </div>
  );
};

export default MapView;