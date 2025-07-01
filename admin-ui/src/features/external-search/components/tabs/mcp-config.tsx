/**
 * MCP Configuration Tab Component
 * 
 * Manages MCP search configuration settings.
 */

'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useMCPConfig } from '../../hooks/use-mcp-config';

export function MCPConfigTab() {
  const { data, isLoading, isSaving, updateConfig } = useMCPConfig();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">Configuration not available</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Search Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Search Configuration</CardTitle>
          <CardDescription>
            Configure how external search providers are used to enhance search results.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base">Enable External Search</Label>
              <div className="text-sm text-muted-foreground">
                Allow search results to be enhanced with external providers
              </div>
            </div>
            <Switch 
              checked={data.config.enable_external_search}
              disabled={isSaving}
            />
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base">Hedged Requests</Label>
              <div className="text-sm text-muted-foreground">
                Start backup provider if primary is slow
              </div>
            </div>
            <Switch 
              checked={data.config.enable_hedged_requests}
              disabled={isSaving}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Hedged Delay (seconds)</Label>
              <Input 
                type="number" 
                min="0.1" 
                max="1.0" 
                step="0.1"
                value={data.config.hedged_delay_seconds}
                disabled={isSaving}
              />
            </div>
            <div className="space-y-2">
              <Label>Max Concurrent Providers</Label>
              <Input 
                type="number" 
                min="1" 
                max="5"
                value={data.config.max_concurrent_providers}
                disabled={isSaving}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>External Search Threshold</Label>
            <Input 
              type="number" 
              min="0.0" 
              max="1.0" 
              step="0.1"
              value={data.config.external_search_threshold}
              disabled={isSaving}
            />
            <div className="text-sm text-muted-foreground">
              Quality score below which external search is triggered (0.0 - 1.0)
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Cache Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Cache Configuration</CardTitle>
          <CardDescription>
            Configure caching for improved performance and reduced API calls.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>L1 Cache Size</Label>
              <Input 
                type="number" 
                min="10" 
                max="1000"
                value={data.cache_config.l1_cache_size}
                disabled={isSaving}
              />
              <div className="text-sm text-muted-foreground">
                In-memory cache entries
              </div>
            </div>
            <div className="space-y-2">
              <Label>L2 Cache TTL (seconds)</Label>
              <Input 
                type="number" 
                min="300" 
                max="86400"
                value={data.cache_config.l2_cache_ttl}
                disabled={isSaving}
              />
              <div className="text-sm text-muted-foreground">
                Redis cache time-to-live
              </div>
            </div>
          </div>

          <Separator />

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base">Enable Compression</Label>
              <div className="text-sm text-muted-foreground">
                Compress cached values to save memory
              </div>
            </div>
            <Switch 
              checked={data.cache_config.enable_compression}
              disabled={isSaving}
            />
          </div>

          <div className="space-y-2">
            <Label>Compression Threshold (bytes)</Label>
            <Input 
              type="number" 
              min="512" 
              max="10240"
              value={data.cache_config.compression_threshold}
              disabled={isSaving}
            />
          </div>
        </CardContent>
      </Card>

      {/* Performance Monitoring */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Monitoring</CardTitle>
          <CardDescription>
            Monitor and optimize external search performance.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base">Enable Performance Monitoring</Label>
              <div className="text-sm text-muted-foreground">
                Track performance metrics and statistics
              </div>
            </div>
            <Switch 
              checked={data.config.enable_performance_monitoring}
              disabled={isSaving}
            />
          </div>

          <div className="space-y-2">
            <Label>Cache TTL (seconds)</Label>
            <Input 
              type="number" 
              min="300" 
              max="86400"
              value={data.config.cache_ttl_seconds}
              disabled={isSaving}
            />
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      <div className="flex justify-end space-x-2">
        <Button variant="outline" disabled={isSaving}>
          Reset to Defaults
        </Button>
        <Button disabled={isSaving}>
          {isSaving ? 'Saving...' : 'Save Configuration'}
        </Button>
      </div>

      {/* Status */}
      <div className="text-sm text-muted-foreground">
        Last updated: {new Date(data.last_updated).toLocaleString()}
      </div>
    </div>
  );
}