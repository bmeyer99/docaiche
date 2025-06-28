'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Icons } from '@/components/icons';
import { DocaicheApiClient } from '@/lib/utils/api-client';
import { useToast } from '@/hooks/use-toast';

interface ServiceHealth {
  name: string;
  status: 'healthy' | 'unhealthy' | 'warning' | 'unknown';
  lastCheck: string;
  responseTime?: number;
  details?: Record<string, any>;
  url?: string;
}

interface SystemMetrics {
  uptime: number;
  memory: {
    used: number;
    total: number;
    percentage: number;
  };
  cpu: {
    usage: number;
  };
  storage: {
    used: number;
    total: number;
    percentage: number;
  };
  activeConnections: number;
  requestsPerMinute: number;
}

export default function SystemHealthPage() {
  const [services, setServices] = useState<ServiceHealth[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const { toast } = useToast();

  const checkHealthStatus = useCallback(async () => {
    const apiClient = new DocaicheApiClient();
    try {
      const [healthData, metricsData] = await Promise.allSettled([
        apiClient.getSystemHealth(),
        apiClient.getSystemMetrics()
      ]);

      if (healthData.status === 'fulfilled') {
        setServices(healthData.value.services || []);
      }

      if (metricsData.status === 'fulfilled') {
        setMetrics(metricsData.value);
      }

      setLastUpdate(new Date());
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to fetch system health data",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    checkHealthStatus();
  }, [checkHealthStatus]);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(checkHealthStatus, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [autoRefresh, checkHealthStatus]);

  const getStatusBadge = (status: ServiceHealth['status']) => {
    switch (status) {
      case 'healthy': return <Badge className="bg-green-100 text-green-800">Healthy</Badge>;
      case 'warning': return <Badge className="bg-yellow-100 text-yellow-800">Warning</Badge>;
      case 'unhealthy': return <Badge className="bg-red-100 text-red-800">Unhealthy</Badge>;
      default: return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  const getOverallStatus = () => {
    if (!services.length) return 'unknown';
    if (services.some(s => s.status === 'unhealthy')) return 'unhealthy';
    if (services.some(s => s.status === 'warning')) return 'warning';
    return 'healthy';
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">System Health</h1>
          <p className="text-muted-foreground">
            Real-time monitoring of system components and services
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Icons.arrowRight className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
            {autoRefresh ? 'Auto Refresh On' : 'Auto Refresh Off'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={checkHealthStatus}
            disabled={loading}
          >
            <Icons.arrowRight className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall Status */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Icons.activity className="w-5 h-5" />
                Overall System Status
              </CardTitle>
              <CardDescription>
                Last updated: {lastUpdate.toLocaleTimeString()}
              </CardDescription>
            </div>
            {getStatusBadge(getOverallStatus())}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {services.filter(s => s.status === 'healthy').length}
              </div>
              <div className="text-sm text-muted-foreground">Healthy Services</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-600">
                {services.filter(s => s.status === 'warning').length}
              </div>
              <div className="text-sm text-muted-foreground">Warning Services</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {services.filter(s => s.status === 'unhealthy').length}
              </div>
              <div className="text-sm text-muted-foreground">Unhealthy Services</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {services.length}
              </div>
              <div className="text-sm text-muted-foreground">Total Services</div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Services Status */}
        <Card>
          <CardHeader>
            <CardTitle>Service Status</CardTitle>
            <CardDescription>Individual service health checks</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Icons.spinner className="w-6 h-6 animate-spin" />
              </div>
            ) : services.length > 0 ? (
              services.map((service) => (
                <div key={service.name} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${
                      service.status === 'healthy' ? 'bg-green-500' : 
                      service.status === 'warning' ? 'bg-yellow-500' : 
                      service.status === 'unhealthy' ? 'bg-red-500' : 'bg-gray-500'
                    }`} />
                    <div>
                      <div className="font-medium">{service.name}</div>
                      <div className="text-sm text-muted-foreground">
                        Last check: {new Date(service.lastCheck).toLocaleTimeString()}
                        {service.responseTime && ` • ${service.responseTime}ms`}
                      </div>
                    </div>
                  </div>
                  {getStatusBadge(service.status)}
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No services to monitor
              </div>
            )}
          </CardContent>
        </Card>

        {/* System Metrics */}
        <Card>
          <CardHeader>
            <CardTitle>System Metrics</CardTitle>
            <CardDescription>Resource utilization and performance</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {metrics ? (
              <>
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Memory Usage</span>
                    <span>{metrics.memory.percentage.toFixed(1)}%</span>
                  </div>
                  <Progress value={metrics.memory.percentage} className="h-2" />
                  <div className="text-xs text-muted-foreground mt-1">
                    {formatBytes(metrics.memory.used)} / {formatBytes(metrics.memory.total)}
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>CPU Usage</span>
                    <span>{metrics.cpu.usage.toFixed(1)}%</span>
                  </div>
                  <Progress value={metrics.cpu.usage} className="h-2" />
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Storage Usage</span>
                    <span>{metrics.storage.percentage.toFixed(1)}%</span>
                  </div>
                  <Progress value={metrics.storage.percentage} className="h-2" />
                  <div className="text-xs text-muted-foreground mt-1">
                    {formatBytes(metrics.storage.used)} / {formatBytes(metrics.storage.total)}
                  </div>
                </div>

                <Separator />

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-2xl font-bold">{formatUptime(metrics.uptime)}</div>
                    <div className="text-sm text-muted-foreground">Uptime</div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold">{metrics.activeConnections}</div>
                    <div className="text-sm text-muted-foreground">Active Connections</div>
                  </div>
                </div>

                <div>
                  <div className="text-2xl font-bold">{metrics.requestsPerMinute}</div>
                  <div className="text-sm text-muted-foreground">Requests/min</div>
                </div>
              </>
            ) : (
              <div className="flex items-center justify-center py-8">
                <div className="text-center text-muted-foreground">
                  <Icons.barChart className="w-8 h-8 mx-auto mb-2" />
                  <div>No metrics available</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}