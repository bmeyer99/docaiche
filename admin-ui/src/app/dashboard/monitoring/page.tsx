'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { RefreshCw, Maximize2, Activity, Database, Server, Globe } from 'lucide-react';
import { MetricChart } from './components/metric-chart';
import { prometheusClient, getContainerMetrics, getRedisMetrics, getAPIMetrics } from './services/prometheus-client';
import { lokiClient } from './services/loki-client';
import { correlationEngine } from './services/correlation-engine';
import { MetricSeries } from './services/prometheus-client';
import { useToast } from '@/hooks/use-toast';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';

export default function MonitoringPage() {
  const { toast } = useToast();
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedView, setSelectedView] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<Record<string, MetricSeries[]>>({});
  const [correlatedData, setCorrelatedData] = useState<any>(null);
  const [showCorrelation, setShowCorrelation] = useState(false);

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

  // Fetch all metrics
  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const timeRange = getTimeRange();
      
      // Fetch metrics sequentially to avoid overwhelming the server
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

  // Handle data point click - show correlated data
  const handleDataPointClick = useCallback(async (params: any) => {
    try {
      const timestamp = params.value[0];
      const seriesName = params.seriesName;
      
      // Extract service/container info from series name or labels
      const context = {
        timestamp,
        service: params.data?.metadata?.service,
        container: params.data?.metadata?.container,
        labels: params.data?.metadata
      };

      const correlated = await correlationEngine.getCorrelatedData(context);
      setCorrelatedData({
        ...correlated,
        originalEvent: params
      });
      setShowCorrelation(true);
    } catch (error) {
      console.error('Failed to get correlated data:', error);
      toast({
        title: 'Correlation failed',
        description: 'Unable to fetch correlated data for this point.',
        variant: 'destructive'
      });
    }
  }, [toast]);

  // Initial load only
  useEffect(() => {
    fetchMetrics();
  }, []);

  // Update metrics when time range changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchMetrics();
    }, 500);
    return () => clearTimeout(timer);
  }, [selectedTimeRange]);

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Interactive Monitoring</h2>
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
            variant={autoRefresh ? "default" : "outline"}
            size="icon"
            onClick={() => setAutoRefresh(!autoRefresh)}
            title={autoRefresh ? "Auto-refresh enabled" : "Auto-refresh disabled"}
          >
            <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <Tabs value={selectedView} onValueChange={setSelectedView} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">System Overview</TabsTrigger>
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="infrastructure">Infrastructure</TabsTrigger>
          <TabsTrigger value="custom">Custom Dashboards</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setSelectedView('services')}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Request Rate</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-24 w-full" />
                ) : (
                  <>
                    <div className="text-2xl font-bold">
                      {metrics.request_rate?.[0]?.data.slice(-1)[0]?.value.toFixed(0) || '0'}/s
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Current request rate
                    </p>
                    <div className="mt-4 h-[80px]">
                      {metrics.request_rate && (
                        <MetricChart
                          title=""
                          series={metrics.request_rate}
                          height={80}
                          showLegend={false}
                          enableZoom={false}
                          enableBrush={false}
                        />
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setSelectedView('services')}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
                <Globe className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-24 w-full" />
                ) : (
                  <>
                    <div className="text-2xl font-bold">
                      {((metrics.error_rate?.[0]?.data.slice(-1)[0]?.value || 0) * 100).toFixed(2)}%
                    </div>
                    <p className="text-xs text-muted-foreground">
                      5xx errors
                    </p>
                    <div className="mt-4 h-[80px]">
                      {metrics.error_rate && (
                        <MetricChart
                          title=""
                          series={metrics.error_rate}
                          height={80}
                          showLegend={false}
                          enableZoom={false}
                          enableBrush={false}
                          chartType="area"
                        />
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setSelectedView('services')}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Response Time</CardTitle>
                <Server className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-24 w-full" />
                ) : (
                  <>
                    <div className="text-2xl font-bold">
                      {((metrics.latency_p95?.[0]?.data.slice(-1)[0]?.value || 0) * 1000).toFixed(0)}ms
                    </div>
                    <p className="text-xs text-muted-foreground">
                      95th percentile
                    </p>
                    <div className="mt-4 h-[80px]">
                      {metrics.latency_p95 && (
                        <MetricChart
                          title=""
                          series={metrics.latency_p95.map(s => ({
                            ...s,
                            data: s.data.map(d => ({ ...d, value: d.value * 1000 }))
                          }))}
                          height={80}
                          showLegend={false}
                          enableZoom={false}
                          enableBrush={false}
                          unit="ms"
                        />
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>

            <Card 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => setSelectedView('infrastructure')}
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Redis Cache</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-24 w-full" />
                ) : (
                  <>
                    <div className="text-2xl font-bold">
                      {(metrics.hit_rate?.[0]?.data.slice(-1)[0]?.value || 0).toFixed(1)}%
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Cache hit rate
                    </p>
                    <div className="mt-4 h-[80px]">
                      {metrics.hit_rate && (
                        <MetricChart
                          title=""
                          series={metrics.hit_rate}
                          height={80}
                          showLegend={false}
                          enableZoom={false}
                          enableBrush={false}
                          unit="%"
                        />
                      )}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Request Volume</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-[300px] w-full" />
                ) : metrics.request_rate && metrics.request_rate.length > 0 ? (
                  <MetricChart
                    title=""
                    series={metrics.request_rate}
                    height={300}
                    onDataPointClick={handleDataPointClick}
                    onRefresh={fetchMetrics}
                    loading={loading}
                    unit="/s"
                    enableZoom={true}
                    enableBrush={true}
                  />
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    No request rate data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Redis Memory Usage</CardTitle>
              </CardHeader>
              <CardContent>
                {loading ? (
                  <Skeleton className="h-[300px] w-full" />
                ) : metrics.memory_used && metrics.memory_used.length > 0 ? (
                  <MetricChart
                    title=""
                    series={metrics.memory_used.map(s => ({
                      ...s,
                      data: s.data.map(d => ({ ...d, value: d.value / 1024 / 1024 })) // Convert to MB
                    }))}
                    height={300}
                    onDataPointClick={handleDataPointClick}
                    onRefresh={fetchMetrics}
                    loading={loading}
                    unit="MB"
                    chartType="area"
                  />
                ) : (
                  <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                    No Redis memory data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Service Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <Skeleton className="h-[400px] w-full" />
              ) : (metrics.grafana_requests && metrics.grafana_requests.length > 0) || (metrics.go_memory && metrics.go_memory.length > 0) ? (
                <MetricChart
                  title=""
                  series={[
                    ...(metrics.grafana_requests || []).map(s => ({ 
                      ...s, 
                      name: 'Grafana Requests/sec',
                      data: s.data.map(d => ({ ...d, value: d.value }))
                    })),
                    ...(metrics.weaviate_requests || []).map(s => ({ 
                      ...s, 
                      name: 'Weaviate Requests/sec',
                      data: s.data.map(d => ({ ...d, value: d.value }))
                    })),
                    ...(metrics.go_memory || []).map(s => ({ 
                      ...s, 
                      name: 'Go Memory MB',
                      data: s.data.map(d => ({ ...d, value: d.value / 1024 / 1024 }))
                    }))
                  ]}
                  height={400}
                  onDataPointClick={handleDataPointClick}
                  onRefresh={fetchMetrics}
                  loading={loading}
                  chartType="line"
                  enableZoom={true}
                  enableBrush={true}
                  showLegend={true}
                />
              ) : (
                <div className="h-[400px] flex items-center justify-center text-muted-foreground">
                  No service metrics data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="services" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Service-Level Monitoring</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {metrics.latency_p50 && metrics.latency_p95 && metrics.latency_p99 && (
                  <MetricChart
                    title="API Latency Percentiles"
                    series={[
                      ...(metrics.latency_p50 || []).map(s => ({ 
                        ...s, 
                        name: 'P50',
                        data: s.data.map(d => ({ ...d, value: d.value * 1000 }))
                      })),
                      ...(metrics.latency_p95 || []).map(s => ({ 
                        ...s, 
                        name: 'P95',
                        data: s.data.map(d => ({ ...d, value: d.value * 1000 }))
                      })),
                      ...(metrics.latency_p99 || []).map(s => ({ 
                        ...s, 
                        name: 'P99',
                        data: s.data.map(d => ({ ...d, value: d.value * 1000 }))
                      }))
                    ]}
                    height={300}
                    onDataPointClick={handleDataPointClick}
                    unit="ms"
                    description="Response time percentiles"
                  />
                )}
                {metrics.error_rate && (
                  <MetricChart
                    title="Error Rate Over Time"
                    series={metrics.error_rate.map(s => ({
                      ...s,
                      data: s.data.map(d => ({ ...d, value: d.value * 100 }))
                    }))}
                    height={300}
                    onDataPointClick={handleDataPointClick}
                    unit="%"
                    description="5xx error rate"
                    chartType="area"
                  />
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="infrastructure" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Infrastructure Monitoring</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4">
                {metrics.memory_used && metrics.connected_clients && (
                  <MetricChart
                    title="Redis Metrics"
                    series={[
                      ...(metrics.memory_used || []).map(s => ({ 
                        ...s, 
                        name: 'Memory (MB)',
                        data: s.data.map(d => ({ ...d, value: d.value / 1024 / 1024 }))
                      })),
                      ...(metrics.connected_clients || []).map(s => ({ 
                        ...s, 
                        name: 'Connected Clients',
                      }))
                    ]}
                    height={300}
                    onDataPointClick={handleDataPointClick}
                    description="Redis memory and connection metrics"
                    showLegend={true}
                  />
                )}
                {metrics.commands_processed && (
                  <MetricChart
                    title="Redis Commands Rate"
                    series={metrics.commands_processed}
                    height={300}
                    onDataPointClick={handleDataPointClick}
                    unit="ops/s"
                    description="Redis operations per second"
                  />
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="custom" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Custom Dashboards</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Create and manage custom dashboard views</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Correlation Dialog */}
      <Dialog open={showCorrelation} onOpenChange={setShowCorrelation}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Correlated Data Analysis</DialogTitle>
          </DialogHeader>
          {correlatedData && (
            <div className="space-y-6">
              {/* Anomalies */}
              {correlatedData.anomalies.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Detected Anomalies</h3>
                  <div className="space-y-2">
                    {correlatedData.anomalies.map((anomaly: any, idx: number) => (
                      <div key={idx} className={`p-3 rounded border ${
                        anomaly.severity === 'critical' ? 'border-red-500 bg-red-50' :
                        anomaly.severity === 'high' ? 'border-orange-500 bg-orange-50' :
                        'border-yellow-500 bg-yellow-50'
                      }`}>
                        <p className="font-medium">{anomaly.message}</p>
                        <p className="text-sm text-muted-foreground">
                          {new Date(anomaly.timestamp).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Related Logs */}
              {correlatedData.logs.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Related Logs</h3>
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {correlatedData.logs.slice(0, 20).map((log: any, idx: number) => (
                      <div key={idx} className={`p-2 rounded text-sm font-mono ${
                        log.level === 'error' ? 'bg-red-50' :
                        log.level === 'warn' ? 'bg-yellow-50' :
                        'bg-gray-50'
                      }`}>
                        <span className="text-xs text-muted-foreground">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </span>
                        <span className="ml-2">[{log.service || 'unknown'}]</span>
                        <span className="ml-2">{log.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Related Services */}
              {correlatedData.relatedServices.length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold mb-2">Related Services</h3>
                  <div className="flex flex-wrap gap-2">
                    {correlatedData.relatedServices.map((service: string) => (
                      <span key={service} className="px-3 py-1 bg-blue-100 rounded-full text-sm">
                        {service}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}