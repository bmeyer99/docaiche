'use client';

import { memo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Icons } from '@/components/icons';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

interface SystemMetrics {
  uptime: number;
  memoryUsage: number;
  cpuUsage: number;
  diskUsage: number;
  networkIO: { in: number; out: number };
  performanceTrend: Array<{ timestamp: string; cpu: number; memory: number; network: number }>;
}

interface AnalyticsSystemMetricsProps {
  systemMetrics: SystemMetrics | null;
}

const METRIC_COLORS = {
  cpu: '#3b82f6',
  memory: '#10b981',
  network: '#f59e0b',
  disk: '#ef4444'
};

export const AnalyticsSystemMetrics = memo(function AnalyticsSystemMetrics({ systemMetrics }: AnalyticsSystemMetricsProps) {
  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h ${minutes}m`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  if (!systemMetrics) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No system metrics available
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Resource Usage</CardTitle>
            <CardDescription>Current system resource utilization</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>Memory Usage</span>
                <span>{systemMetrics.memoryUsage?.toFixed(1) || '0'}%</span>
              </div>
              <Progress value={systemMetrics.memoryUsage || 0} className="h-2" />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>CPU Usage</span>
                <span>{systemMetrics.cpuUsage?.toFixed(1) || '0'}%</span>
              </div>
              <Progress value={systemMetrics.cpuUsage || 0} className="h-2" />
            </div>

            <div>
              <div className="flex justify-between text-sm mb-2">
                <span>Disk Usage</span>
                <span>{systemMetrics.diskUsage?.toFixed(1) || '0'}%</span>
              </div>
              <Progress value={systemMetrics.diskUsage || 0} className="h-2" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Information</CardTitle>
            <CardDescription>Uptime and network statistics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-2xl font-bold">{formatUptime(systemMetrics.uptime)}</div>
                <div className="text-sm text-muted-foreground">Uptime</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground mb-1">Network I/O</div>
                <div className="space-y-1">
                  <div className="flex items-center gap-1">
                    <Icons.chevronLeft className="w-3 h-3 text-blue-600 rotate-90" />
                    <span className="text-sm">{formatBytes(systemMetrics.networkIO?.in || 0)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Icons.chevronLeft className="w-3 h-3 text-green-600 -rotate-90" />
                    <span className="text-sm">{formatBytes(systemMetrics.networkIO?.out || 0)}</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Performance Trends</CardTitle>
          <CardDescription>System performance metrics over time</CardDescription>
        </CardHeader>
        <CardContent>
          {systemMetrics.performanceTrend && systemMetrics.performanceTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart
                data={systemMetrics.performanceTrend}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis 
                  dataKey="timestamp" 
                  stroke="#9ca3af"
                  style={{ fontSize: '12px' }}
                  tickFormatter={(value) => new Date(value).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                />
                <YAxis 
                  stroke="#9ca3af"
                  style={{ fontSize: '12px' }}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #e5e7eb',
                    borderRadius: '6px',
                    fontSize: '12px'
                  }}
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                  formatter={(value: number) => `${value.toFixed(1)}%`}
                />
                <Legend 
                  wrapperStyle={{ fontSize: '12px' }}
                />
                <Line
                  type="monotone"
                  dataKey="cpu"
                  stroke={METRIC_COLORS.cpu}
                  strokeWidth={2}
                  name="CPU"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="memory"
                  stroke={METRIC_COLORS.memory}
                  strokeWidth={2}
                  name="Memory"
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="network"
                  stroke={METRIC_COLORS.network}
                  strokeWidth={2}
                  name="Network"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Icons.barChart className="w-8 h-8 mx-auto mb-2" />
              <div>No performance trend data</div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
});