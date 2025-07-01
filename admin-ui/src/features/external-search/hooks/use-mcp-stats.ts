/**
 * Hook for MCP Performance Statistics
 * 
 * Provides data for monitoring MCP performance metrics.
 */

'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/utils/api-client';
import type { MCPStatsResponse } from '@/lib/config/api';

interface UseMCPStatsOptions {
  refetchInterval?: number;
}

export function useMCPStats(options: UseMCPStatsOptions = {}) {
  const { refetchInterval = 30000 } = options;
  const [data, setData] = useState<MCPStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchStats = async () => {
    try {
      setError(null);
      const response = await apiClient.getMCPStats();
      setData(response);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error('Failed to fetch MCP stats:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();

    // Set up polling if refetchInterval is provided
    if (refetchInterval > 0) {
      const interval = setInterval(fetchStats, refetchInterval);
      return () => clearInterval(interval);
    }
  }, [refetchInterval]);

  const refetch = () => {
    setIsLoading(true);
    fetchStats();
  };

  return {
    data,
    isLoading,
    error,
    refetch,
  };
}