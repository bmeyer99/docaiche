'use client';

import { memo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Icons } from '@/components/icons';

interface AnalyticsData {
  searchMetrics: {
    totalQueries: number;
    uniqueUsers: number;
    avgResponseTime: number;
    successRate: number;
  };
  contentMetrics: {
    totalDocuments: number;
    totalCollections: number;
    indexedToday: number;
  };
  providerMetrics: {
    totalRequests: number;
    avgLatency: number;
  };
  systemMetrics: {
    uptime: number;
  };
}

interface AnalyticsOverviewCardsProps {
  analytics: AnalyticsData | null;
}

export const AnalyticsOverviewCards = memo(function AnalyticsOverviewCards({ analytics }: AnalyticsOverviewCardsProps) {
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDuration = (ms: number) => {
    if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
    return `${ms.toFixed(0)}ms`;
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Searches</CardTitle>
          <Icons.search className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {analytics?.searchMetrics.totalQueries ? formatNumber(analytics.searchMetrics.totalQueries) : '0'}
          </div>
          <p className="text-xs text-muted-foreground">
            {analytics?.searchMetrics.successRate ? `${analytics.searchMetrics.successRate.toFixed(1)}% success rate` : 'No data'}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Active Users</CardTitle>
          <Icons.users className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {analytics?.searchMetrics.uniqueUsers ? formatNumber(analytics.searchMetrics.uniqueUsers) : '0'}
          </div>
          <p className="text-xs text-muted-foreground">
            Unique users this period
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
          <Icons.clock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {analytics?.searchMetrics.avgResponseTime ? formatDuration(analytics.searchMetrics.avgResponseTime) : '0ms'}
          </div>
          <p className="text-xs text-muted-foreground">
            Search query response time
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">System Uptime</CardTitle>
          <Icons.activity className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {analytics?.systemMetrics.uptime ? formatUptime(analytics.systemMetrics.uptime) : '0m'}
          </div>
          <p className="text-xs text-muted-foreground">
            System availability
          </p>
        </CardContent>
      </Card>
    </div>
  );
});