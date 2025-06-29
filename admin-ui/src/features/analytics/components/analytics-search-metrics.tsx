'use client';

import { memo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Icons } from '@/components/icons';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

interface SearchMetrics {
  totalQueries: number;
  uniqueUsers: number;
  avgResponseTime: number;
  successRate: number;
  topQueries: Array<{ query: string; count: number }>;
  queriesByHour: Array<{ hour: number; count: number; responseTime: number }>;
  queriesByDay: Array<{ date: string; count: number; successRate: number }>;
}

interface AnalyticsSearchMetricsProps {
  searchMetrics: SearchMetrics | null;
  chartType: 'line' | 'area' | 'bar';
}

const CHART_COLORS = {
  primary: '#3b82f6',
  secondary: '#10b981',
  accent: '#f59e0b',
  warning: '#ef4444',
  muted: '#6b7280',
  success: '#22c55e',
  info: '#06b6d4'
};

export const AnalyticsSearchMetrics = memo(function AnalyticsSearchMetrics({ searchMetrics, chartType }: AnalyticsSearchMetricsProps) {
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const renderChart = (data: Array<Record<string, string | number>>, type: string, dataKey: string, name?: string) => {
    const commonProps = {
      data,
      margin: { top: 5, right: 30, left: 20, bottom: 5 }
    };

    const ChartComponent = type === 'line' ? LineChart : type === 'bar' ? BarChart : AreaChart;
    const DataComponent = type === 'line' ? Line : type === 'bar' ? Bar : Area;

    return (
      <ResponsiveContainer width="100%" height={300}>
        <ChartComponent {...commonProps}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis 
            dataKey="hour" 
            stroke="#9ca3af"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="#9ca3af"
            style={{ fontSize: '12px' }}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'rgba(255, 255, 255, 0.95)',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              fontSize: '12px'
            }}
          />
          <Legend 
            wrapperStyle={{ fontSize: '12px' }}
          />
          <DataComponent
            type="monotone"
            dataKey={dataKey}
            stroke={CHART_COLORS.primary}
            fill={CHART_COLORS.primary}
            strokeWidth={2}
            name={name || dataKey}
            {...(type === 'area' ? { fillOpacity: 0.3 } : {})}
          />
          {dataKey === 'count' && (
            <ReferenceLine 
              y={data.reduce((sum, item) => sum + (item[dataKey] as number), 0) / data.length} 
              stroke={CHART_COLORS.warning} 
              strokeDasharray="3 3"
              label={{ value: "Average", position: "insideTopRight", style: { fontSize: '11px' } }}
            />
          )}
        </ChartComponent>
      </ResponsiveContainer>
    );
  };

  if (!searchMetrics) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No search metrics available
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Search Volume by Hour</CardTitle>
            <CardDescription>Query patterns throughout the day</CardDescription>
          </CardHeader>
          <CardContent>
            {searchMetrics.queriesByHour && searchMetrics.queriesByHour.length > 0 ? (
              renderChart(searchMetrics.queriesByHour, chartType, 'count', 'Searches')
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Icons.barChart className="w-8 h-8 mx-auto mb-2" />
                <div>No hourly data available</div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Search Queries</CardTitle>
            <CardDescription>Most frequently searched terms</CardDescription>
          </CardHeader>
          <CardContent>
            {searchMetrics.topQueries && searchMetrics.topQueries.length > 0 ? (
              <div className="space-y-3">
                {searchMetrics.topQueries.slice(0, 5).map((query, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{index + 1}</Badge>
                      <span className="font-medium">{query.query}</span>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {formatNumber(query.count)} searches
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No search data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Search Success Rate</CardTitle>
          <CardDescription>Percentage of successful queries</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="text-center">
            <div className="text-4xl font-bold text-green-600">
              {searchMetrics.successRate?.toFixed(1) || '0'}%
            </div>
            <div className="text-sm text-muted-foreground">Success Rate</div>
          </div>
          <Progress 
            value={searchMetrics.successRate || 0} 
            className="h-3" 
          />
        </CardContent>
      </Card>
    </div>
  );
});