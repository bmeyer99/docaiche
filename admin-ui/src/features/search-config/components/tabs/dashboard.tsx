'use client';

/**
 * Dashboard tab component - Overview of search system health and metrics
 */

import React, { useEffect, useState } from 'react';
import { useQueueMetrics, useSystemHealth } from '../../hooks/use-search-config-websocket';
import { MetricCard } from '../shared/metric-card';
import { HealthIndicator } from '../shared/health-indicator';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { RefreshCw, Search, Zap, Database, Bot, Globe } from 'lucide-react';

interface DashboardProps {
  onChangeDetected?: () => void;
}

export function SearchConfigDashboard({ onChangeDetected }: DashboardProps) {
  const { currentDepth, processingRate, history } = useQueueMetrics();
  const { healthStatus, overallHealth } = useSystemHealth();
  const [metrics, setMetrics] = useState({
    totalSearches: 0,
    avgLatency: 0,
    cacheHitRate: 0,
    errorRate: 0,
    activeProviders: 0,
    vectorWorkspaces: 0
  });
  const [recentSearches, setRecentSearches] = useState<any[]>([]);
  const [searchVolumeData, setSearchVolumeData] = useState<any[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Fetch real metrics data
  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      // Fetch system metrics
      const response = await fetch('/api/v1/metrics/dashboard');
      if (response.ok) {
        const data = await response.json();
        setMetrics({
          totalSearches: data.total_searches_24h || 0,
          avgLatency: data.avg_latency_ms || 0,
          cacheHitRate: data.cache_hit_rate || 0,
          errorRate: data.error_rate || 0,
          activeProviders: data.active_providers || 0,
          vectorWorkspaces: data.vector_workspaces || 0
        });
        
        if (data.search_volume_hourly) {
          setSearchVolumeData(data.search_volume_hourly);
        }
        
        if (data.recent_searches) {
          setRecentSearches(data.recent_searches);
        }
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      // Keep existing values on error
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await fetchMetrics();
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Search System Overview</h2>
        <Button 
          variant="outline" 
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Searches (24h)"
          value={metrics.totalSearches.toLocaleString()}
          change={12.5}
          trend="up"
          icon={<Search className="h-4 w-4" />}
        />
        <MetricCard
          title="Avg Latency"
          value={`${metrics.avgLatency}ms`}
          change={-5.2}
          trend="down"
          icon={<Zap className="h-4 w-4" />}
        />
        <MetricCard
          title="Cache Hit Rate"
          value={`${(metrics.cacheHitRate * 100).toFixed(0)}%`}
          change={3.1}
          trend="up"
          icon={<Database className="h-4 w-4" />}
        />
        <MetricCard
          title="Error Rate"
          value={`${(metrics.errorRate * 100).toFixed(1)}%`}
          change={-0.5}
          trend="down"
          icon={<Globe className="h-4 w-4" />}
        />
      </div>

      {/* System Health */}
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Configuration</p>
              <HealthIndicator status={healthStatus.configuration?.status || 'unknown'} />
            </div>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Vector Search</p>
              <HealthIndicator status={healthStatus.vector_search?.status || 'unknown'} />
            </div>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Text AI</p>
              <HealthIndicator status={healthStatus.text_ai?.status || 'unknown'} />
            </div>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Providers</p>
              <HealthIndicator status={healthStatus.providers?.status || 'unknown'} />
            </div>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Queue System</p>
              <HealthIndicator status={healthStatus.queue?.status || 'unknown'} />
            </div>
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Cache</p>
              <HealthIndicator status={healthStatus.cache?.status || 'unknown'} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Search Volume Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Search Volume (24h)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={searchVolumeData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" />
                  <YAxis />
                  <Tooltip />
                  <Area 
                    type="monotone" 
                    dataKey="searches" 
                    stroke="#8884d8" 
                    fill="#8884d8" 
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Queue Depth Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Queue Depth & Processing Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Current Depth</p>
                  <p className="text-2xl font-bold">{currentDepth}/100</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Processing Rate</p>
                  <p className="text-2xl font-bold">{processingRate.toFixed(1)}/s</p>
                </div>
              </div>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={history.slice(-20)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" />
                    <YAxis />
                    <Tooltip />
                    <Line 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#82ca9d" 
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Search Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Query</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Latency</TableHead>
                <TableHead>Results</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentSearches.length > 0 ? (
                recentSearches.slice(0, 5).map((search, i) => (
                  <TableRow key={i}>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(search.timestamp).toLocaleTimeString()}
                    </TableCell>
                    <TableCell className="font-medium">{search.query || 'N/A'}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Database className="h-3 w-3" />
                        <span className="text-sm">{search.type || 'Vector'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm">{search.latency_ms || 0}ms</span>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm">{search.results_count || 0}</span>
                    </TableCell>
                    <TableCell>
                      <HealthIndicator status={search.status || 'unknown'} showLabel={false} size="sm" />
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground">
                    No recent search activity
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}