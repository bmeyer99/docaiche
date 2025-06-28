import React, { useState, useEffect } from 'react';

const ConnectionStatus: React.FC = () => {
  const [connectionMode, setConnectionMode] = useState<'connected' | 'polling' | 'disconnected'>('disconnected');

  useEffect(() => {
    // Simple connection check - replace with actual WebSocket logic
    const checkConnection = () => {
      try {
        // Simulate connection check
        const isOnline = navigator.onLine;
        if (isOnline) {
          setConnectionMode('connected');
        } else {
          setConnectionMode('disconnected');
        }
      } catch (error) {
        setConnectionMode('polling');
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 5000);

    return () => clearInterval(interval);
  }, []);

  const getStatusDisplay = () => {
    switch (connectionMode) {
      case 'connected':
        return {
          dot: 'w-2 h-2 bg-green-500 rounded-full',
          text: 'Connected'
        };
      case 'polling':
        return {
          dot: 'w-2 h-2 bg-gray-400 rounded-full',
          text: 'Polling Mode'
        };
      default:
        return {
          dot: 'w-2 h-2 bg-red-500 rounded-full',
          text: 'Disconnected'
        };
    }
  };

  const status = getStatusDisplay();

  return (
    <div className="flex items-center space-x-2">
      <div className={status.dot}></div>
      <span className="text-sm text-gray-500">{status.text}</span>
    </div>
  );
};

export default ConnectionStatus;