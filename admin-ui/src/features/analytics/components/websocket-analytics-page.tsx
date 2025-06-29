'use client';

import { useState, useEffect } from 'react';
import { useAnalyticsWebSocket } from '@/lib/hooks/use-websocket';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Icons } from '@/components/icons';
import { 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  LineChart, 
  Line, 
  PieChart, 
  Pie, 
  Cell, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend
} from 'recharts';

// Color palette for charts
const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
  '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
];

export default function WebSocketAnalyticsPage() {
  const [timeRange, setTimeRange] = useState('24h');
  const [chartType, setChartType] = useState<'line' | 'area' | 'bar'>('area');
  
  // Always connect WebSocket - monitoring should always be available
  const { analytics, stats, isConnected, error } = useAnalyticsWebSocket(timeRange, true);

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDuration = (ms: number) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms}ms`;
  };

  // Transform analytics data for charts
  const getSearchTrendData = () => {
    if (!analytics?.searchMetrics?.queriesByHour) return [];
    return analytics.searchMetrics.queriesByHour.map((item: any, index: number) => ({
      hour: `${index}:00`,
      searches: item.count || 0,
      responseTime: item.responseTime || 0
    }));
  };

  const getTechnologyData = () => {
    if (!analytics?.contentMetrics?.documentsByTechnology) return [];
    return analytics.contentMetrics.documentsByTechnology;
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header with WebSocket Status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Real-time Analytics</h1>
          <p className="text-muted-foreground">
            Live dashboard with WebSocket updates
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
            <span className="text-sm text-muted-foreground">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="24h">Last 24h</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Connection Error Alert */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <Icons.alertCircle className="w-5 h-5 text-red-600" />
            <div>
              <div className="font-medium text-red-800">Connection Error</div>
              <div className="text-sm text-red-600">{error.message}</div>
            </div>
          </div>
        </div>
      )}

      {/* Key Metrics */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Searches
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatNumber(stats.search_stats?.total_searches || 0)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {stats.search_stats?.cache_hit_rate 
                  ? `${(stats.search_stats.cache_hit_rate * 100).toFixed(1)}% cache hit`
                  : 'No cache data'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Avg Response Time
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatDuration(stats.search_stats?.avg_response_time_ms || 0)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Per search query
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Documents
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {formatNumber(stats.content_stats?.total_documents || 0)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Across {stats.content_stats?.workspaces || 0} workspaces
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                System Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="bg-green-100 text-green-700">
                  Healthy
                </Badge>
                <span className="text-sm text-muted-foreground">
                  All systems operational
                </span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      {analytics && (
        <Tabs defaultValue="search" className="space-y-4">
          <TabsList>
            <TabsTrigger value="search">Search Analytics</TabsTrigger>
            <TabsTrigger value="content">Content Analytics</TabsTrigger>
            <TabsTrigger value="system">System Metrics</TabsTrigger>
          </TabsList>

          <TabsContent value="search" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Search Volume</CardTitle>
                    <CardDescription>
                      Search queries over time
                    </CardDescription>
                  </div>
                  <Select value={chartType} onValueChange={(value: any) => setChartType(value)}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="line">Line</SelectItem>
                      <SelectItem value="area">Area</SelectItem>
                      <SelectItem value="bar">Bar</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    {chartType === 'area' ? (
                      <AreaChart data={getSearchTrendData()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="hour" />
                        <YAxis />
                        <Tooltip />
                        <Area 
                          type="monotone" 
                          dataKey="searches" 
                          stroke="#3b82f6" 
                          fill="#3b82f6" 
                          fillOpacity={0.2}
                        />
                      </AreaChart>
                    ) : chartType === 'bar' ? (
                      <BarChart data={getSearchTrendData()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="hour" />
                        <YAxis />
                        <Tooltip />
                        <Bar dataKey="searches" fill="#3b82f6" />
                      </BarChart>
                    ) : (
                      <LineChart data={getSearchTrendData()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="hour" />
                        <YAxis />
                        <Tooltip />
                        <Line 
                          type="monotone" 
                          dataKey="searches" 
                          stroke="#3b82f6" 
                          strokeWidth={2}
                        />
                      </LineChart>
                    )}
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Top Queries */}
            <Card>
              <CardHeader>
                <CardTitle>Top Search Queries</CardTitle>
                <CardDescription>Most popular search terms</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {analytics.searchMetrics?.topQueries?.slice(0, 10).map((query: any, index: number) => (
                    <div key={index} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{index + 1}.</span>
                        <span className="text-sm">{query.query}</span>
                      </div>
                      <Badge variant="secondary">{query.count} searches</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="content" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Content Distribution</CardTitle>
                <CardDescription>Documents by technology</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={getTechnologyData()}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="count"
                      >
                        {getTechnologyData().map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="system" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle>Cache Performance</CardTitle>
                  <CardDescription>Cache hit/miss statistics</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm">Hit Rate</span>
                        <span className="text-sm font-medium">
                          {((stats?.cache_stats?.hit_rate || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-green-600 h-2 rounded-full" 
                          style={{ width: `${(stats?.cache_stats?.hit_rate || 0) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Total Keys</p>
                        <p className="font-medium">{formatNumber(stats?.cache_stats?.total_keys || 0)}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Memory Usage</p>
                        <p className="font-medium">{stats?.cache_stats?.memory_usage_mb || 0} MB</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>System Resources</CardTitle>
                  <CardDescription>Current resource utilization</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm">CPU Usage</span>
                        <span className="text-sm font-medium">
                          {stats?.system_stats?.cpu_usage_percent?.toFixed(1) || 0}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-600 h-2 rounded-full" 
                          style={{ width: `${stats?.system_stats?.cpu_usage_percent || 0}%` }}
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Memory</p>
                        <p className="font-medium">{stats?.system_stats?.memory_usage_mb || 0} MB</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Disk</p>
                        <p className="font-medium">{stats?.system_stats?.disk_usage_mb || 0} MB</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}