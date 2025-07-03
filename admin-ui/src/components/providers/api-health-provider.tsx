'use client';

import React, { createContext, useContext, useEffect, useRef, useState, ReactNode } from 'react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { useAppStore } from '@/lib/store';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2, WifiOff } from 'lucide-react';

interface ApiHealthContextValue {
  status: 'connected' | 'degraded' | 'disconnected';
  lastCheck: Date | null;
  error: string | null;
  checkHealth: () => Promise<void>;
}

const ApiHealthContext = createContext<ApiHealthContextValue | null>(null);

export function useApiHealth() {
  const context = useContext(ApiHealthContext);
  if (!context) {
    throw new Error('useApiHealth must be used within ApiHealthProvider');
  }
  return context;
}

interface ApiHealthProviderProps {
  children: ReactNode;
}

export function ApiHealthProvider({ children }: ApiHealthProviderProps) {
  const [status, setStatus] = useState<'connected' | 'degraded' | 'disconnected'>('connected');
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastNotificationStatus, setLastNotificationStatus] = useState<string | null>(null);
  
  const apiClient = useApiClient();
  const { toast, dismiss, warning } = useToast();
  const setServiceHealth = useAppStore((state) => state.setServiceHealth);
  const checkIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const notificationToastIdRef = useRef<string | null>(null);

  const checkHealth = async () => {
    try {
      const startTime = Date.now();
      const response = await apiClient.getHealth();
      const latency = Date.now() - startTime;
      const now = new Date();
      setLastCheck(now);
      
      // Determine status based on response
      let newStatus: 'connected' | 'degraded' | 'disconnected' = 'connected';
      
      if (response.overall_status === 'healthy') {
        newStatus = 'connected';
        setError(null);
      } else if (response.overall_status === 'degraded') {
        newStatus = 'degraded';
        setError('API is experiencing degraded performance');
      } else {
        newStatus = 'disconnected';
        setError('API is unhealthy');
      }
      
      setStatus(newStatus);
      
      // Update store with API health
      setServiceHealth('api', { 
        status: response.overall_status || 'unhealthy',
        latency: latency
      });

      // Show notification if status changed
      if (newStatus !== lastNotificationStatus && lastNotificationStatus !== null) {
        // Dismiss previous notification if exists
        if (notificationToastIdRef.current) {
          dismiss(notificationToastIdRef.current);
        }

        if (newStatus === 'degraded') {
          const toastId = `api-health-${Date.now()}`;
          notificationToastIdRef.current = toastId;
          warning("API Performance Degraded", "The API is experiencing degraded performance. Some features may be slow.", {
            id: toastId,
            duration: 999999, // Very long duration instead of Infinity
          });
        } else if (newStatus === 'disconnected') {
          const toastId = `api-health-${Date.now()}`;
          notificationToastIdRef.current = toastId;
          toast({
            id: toastId,
            title: "API Disconnected",
            description: "Unable to connect to the API server. Please check your connection.",
            variant: "destructive",
            duration: 999999, // Very long duration instead of Infinity
          });
        } else if (newStatus === 'connected' && (lastNotificationStatus === 'degraded' || lastNotificationStatus === 'disconnected')) {
          // Clear any existing notification
          if (notificationToastIdRef.current) {
            dismiss(notificationToastIdRef.current);
            notificationToastIdRef.current = null;
          }
          // Show success notification
          toast({
            title: "API Connected",
            description: "Connection to the API server has been restored.",
            variant: "default",
            duration: 3000,
          });
        }
      }
      
      setLastNotificationStatus(newStatus);
      
    } catch (err) {
      // Connection failed
      setStatus('disconnected');
      setError(err instanceof Error ? err.message : 'Failed to connect to API');
      setLastCheck(new Date());
      
      // Update store
      setServiceHealth('api', { 
        status: 'unhealthy',
        error: err instanceof Error ? err.message : 'Connection failed'
      });

      // Show notification if this is a new disconnection
      if (lastNotificationStatus !== 'disconnected') {
        // Dismiss previous notification if exists
        if (notificationToastIdRef.current) {
          dismiss(notificationToastIdRef.current);
        }

        const toastId = `api-health-${Date.now()}`;
        notificationToastIdRef.current = toastId;
        toast({
          id: toastId,
          title: "API Connection Lost",
          description: "Unable to connect to the API server. Retrying...",
          variant: "destructive",
          duration: 999999,
        });
        setLastNotificationStatus('disconnected');
      }
    }
  };

  // Initial health check
  useEffect(() => {
    checkHealth();
  }, []);

  // Set up interval for health checks every 5 minutes
  useEffect(() => {
    // Start interval
    checkIntervalRef.current = setInterval(() => {
      checkHealth();
    }, 300000); // 5 minutes

    // Cleanup
    return () => {
      if (checkIntervalRef.current) {
        clearInterval(checkIntervalRef.current);
      }
      // Dismiss any active notification
      if (notificationToastIdRef.current) {
        dismiss(notificationToastIdRef.current);
      }
    };
  }, [lastNotificationStatus]); // Re-create interval when notification status changes

  // Monitor online/offline events
  useEffect(() => {
    const handleOnline = () => {
      checkHealth(); // Check immediately when coming online
    };
    
    const handleOffline = () => {
      setStatus('disconnected');
      setError('Device is offline');
      setServiceHealth('api', { 
        status: 'unhealthy',
        error: 'Device offline'
      });
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const contextValue: ApiHealthContextValue = {
    status,
    lastCheck,
    error,
    checkHealth,
  };

  return (
    <ApiHealthContext.Provider value={contextValue}>
      {children}
      {/* Global API status banner for critical issues */}
      {status === 'disconnected' && (
        <div className="fixed bottom-0 left-0 right-0 z-50 p-4 bg-red-50 dark:bg-red-950 border-t border-red-200 dark:border-red-800">
          <Alert variant="destructive" className="max-w-4xl mx-auto">
            <WifiOff className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>API connection lost. Some features may be unavailable.</span>
              <span className="text-xs opacity-75">
                Last checked: {lastCheck ? new Date(lastCheck).toLocaleTimeString() : 'Never'}
              </span>
            </AlertDescription>
          </Alert>
        </div>
      )}
    </ApiHealthContext.Provider>
  );
}

// Connection Status Indicator Component
export function ConnectionStatusIndicator() {
  const { status, lastCheck } = useApiHealth();
  
  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'text-green-600 dark:text-green-400';
      case 'degraded':
        return 'text-orange-600 dark:text-orange-400';
      case 'disconnected':
        return 'text-red-600 dark:text-red-400';
    }
  };
  
  const getStatusIcon = () => {
    switch (status) {
      case 'connected':
        return <CheckCircle2 className="w-4 h-4" />;
      case 'degraded':
        return <AlertCircle className="w-4 h-4" />;
      case 'disconnected':
        return <WifiOff className="w-4 h-4" />;
    }
  };
  
  const getStatusText = () => {
    switch (status) {
      case 'connected':
        return 'Connected';
      case 'degraded':
        return 'Degraded';
      case 'disconnected':
        return 'Disconnected';
    }
  };

  return (
    <div className={`flex items-center gap-2 text-sm ${getStatusColor()}`}>
      {getStatusIcon()}
      <span className="font-medium">{getStatusText()}</span>
    </div>
  );
}