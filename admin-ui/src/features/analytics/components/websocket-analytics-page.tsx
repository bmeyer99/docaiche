'use client';

import { useState } from 'react';
import { useAnalyticsWebSocket } from '@/lib/hooks/use-websocket';
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
  ResponsiveContainer
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
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
      {/* Header with WebSocket Status */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">TEST CHANGES WORKING - DocAIche Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time system monitoring and analytics
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

      {/* System Health Overview */}
      {analytics?.systemHealth && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Icons.activity className="w-5 h-5" />
              System Health Overview
            </CardTitle>
            <CardDescription>
              Real-time status of all system components organized by service group
            </CardDescription>
          </CardHeader>
          <CardContent>
            {(() => {
              // Group services by their category
              const serviceGroups = {
                infrastructure: { title: 'Core Infrastructure', icon: '🏗️', services: [] as any[] },
                search_ai: { title: 'Search & AI Services', icon: '🔍', services: [] as any[] },
                monitoring: { title: 'Monitoring & Operations', icon: '📊', services: [] as any[] }
              };

              // Categorize services and group API endpoints
              const apiEndpoints: any[] = [];
              
              Object.entries(analytics.systemHealth).forEach(([component, health]: [string, any]) => {
                const group = health.group || 'infrastructure';
                
                // Check if this is an API endpoint
                if (component.startsWith('api_endpoint_')) {
                  apiEndpoints.push({ component, health });
                  return; // Don't add as separate service
                }
                
                if (group in serviceGroups) {
                  serviceGroups[group as keyof typeof serviceGroups].services.push({ component, health });
                }
              });
              
              // TEST - Add visible test marker
              console.log('FRONTEND CHANGES ACTIVE - TEST MARKER');
              console.log('API Endpoints found:', apiEndpoints.length);
              console.log('API Core services:', serviceGroups.infrastructure.services.map(s => s.component));
              
              // Add API endpoints data to the API Core service if it exists
              const apiCoreIndex = serviceGroups.infrastructure.services.findIndex(s => s.component === 'api_core');
              console.log('API Core index:', apiCoreIndex);
              if (apiCoreIndex !== -1) {
                serviceGroups.infrastructure.services[apiCoreIndex].endpoints = apiEndpoints;
                console.log('Added endpoints to API Core:', apiEndpoints.length);
              }

              // Helper function to get status color
              const getStatusColor = (status: string) => {
                switch (status) {
                  case 'healthy': return 'bg-green-500';
                  case 'degraded': return 'bg-yellow-500';
                  case 'unhealthy': 
                  case 'failed': return 'bg-red-500';
                  default: return 'bg-gray-500';
                }
              };

              // Helper function to format component names
              const formatComponentName = (component: string) => {
                // Handle API endpoint names specially
                if (component.startsWith('api_endpoint_')) {
                  const path = component.replace('api_endpoint_', '').replace(/_/g, '/');
                  const pathParts = path.split('/').filter(p => p);
                  if (pathParts.length >= 3) {
                    // Extract meaningful name from path like /api/v1/health -> Health
                    const endpointName = pathParts[pathParts.length - 1];
                    return endpointName
                      .replace(/\b\w/g, l => l.toUpperCase())
                      .replace('Api', 'API')
                      .replace('Ai', 'AI') + ' Endpoint';
                  }
                  return path;
                }
                
                return component
                  .replace(/_/g, ' ')
                  .replace(/\b\w/g, l => l.toUpperCase())
                  .replace('Api Core', 'API Core')
                  .replace('Ai ', 'AI ');
              };

              return (
                <div className="space-y-6">
                  {Object.entries(serviceGroups).map(([groupKey, group]) => {
                    if (group.services.length === 0) return null;
                    
                    // Calculate group health summary
                    const healthyCounts = group.services.filter(s => s.health.status === 'healthy').length;
                    const totalCounts = group.services.length;
                    const groupStatus = healthyCounts === totalCounts ? 'healthy' : 
                                      healthyCounts > 0 ? 'degraded' : 'unhealthy';

                    return (
                      <div key={groupKey} className="space-y-3">
                        <div className="flex items-center gap-3 pb-2 border-b">
                          <span className="text-lg">{group.icon}</span>
                          <div className="flex-1">
                            <h3 className="font-semibold text-base">{group.title}</h3>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <div className={`w-2 h-2 rounded-full ${getStatusColor(groupStatus)}`} />
                              <span>{healthyCounts}/{totalCounts} services healthy</span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                          {group.services.map(({ component, health, endpoints }) => (
                            <div key={component} className="flex items-center justify-between p-3 rounded-lg border bg-card">
                              <div className="flex items-center gap-3 flex-1 min-w-0">
                                <div className={`w-3 h-3 rounded-full ${getStatusColor(health.status)} ${
                                  health.status === 'healthy' ? 'animate-pulse' : ''
                                }`} />
                                <div className="min-w-0 flex-1">
                                  <div className="font-medium text-sm truncate">
                                    {formatComponentName(component)}
                                  </div>
                                  <div className="text-xs text-muted-foreground truncate">
                                    {health.message}
                                  </div>
                                  {health.response_time !== undefined && health.response_time !== null && (
                                    <div className="text-xs text-muted-foreground">
                                      {health.response_time === 0 ? 'idle' : `${health.response_time}ms response`}
                                    </div>
                                  )}
                                  
                                  {/* Show API endpoints as small badges if this is API Core */}
                                  {component === 'api_core' && endpoints && endpoints.length > 0 && (
                                    <div className="flex flex-wrap gap-1 mt-2">
                                      {endpoints.map(({ component: endpointComponent, health: endpointHealth }: any) => {
                                        const endpointName = endpointComponent
                                          .replace('api_endpoint_', '')
                                          .replace(/_/g, '/')
                                          .split('/')
                                          .pop() || 'unknown';
                                        
                                        return (
                                          <Badge 
                                            key={endpointComponent}
                                            variant="outline" 
                                            className={`text-xs px-1.5 py-0.5 ${
                                              endpointHealth.status === 'healthy' ? 'border-green-300 text-green-700' :
                                              endpointHealth.status === 'degraded' ? 'border-yellow-300 text-yellow-700' :
                                              'border-red-300 text-red-700'
                                            }`}
                                            title={`${endpointName}: ${endpointHealth.message} (${endpointHealth.response_time || 0}ms)`}
                                          >
                                            {endpointName}
                                          </Badge>
                                        );
                                      })}
                                    </div>
                                  )}
                                </div>
                              </div>
                              {health.action && (
                                <Button 
                                  size="sm" 
                                  variant="outline"
                                  className="ml-2 flex-shrink-0"
                                  onClick={() => window.location.href = health.action.url}
                                >
                                  {health.action.label}
                                </Button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </CardContent>
        </Card>
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
                <Badge variant="secondary" className={
                  analytics?.systemHealth && Object.values(analytics.systemHealth).every((h: any) => h.status === 'healthy')
                    ? "bg-green-100 text-green-700"
                    : analytics?.systemHealth && Object.values(analytics.systemHealth).some((h: any) => h.status === 'failed')
                    ? "bg-red-100 text-red-700"
                    : "bg-yellow-100 text-yellow-700"
                }>
                  {analytics?.systemHealth && Object.values(analytics.systemHealth).every((h: any) => h.status === 'healthy')
                    ? "Healthy"
                    : analytics?.systemHealth && Object.values(analytics.systemHealth).some((h: any) => h.status === 'failed')
                    ? "Issues Detected"
                    : "Degraded"}
                </Badge>
                <span className="text-sm text-muted-foreground">
                  {analytics?.systemHealth && Object.values(analytics.systemHealth).filter((h: any) => h.status !== 'healthy').length || 0} components need attention
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
            {/* Service Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {stats?.service_metrics && Object.entries(stats.service_metrics).map(([serviceName, metrics]: [string, any]) => (
                <Card key={serviceName}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm capitalize flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${
                        metrics.status === 'running' ? 'bg-green-500' :
                        metrics.status === 'exited' ? 'bg-red-500' :
                        'bg-yellow-500'
                      }`} />
                      {serviceName.replace('-', ' ')}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Status: {metrics.status || 'unknown'}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {/* CPU Usage */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-muted-foreground">CPU</span>
                        <span className="text-xs font-medium">{metrics.cpu_percent || 0}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1">
                        <div 
                          className="bg-blue-500 h-1 rounded-full" 
                          style={{ width: `${Math.min(metrics.cpu_percent || 0, 100)}%` }}
                        />
                      </div>
                    </div>
                    
                    {/* Memory Usage */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-muted-foreground">Memory</span>
                        <span className="text-xs font-medium">{metrics.memory_usage_mb || 0} MB</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1">
                        <div 
                          className="bg-green-500 h-1 rounded-full" 
                          style={{ width: `${Math.min(metrics.memory_percent || 0, 100)}%` }}
                        />
                      </div>
                    </div>
                    
                    {/* Network I/O */}
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <p className="text-muted-foreground">RX</p>
                        <p className="font-medium">{metrics.network_rx_mb || 0} MB</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">TX</p>
                        <p className="font-medium">{metrics.network_tx_mb || 0} MB</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            
            {/* Redis Detailed Metrics */}
            {stats?.redis_metrics && (
              <Card>
                <CardHeader>
                  <CardTitle>Redis Cache Metrics</CardTitle>
                  <CardDescription>Detailed Redis performance and usage</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-muted-foreground">Connections</p>
                      <p className="text-2xl font-bold">{stats.redis_metrics.connected_clients || 0}</p>
                      <p className="text-xs text-muted-foreground">Active clients</p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-muted-foreground">Operations/sec</p>
                      <p className="text-2xl font-bold">{stats.redis_metrics.instantaneous_ops_per_sec || 0}</p>
                      <p className="text-xs text-muted-foreground">Current rate</p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-muted-foreground">Memory Usage</p>
                      <p className="text-2xl font-bold">{stats.redis_metrics.used_memory_mb || 0}</p>
                      <p className="text-xs text-muted-foreground">MB used</p>
                    </div>
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-muted-foreground">Hit Rate</p>
                      <p className="text-2xl font-bold">
                        {stats.redis_metrics.keyspace_hits && stats.redis_metrics.keyspace_misses
                          ? Math.round((stats.redis_metrics.keyspace_hits / (stats.redis_metrics.keyspace_hits + stats.redis_metrics.keyspace_misses)) * 100)
                          : 0}%
                      </p>
                      <p className="text-xs text-muted-foreground">Cache efficiency</p>
                    </div>
                  </div>
                  
                  <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Commands Processed</p>
                      <p className="font-medium">{formatNumber(stats.redis_metrics.total_commands_processed || 0)}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Expired Keys</p>
                      <p className="font-medium">{formatNumber(stats.redis_metrics.expired_keys || 0)}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">Evicted Keys</p>
                      <p className="font-medium">{formatNumber(stats.redis_metrics.evicted_keys || 0)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* AnythingLLM Metrics */}
            {stats?.anythingllm_metrics && (
              <Card>
                <CardHeader>
                  <CardTitle>AnythingLLM Service</CardTitle>
                  <CardDescription>Vector database and LLM service status</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-sm text-muted-foreground">Status</p>
                      <Badge variant={stats.anythingllm_metrics.status === 'healthy' ? 'default' : 'destructive'}>
                        {stats.anythingllm_metrics.status || 'unknown'}
                      </Badge>
                    </div>
                    {stats.anythingllm_metrics.version && (
                      <div>
                        <p className="text-sm text-muted-foreground">Version</p>
                        <p className="font-medium">{stats.anythingllm_metrics.version}</p>
                      </div>
                    )}
                    {stats.anythingllm_metrics.vectorDB && (
                      <div>
                        <p className="text-sm text-muted-foreground">Vector DB</p>
                        <p className="font-medium">{stats.anythingllm_metrics.vectorDB}</p>
                      </div>
                    )}
                    {stats.anythingllm_metrics.LLMProvider && (
                      <div>
                        <p className="text-sm text-muted-foreground">LLM Provider</p>
                        <p className="font-medium">{stats.anythingllm_metrics.LLMProvider}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}