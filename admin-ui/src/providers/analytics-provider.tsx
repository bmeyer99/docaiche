'use client';

import { useEffect } from 'react';
import CleanAnalyticsManager from '@/lib/clean-analytics-manager';
import { useAnalyticsStore } from '@/stores/analytics-store';
import { browserLogger } from '@/lib/utils/browser-logger';

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Only initialize in browser environment
    if (typeof window === 'undefined') return;
    
    browserLogger.info('AnalyticsProvider: Initializing Clean WebSocket connection');
    
    // Initialize WebSocket connection on app mount
    const wsManager = CleanAnalyticsManager.getInstance();
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${wsProtocol}//${window.location.host}/ws/analytics/clean`;
    
    wsManager.connect(url);
    
    // Subscribe to time range changes to send updates
    const unsubscribe = useAnalyticsStore.subscribe(
      (state) => state.timeRange,
      (timeRange) => {
        browserLogger.debug('AnalyticsProvider: Time range changed', { timeRange });
        wsManager.sendTimeRange(timeRange);
      }
    );
    
    return () => {
      browserLogger.debug('AnalyticsProvider: Cleaning up');
      unsubscribe();
      // Note: We don't disconnect here because we want to keep the connection alive
      // for background data loading even when components unmount
    };
  }, []);
  
  return <>{children}</>;
}