'use client';

import { memo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
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

interface ProviderMetrics {
  totalRequests: number;
  avgLatency: number;
  errorRate: number;
  requestsByProvider: Array<{ provider: string; count: number; avgLatency: number; errorRate: number }>;
  latencyTrend: Array<{ timestamp: string; provider: string; latency: number }>;
}

interface AnalyticsProviderMetricsProps {
  providerMetrics: ProviderMetrics | null;
}

const PROVIDER_COLORS: Record<string, string> = {
  openai: '#10a37f',
  anthropic: '#d97706',
  ollama: '#3b82f6',
  mistral: '#ef4444',
  default: '#6b7280'
};

export const AnalyticsProviderMetrics = memo(function AnalyticsProviderMetrics({ providerMetrics }: AnalyticsProviderMetricsProps) {
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDuration = (ms: number) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms.toFixed(0)}ms`;
  };

  if (!providerMetrics) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No provider metrics available
      </div>
    );
  }

  // Group latency data by provider for multi-line chart
  const providerLines = providerMetrics.latencyTrend
    ? Array.from(new Set(providerMetrics.latencyTrend.map(d => d.provider)))
    : [];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total API Requests</CardTitle>
            <Icons.activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatNumber(providerMetrics.totalRequests)}
            </div>
            <p className="text-xs text-muted-foreground">
              Across all providers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Latency</CardTitle>
            <Icons.clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatDuration(providerMetrics.avgLatency)}
            </div>
            <p className="text-xs text-muted-foreground">
              Response time
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
            <Icons.alertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {providerMetrics.errorRate.toFixed(2)}%
            </div>
            <p className="text-xs text-muted-foreground">
              Failed requests
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Provider Performance</CardTitle>
            <CardDescription>Request distribution and latency by provider</CardDescription>
          </CardHeader>
          <CardContent>
            {providerMetrics.requestsByProvider && providerMetrics.requestsByProvider.length > 0 ? (
              <div className="space-y-3">
                {providerMetrics.requestsByProvider.map((provider, index) => (
                  <div key={index} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">{provider.provider}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground">
                          {formatNumber(provider.count)} requests
                        </span>
                        <Badge variant="outline">
                          {formatDuration(provider.avgLatency)}
                        </Badge>
                        {provider.errorRate > 0 && (
                          <Badge variant="destructive">
                            {provider.errorRate.toFixed(1)}% errors
                          </Badge>
                        )}
                      </div>
                    </div>
                    <Progress 
                      value={(provider.count / providerMetrics.totalRequests) * 100} 
                      className="h-2" 
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No provider data available
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Latency Trends</CardTitle>
            <CardDescription>Provider response times over time</CardDescription>
          </CardHeader>
          <CardContent>
            {providerMetrics.latencyTrend && providerMetrics.latencyTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={providerMetrics.latencyTrend}
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
                    tickFormatter={(value) => `${value}ms`}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: 'rgba(255, 255, 255, 0.95)',
                      border: '1px solid #e5e7eb',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}
                    labelFormatter={(value) => new Date(value).toLocaleString()}
                    formatter={(value: number) => [`${value.toFixed(0)}ms`, 'Latency']}
                  />
                  <Legend 
                    wrapperStyle={{ fontSize: '12px' }}
                  />
                  {providerLines.map((provider) => (
                    <Line
                      key={provider}
                      type="monotone"
                      dataKey="latency"
                      data={providerMetrics.latencyTrend.filter(d => d.provider === provider)}
                      stroke={PROVIDER_COLORS[provider] || PROVIDER_COLORS.default}
                      strokeWidth={2}
                      name={provider}
                      connectNulls
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Icons.barChart className="w-8 h-8 mx-auto mb-2" />
                <div>No latency trend data</div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
});