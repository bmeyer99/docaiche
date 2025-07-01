/**
 * Hook for MCP Configuration Management
 * 
 * Provides data and operations for managing MCP search configuration.
 */

'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/utils/api-client';
import { useToast } from '@/hooks/use-toast';
import type { MCPConfigResponse, MCPSearchConfig } from '@/lib/config/api';

export function useMCPConfig() {
  const [data, setData] = useState<MCPConfigResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const { toast } = useToast();

  const fetchConfig = async () => {
    try {
      setError(null);
      const response = await apiClient.getMCPConfig();
      setData(response);
    } catch (err) {
      const error = err as Error;
      setError(error);
      console.error('Failed to fetch MCP config:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchConfig();
  }, []);

  const updateConfig = async (config: MCPSearchConfig): Promise<boolean> => {
    try {
      setIsSaving(true);
      const response = await apiClient.updateMCPConfig(config);
      setData(response);
      
      toast({
        title: 'Configuration Updated',
        description: 'MCP search configuration has been successfully updated.',
      });
      
      return true;
    } catch (error) {
      console.error('Failed to update MCP config:', error);
      toast({
        title: 'Update Failed',
        description: 'Failed to update configuration. Please try again.',
        variant: 'destructive',
      });
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  const refetch = () => {
    setIsLoading(true);
    fetchConfig();
  };

  return {
    data,
    isLoading,
    error,
    isSaving,
    updateConfig,
    refetch,
  };
}