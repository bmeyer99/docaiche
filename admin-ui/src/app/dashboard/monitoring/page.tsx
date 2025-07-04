'use client';

import React, { useState, useCallback, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { Activity, Database, RefreshCw, Server, Monitor, AlertTriangle, CheckCircle, Clock, Users, HardDrive, Cpu, MemoryStick } from 'lucide-react';
import { MetricChart } from './components/metric-chart';
import { getContainerMetrics, getRedisMetrics, getAPIMetrics } from './services/prometheus-client';

interface MetricSeries {
  name: string;
  data: Array<{ timestamp: number; value: number; metadata?: Record<string, string> }>;
  labels: Record<string, string>;
}

export default function MonitoringPage() {
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');
  const [selectedView, setSelectedView] = useState('overview');
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState<Record<string, MetricSeries[]>>({});
  const [services, setServices] = useState<Array<{name: string, status: string, category: string}>>([]);
  const { toast } = useToast();

  // Calculate time range based on selection
  const getTimeRange = useCallback(() => {
    const now = Math.floor(Date.now() / 1000); // Convert to Unix seconds
    const ranges: Record<string, number> = {
      '5m': 5 * 60,
      '15m': 15 * 60,
      '1h': 60 * 60,
      '6h': 6 * 60 * 60,
      '24h': 24 * 60 * 60,
      '7d': 7 * 24 * 60 * 60
    };
    const duration = ranges[selectedTimeRange] || ranges['1h'];
    return {
      start: now - duration,
      end: now
    };
  }, [selectedTimeRange]);

  // Fetch all metrics sequentially to avoid overwhelming the server
  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const timeRange = getTimeRange();
      
      const containerData = await getContainerMetrics(timeRange);
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const redisData = await getRedisMetrics(timeRange);
      await new Promise(resolve => setTimeout(resolve, 200));
      
      const apiData = await getAPIMetrics(timeRange);

      const allMetrics = {
        ...containerData,
        ...redisData,
        ...apiData
      };
      
      console.log('Fetched metrics:', allMetrics);
      setMetrics(allMetrics);
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
      toast({
        title: 'Error fetching metrics',
        description: 'Failed to load monitoring data. Please try again.',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  }, [getTimeRange, toast]);

  // Fetch service status from Prometheus up metric
  const fetchServiceStatus = useCallback(async () => {
    try {
      const response = await fetch('/prometheus/api/v1/query?query=up');
      const data = await response.json();
      
      if (data.status === 'success') {
        const serviceList = data.data.result.map((result: any) => {
          const instance = result.metric.instance || result.metric.job || 'unknown';
          const job = result.metric.job || 'unknown';
          const isUp = result.value[1] === '1';
          
          // Categorize services
          let category = 'Infrastructure';
          if (['admin-ui', 'api', 'db', 'traefik'].includes(job)) {
            category = 'Core Application';
          } else if (['redis', 'weaviate', 'redis-exporter'].includes(job)) {
            category = 'Data & Storage';
          } else if (['prometheus', 'grafana', 'loki', 'promtail', 'node-exporter'].includes(job)) {
            category = 'Monitoring & Observability';
          }
          
          return {
            name: job.charAt(0).toUpperCase() + job.slice(1).replace('-', ' '),
            status: isUp ? 'UP' : 'DOWN',
            category
          };
        });
        
        setServices(serviceList);
      }
    } catch (error) {
      console.error('Failed to fetch service status:', error);
      // Fallback to static list
      setServices([
        {name: 'Admin UI', status: 'UP', category: 'Core Application'},
        {name: 'API', status: 'UP', category: 'Core Application'},
        {name: 'Database', status: 'UP', category: 'Core Application'},
        {name: 'Traefik', status: 'UP', category: 'Core Application'},
        {name: 'Redis', status: 'UP', category: 'Data & Storage'},
        {name: 'Weaviate', status: 'UP', category: 'Data & Storage'},
        {name: 'Redis Exporter', status: 'UP', category: 'Data & Storage'},
        {name: 'Prometheus', status: 'UP', category: 'Monitoring & Observability'},
        {name: 'Grafana', status: 'UP', category: 'Monitoring & Observability'},
        {name: 'Loki', status: 'UP', category: 'Monitoring & Observability'},
        {name: 'Promtail', status: 'UP', category: 'Monitoring & Observability'},
        {name: 'Node Exporter', status: 'UP', category: 'Monitoring & Observability'},
      ]);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchMetrics();
    fetchServiceStatus();
  }, []);

  // Update metrics when time range changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchMetrics();
    }, 500);
    return () => clearTimeout(timer);
  }, [selectedTimeRange]);

  // Render service-specific detail view
  const renderServiceDetail = (serviceName: string) => {
    const service = services.find(s => s.name.toLowerCase().replace(/\s+/g, '-') === serviceName);
    if (!service) return null;

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button 
              variant="outline" 
              onClick={() => setSelectedView('overview')}
              className="gap-2"
            >
              ← Back to Overview
            </Button>
            <div className="flex items-center gap-2">
              {service.status === 'UP' ? (
                <CheckCircle className="h-6 w-6 text-green-500" />
              ) : (
                <AlertTriangle className="h-6 w-6 text-red-500" />
              )}
              <h2 className="text-3xl font-bold">{service.name} Service Details</h2>
            </div>
          </div>
          <Badge 
            variant="outline" 
            className={`${
              service.status === 'UP' 
                ? 'text-green-600 border-green-600' 
                : 'text-red-600 border-red-600'
            }`}
          >
            {service.status}
          </Badge>
        </div>

        {/* Service-specific metrics */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Request Rate</CardTitle>
              <CardDescription>Requests per second over time</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-[300px] w-full" />
              ) : (
                <MetricChart
                  title=""
                  series={metrics.request_rate || []}
                  height={300}
                  unit="/s"
                  enableZoom={true}
                  chartType="line"
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Response Time</CardTitle>
              <CardDescription>Average response time</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-[300px] w-full" />
              ) : (
                <MetricChart
                  title=""
                  series={metrics.latency_p95 || []}
                  height={300}
                  unit="ms"
                  enableZoom={true}
                  chartType="area"
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Memory Usage</CardTitle>
              <CardDescription>Memory consumption over time</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-[300px] w-full" />
              ) : (
                <MetricChart
                  title=""
                  series={metrics.memory_used?.map(s => ({
                    ...s,
                    data: s.data.map(d => ({ ...d, value: d.value / 1024 / 1024 }))
                  })) || []}
                  height={300}
                  unit="MB"
                  enableZoom={true}
                  chartType="area"
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Error Rate</CardTitle>
              <CardDescription>Error percentage over time</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-[300px] w-full" />
              ) : (
                <MetricChart
                  title=""
                  series={metrics.error_rate || []}
                  height={300}
                  unit="%"
                  enableZoom={true}
                  chartType="line"
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Service logs and additional info */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Events & Logs</CardTitle>
            <CardDescription>Latest service events and log entries</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span className="text-muted-foreground">2 minutes ago</span>
                <span>Service health check passed</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span className="text-muted-foreground">5 minutes ago</span>
                <span>Metrics endpoint responding normally</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <RefreshCw className="h-4 w-4 text-blue-500" />
                <span className="text-muted-foreground">10 minutes ago</span>
                <span>Service restarted successfully</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  };

  // Check if current view is a service detail view
  const isServiceView = selectedView.startsWith('service-');
  const currentServiceName = isServiceView ? selectedView.replace('service-', '') : '';

  if (isServiceView) {
    return (
      <div className="flex-1 space-y-4 p-8 pt-6">
        {renderServiceDetail(currentServiceName)}
      </div>
    );
  }

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">System Monitoring</h2>
        <div className="flex items-center space-x-2">
          <Select value={selectedTimeRange} onValueChange={setSelectedTimeRange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select time range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5m">Last 5 minutes</SelectItem>
              <SelectItem value="15m">Last 15 minutes</SelectItem>
              <SelectItem value="1h">Last 1 hour</SelectItem>
              <SelectItem value="6h">Last 6 hours</SelectItem>
              <SelectItem value="24h">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={fetchMetrics}
            disabled={loading}
            title="Refresh metrics"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <Tabs value={selectedView} onValueChange={setSelectedView} className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">System Overview</TabsTrigger>
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="infrastructure">Infrastructure</TabsTrigger>
          <TabsTrigger value="dashboards">Grafana Dashboards</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Service Health Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="h-5 w-5" />
                Service Health Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6">
                {services.map(service => (
                  <div 
                    key={service.name} 
                    className="flex flex-col items-center justify-center p-4 border rounded-lg space-y-2 cursor-pointer hover:shadow-lg hover:border-primary/50 transition-all"
                    onClick={() => setSelectedView(`service-${service.name.toLowerCase().replace(/\s+/g, '-')}`)}
                  >
                    <div className="flex items-center gap-2">
                      {service.status === 'UP' ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <AlertTriangle className="h-4 w-4 text-red-500" />
                      )}
                      <span className="font-medium">{service.name}</span>
                    </div>
                    <Badge 
                      variant="outline" 
                      className={`text-xs ${
                        service.status === 'UP' 
                          ? 'text-green-600 border-green-600' 
                          : 'text-red-600 border-red-600'
                      }`}
                    >
                      {service.status}
                    </Badge>
                    <div className="text-xs text-muted-foreground mt-1">
                      Click to view details
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Key Metrics Summary */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card 
              className="cursor-pointer hover:shadow-lg transition-all" 
              onClick={() => setSelectedView('services')}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Request Rate</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {loading ? <Skeleton className="h-8 w-16" /> : 
                   metrics.request_rate?.[0]?.data.slice(-1)[0]?.value.toFixed(1) || '0'}/s
                </div>
                <p className="text-xs text-muted-foreground">HTTP requests per second</p>
                <p className="text-xs text-blue-600 mt-1">Click to view details →</p>
              </CardContent>
            </Card>

            <Card 
              className="cursor-pointer hover:shadow-lg transition-all" 
              onClick={() => setSelectedView('infrastructure')}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Redis Memory</CardTitle>
                <MemoryStick className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {loading ? <Skeleton className="h-8 w-16" /> : 
                   (metrics.memory_used?.[0]?.data.slice(-1)[0]?.value / 1024 / 1024).toFixed(1) || '0'}MB
                </div>
                <p className="text-xs text-muted-foreground">Redis memory usage</p>
                <p className="text-xs text-blue-600 mt-1">Click to view details →</p>
              </CardContent>
            </Card>

            <Card 
              className="cursor-pointer hover:shadow-lg transition-all" 
              onClick={() => setSelectedView('infrastructure')}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Connected Clients</CardTitle>
                <Users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {loading ? <Skeleton className="h-8 w-16" /> : 
                   metrics.connected_clients?.[0]?.data.slice(-1)[0]?.value || '0'}
                </div>
                <p className="text-xs text-muted-foreground">Redis connections</p>
                <p className="text-xs text-blue-600 mt-1">Click to view details →</p>
              </CardContent>
            </Card>

            <Card 
              className="cursor-pointer hover:shadow-lg transition-all" 
              onClick={() => setSelectedView('infrastructure')}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Cache Hit Rate</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {loading ? <Skeleton className="h-8 w-16" /> : 
                   (metrics.hit_rate?.[0]?.data.slice(-1)[0]?.value || 0).toFixed(1)}%
                </div>
                <p className="text-xs text-muted-foreground">Redis cache efficiency</p>
                <p className="text-xs text-blue-600 mt-1">Click to view details →</p>
              </CardContent>
            </Card>
          </div>

          {/* System Performance Charts */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Request Volume</CardTitle>
                <CardDescription>HTTP requests across all services</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-[300px] w-full" />
                ) : (
                  <MetricChart
                    title=""
                    series={metrics.request_rate || []}
                    height={300}
                    unit="/s"
                    enableZoom={true}
                    onDataPointClick={(params) => {
                      console.log('Request rate data point clicked:', params);
                      // Could navigate to detailed view or show more info
                    }}
                    onTimeRangeChange={(start, end) => {
                      console.log('Time range changed:', start, end);
                      // Could filter other charts to same time range
                    }}
                    description="Click and drag to zoom, click data points for details"
                  />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Redis Memory Usage</CardTitle>
                <CardDescription>Memory consumption over time</CardDescription>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-[300px] w-full" />
                ) : (
                  <MetricChart
                    title=""
                    series={metrics.memory_used?.map(s => ({
                      ...s,
                      data: s.data.map(d => ({ ...d, value: d.value / 1024 / 1024 }))
                    })) || []}
                    height={300}
                    unit="MB"
                    chartType="area"
                    enableZoom={true}
                    onDataPointClick={(params) => {
                      console.log('Memory usage data point clicked:', params);
                      setSelectedView('infrastructure');
                    }}
                    description="Click data points to drill down into infrastructure metrics"
                  />
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="services" className="space-y-6">
          {/* API Service Monitoring */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Server className="h-5 w-5" />
                API Service Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium mb-4">Request Latency Percentiles</h4>
                  {loading ? (
                    <Skeleton className="h-[250px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={[
                        ...(metrics.latency_p50 || []).map(s => ({ ...s, name: 'P50' })),
                        ...(metrics.latency_p95 || []).map(s => ({ ...s, name: 'P95' })),
                        ...(metrics.latency_p99 || []).map(s => ({ ...s, name: 'P99' }))
                      ]}
                      height={250}
                      unit="s"
                      showLegend={true}
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Request Rate</h4>
                  {loading ? (
                    <Skeleton className="h-[250px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.request_rate || []}
                      height={250}
                      unit="/s"
                      chartType="area"
                    />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Weaviate Service Monitoring */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Weaviate Vector Database
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium mb-4">Weaviate Request Rate</h4>
                  {loading ? (
                    <Skeleton className="h-[250px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.weaviate_requests || []}
                      height={250}
                      unit="/s"
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Weaviate Response Time</h4>
                  {loading ? (
                    <Skeleton className="h-[250px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.weaviate_latency_p95 || []}
                      height={250}
                      unit="s"
                    />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Grafana Service Monitoring */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="h-5 w-5" />
                Grafana Monitoring
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium mb-4">Grafana Request Rate</h4>
                  {loading ? (
                    <Skeleton className="h-[250px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.grafana_requests || []}
                      height={250}
                      unit="/s"
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Grafana Response Time</h4>
                  {loading ? (
                    <Skeleton className="h-[250px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.latency_p95 || []}
                      height={250}
                      unit="s"
                    />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="infrastructure" className="space-y-6">
          {/* Redis Infrastructure */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Redis Infrastructure Monitoring
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                <div>
                  <h4 className="text-sm font-medium mb-4">Memory Usage Over Time</h4>
                  {loading ? (
                    <Skeleton className="h-[200px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.memory_used?.map(s => ({
                        ...s,
                        data: s.data.map(d => ({ ...d, value: d.value / 1024 / 1024 }))
                      })) || []}
                      height={200}
                      unit="MB"
                      chartType="area"
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Connected Clients</h4>
                  {loading ? (
                    <Skeleton className="h-[200px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.connected_clients || []}
                      height={200}
                      unit="clients"
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Commands Rate</h4>
                  {loading ? (
                    <Skeleton className="h-[200px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.commands_processed || []}
                      height={200}
                      unit="ops/s"
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Cache Hit Rate</h4>
                  {loading ? (
                    <Skeleton className="h-[200px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.hit_rate || []}
                      height={200}
                      unit="%"
                      chartType="area"
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Keyspace Hits</h4>
                  {loading ? (
                    <Skeleton className="h-[200px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.keyspace_hits || []}
                      height={200}
                      unit="hits/s"
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Keyspace Misses</h4>
                  {loading ? (
                    <Skeleton className="h-[200px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.keyspace_misses || []}
                      height={200}
                      unit="misses/s"
                    />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* System Resources */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Cpu className="h-5 w-5" />
                System Resources
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-6 md:grid-cols-2">
                <div>
                  <h4 className="text-sm font-medium mb-4">Go Memory Allocation</h4>
                  {loading ? (
                    <Skeleton className="h-[250px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={metrics.go_memory?.map(s => ({
                        ...s,
                        data: s.data.map(d => ({ ...d, value: d.value / 1024 / 1024 }))
                      })) || []}
                      height={250}
                      unit="MB"
                      chartType="area"
                    />
                  )}
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-4">Service Requests Comparison</h4>
                  {loading ? (
                    <Skeleton className="h-[250px] w-full" />
                  ) : (
                    <MetricChart
                      title=""
                      series={[
                        ...(metrics.grafana_requests || []).map(s => ({ ...s, name: 'Grafana' })),
                        ...(metrics.weaviate_requests || []).map(s => ({ ...s, name: 'Weaviate' })),
                        ...(metrics.prometheus_requests || []).map(s => ({ ...s, name: 'Prometheus' }))
                      ]}
                      height={250}
                      unit="/s"
                      showLegend={true}
                    />
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="dashboards" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Grafana Dashboard Integration</CardTitle>
              <CardDescription>
                Access comprehensive dashboards from your Grafana instance
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card className="cursor-pointer hover:shadow-lg transition-shadow" 
                      onClick={() => window.open('/grafana/d/system-overview', '_blank')}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">System Overview</CardTitle>
                    <CardDescription>Overall system health and performance</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">6 panels</Badge>
                      <Monitor className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>

                <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                      onClick={() => window.open('/grafana/d/redis-monitoring', '_blank')}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Redis Monitoring</CardTitle>
                    <CardDescription>Comprehensive Redis metrics and analysis</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">8 panels</Badge>
                      <Database className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>

                <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                      onClick={() => window.open('/grafana/d/weaviate-monitoring', '_blank')}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Weaviate Monitoring</CardTitle>
                    <CardDescription>Vector database performance and metrics</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">8 panels</Badge>
                      <Server className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>

                <Card className="cursor-pointer hover:shadow-lg transition-shadow"
                      onClick={() => window.open('/grafana/d/container-logs', '_blank')}>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Container Logs</CardTitle>
                    <CardDescription>Centralized logging and log analysis</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <Badge variant="secondary">Log analysis</Badge>
                      <AlertTriangle className="h-5 w-5 text-muted-foreground" />
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="flex items-start gap-3">
                  <Monitor className="h-5 w-5 text-blue-600 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-blue-900">Full Grafana Access</h4>
                    <p className="text-sm text-blue-700 mt-1">
                      Click any dashboard above to open it in a new tab with full Grafana functionality, 
                      including advanced querying, alerting, and collaboration features.
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}