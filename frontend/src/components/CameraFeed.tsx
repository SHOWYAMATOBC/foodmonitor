import React, { useCallback, useRef, useState, useEffect } from 'react';
import Webcam from 'react-webcam';

const CameraFeed: React.FC = () => {
  const webcamRef = useRef<Webcam>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [aspectRatio, setAspectRatio] = useState<number>(16/9);

  const videoConstraints = {
    width: 1280,
    height: 720,
    facingMode: "user",
    aspectRatio: 16/9
  };

  const toggleFullscreen = useCallback(async () => {
    if (!document.fullscreenElement && containerRef.current) {
      try {
        await containerRef.current.requestFullscreen();
        setIsFullscreen(true);
      } catch (err) {
        console.error("Error attempting to enable fullscreen:", err);
      }
    } else {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  }, []);

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  useEffect(() => {
    const updateAspectRatio = () => {
      if (webcamRef.current && webcamRef.current.video) {
        const { videoWidth, videoHeight } = webcamRef.current.video;
        setAspectRatio(videoWidth / videoHeight);
      }
    };

    if (webcamRef.current && webcamRef.current.video) {
      webcamRef.current.video.addEventListener('loadedmetadata', updateAspectRatio);
    }

    return () => {
      if (webcamRef.current && webcamRef.current.video) {
        webcamRef.current.video.removeEventListener('loadedmetadata', updateAspectRatio);
      }
    };
  }, []);

  return (
    <div 
      ref={containerRef}
      className={`relative ${isFullscreen ? 'fixed inset-0 z-50 bg-black' : ''}`}
      style={{ 
        width: isFullscreen ? '100vw' : '100%',
        maxWidth: isFullscreen ? '100vw' : '1280px',
        margin: '0 auto'
      }}
    >
      <div 
        className={`relative bg-gray-900 ${
          isFullscreen ? 'w-screen h-screen' : 'rounded-lg overflow-hidden'
        }`}
        style={{
          aspectRatio: '16/9',
          width: '100%',
          height: 'auto'
        }}
      >
        <Webcam
          audio={false}
          ref={webcamRef}
          screenshotFormat="image/jpeg"
          videoConstraints={videoConstraints}
          className="w-full h-full object-cover"
          style={{
            aspectRatio: '16/9',
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            transform: 'scaleX(-1)'
          }}
        />
        <div className="absolute top-0 right-0 p-4 flex gap-2">
          <button
            onClick={toggleFullscreen}
            className="px-4 py-2 bg-black bg-opacity-50 text-white rounded-lg hover:bg-opacity-75 transition-all flex items-center gap-2"
          >
            <span>{isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default CameraFeed;