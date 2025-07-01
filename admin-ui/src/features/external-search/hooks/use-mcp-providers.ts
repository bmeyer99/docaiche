/**
 * Hook for MCP Providers Management
 * 
 * Provides data and operations for managing external search providers.
 */

'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/utils/api-client';
import { useToast } from '@/hooks/use-toast';
import type { 
  MCPProvidersResponse, 
  MCPProvider, 
  MCPProviderConfig 
} from '@/lib/config/api';

interface UseMCPProvidersOptions {
  enabledOnly?: boolean;
  refetchInterval?: number;
}

export function useMCPProviders(options: UseMCPProvidersOptions = {}) {
  const { enabledOnly = false, refetchInterval = 30000 } = options;
  const [data, setData] = useState<MCPProvidersResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const { toast } = useToast();

  const fetchProviders = async () => {
    try {
      setError(null);
      const response = await apiClient.getMCPProviders(enabledOnly);
      setData(response);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error('Failed to fetch MCP providers:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();

    // Set up polling if refetchInterval is provided
    if (refetchInterval > 0) {
      const interval = setInterval(fetchProviders, refetchInterval);
      return () => clearInterval(interval);
    }
  }, [enabledOnly, refetchInterval]);

  const createProvider = async (config: MCPProviderConfig): Promise<MCPProvider | null> => {
    try {
      const newProvider = await apiClient.createMCPProvider(config);
      
      // Refresh the list
      await fetchProviders();
      
      toast({
        title: 'Provider Created',
        description: `${config.provider_id} has been successfully created.`,
      });
      
      return newProvider;
    } catch (error) {
      console.error('Failed to create provider:', error);
      toast({
        title: 'Creation Failed',
        description: 'Failed to create the provider. Please try again.',
        variant: 'destructive',
      });
      return null;
    }
  };

  const updateProvider = async (
    providerId: string, 
    updates: Partial<MCPProviderConfig>
  ): Promise<MCPProvider | null> => {
    try {
      const updatedProvider = await apiClient.updateMCPProvider(providerId, updates);
      
      // Refresh the list
      await fetchProviders();
      
      toast({
        title: 'Provider Updated',
        description: `${providerId} has been successfully updated.`,
      });
      
      return updatedProvider;
    } catch (error) {
      console.error('Failed to update provider:', error);
      toast({
        title: 'Update Failed',
        description: 'Failed to update the provider. Please try again.',
        variant: 'destructive',
      });
      return null;
    }
  };

  const deleteProvider = async (providerId: string): Promise<boolean> => {
    try {
      await apiClient.deleteMCPProvider(providerId);
      
      // Refresh the list
      await fetchProviders();
      
      toast({
        title: 'Provider Deleted',
        description: `${providerId} has been successfully deleted.`,
      });
      
      return true;
    } catch (error) {
      console.error('Failed to delete provider:', error);
      toast({
        title: 'Deletion Failed',
        description: 'Failed to delete the provider. Please try again.',
        variant: 'destructive',
      });
      return false;
    }
  };

  const testProvider = async (providerId: string, testQuery: string = 'test') => {
    try {
      const result = await apiClient.testMCPProvider(providerId, testQuery);
      
      if (result.success) {
        toast({
          title: 'Test Successful',
          description: `${providerId} responded in ${result.response_time_ms}ms with ${result.results_count} results.`,
        });
      } else {
        toast({
          title: 'Test Failed',
          description: result.error_message || 'Provider test failed.',
          variant: 'destructive',
        });
      }
      
      return result;
    } catch (error) {
      console.error('Failed to test provider:', error);
      toast({
        title: 'Test Error',
        description: 'Failed to test the provider. Please try again.',
        variant: 'destructive',
      });
      return null;
    }
  };

  const refetch = () => {
    setIsLoading(true);
    fetchProviders();
  };

  return {
    data,
    isLoading,
    error,
    refetch,
    createProvider,
    updateProvider,
    deleteProvider,
    testProvider,
  };
}