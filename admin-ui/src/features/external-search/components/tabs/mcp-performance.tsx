/**
 * MCP Performance Tab Component
 * 
 * Displays performance metrics and statistics for external search.
 */

'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useMCPStats } from '../../hooks/use-mcp-stats';

export function MCPPerformanceTab() {
  const { data, isLoading, refetch } = useMCPStats();

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-16 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground mb-4">Performance data not available</p>
        <Button onClick={refetch} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  const stats = data.stats;
  const cacheHitRate = stats.total_searches > 0 
    ? (stats.cache_hits / (stats.cache_hits + stats.cache_misses)) * 100 
    : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">Performance Overview</h3>
          <p className="text-sm text-muted-foreground">
            Last {data.collection_period_hours} hours of activity
          </p>
        </div>
        <Button onClick={refetch} variant="outline" size="sm">
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Searches</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total_searches.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              External search requests
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Cache Hit Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{cacheHitRate.toFixed(1)}%</div>
            <Progress value={cacheHitRate} className="mt-2" />
            <p className="text-xs text-muted-foreground mt-1">
              {stats.cache_hits} hits / {stats.cache_misses} misses
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.avg_response_time_ms.toFixed(0)}ms</div>
            <p className="text-xs text-muted-foreground">
              Average response time
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Hedged Requests</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.hedged_requests}</div>
            <p className="text-xs text-muted-foreground">
              Backup providers triggered
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Provider Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Provider Performance</CardTitle>
          <CardDescription>
            Individual performance metrics for each external search provider.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stats.provider_stats.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No provider statistics available
            </div>
          ) : (
            <div className="space-y-4">
              {stats.provider_stats.map((provider) => {
                const successRate = provider.total_requests > 0 
                  ? (provider.successful_requests / provider.total_requests) * 100 
                  : 0;

                return (
                  <div key={provider.provider_id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-3">
                        <h4 className="font-medium">{provider.provider_id}</h4>
                        <Badge variant={provider.circuit_breaker_open ? 'destructive' : 'default'}>
                          {provider.circuit_breaker_open ? 'Circuit Open' : 'Active'}
                        </Badge>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {provider.avg_response_time_ms.toFixed(0)}ms avg
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-4 gap-4 text-sm">
                      <div>
                        <div className="text-muted-foreground">Total Requests</div>
                        <div className="font-medium">{provider.total_requests}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Success Rate</div>
                        <div className="font-medium">{successRate.toFixed(1)}%</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Failed Requests</div>
                        <div className="font-medium">{provider.failed_requests}</div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">24h Requests</div>
                        <div className="font-medium">{provider.last_24h_requests}</div>
                      </div>
                    </div>
                    
                    <Progress value={successRate} className="mt-3" />
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* System Health */}
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
          <CardDescription>
            Overall system health and circuit breaker status.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="text-sm text-muted-foreground mb-2">Circuit Breakers</div>
              <div className="text-2xl font-bold">
                {stats.circuit_breaks}
              </div>
              <div className="text-sm text-muted-foreground">
                Total activations
              </div>
            </div>
            
            <div>
              <div className="text-sm text-muted-foreground mb-2">Data Collection</div>
              <div className="text-sm">
                Period: {data.collection_period_hours} hours
              </div>
              <div className="text-sm text-muted-foreground">
                Reset: {new Date(data.last_reset).toLocaleString()}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}