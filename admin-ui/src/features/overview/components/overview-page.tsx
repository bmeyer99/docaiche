'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Icons } from '@/components/icons';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { AI_PROVIDERS } from '@/lib/config/providers';
import { OverviewLoading } from './overview-loading';
import { GradientHeader } from '@/components/ui/gradient-header';

interface DashboardStats {
  search_stats: {
    searches_today?: number;
    total_searches?: number;
  };
  content_stats: {
    total_documents?: number;
    collections?: number;
    last_update?: string;
  };
  system_stats: {
    uptime_seconds?: number;
  };
  cache_stats?: any;
}

interface RecentActivity {
  id: string;
  type: 'search' | 'index' | 'config' | 'error';
  message: string;
  timestamp: string;
  details?: string;
}

export default function OverviewPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const apiClient = useApiClient();

  const loadDashboardData = useCallback(async () => {
    try {
      const [statsData, activityData] = await Promise.all([
        apiClient.getDashboardStats(),
        apiClient.getRecentActivity()
      ]);

      setStats(statsData);
      setRecentActivity(activityData || []);
    } catch (error) {
      // Leave stats and activity as null/empty on error
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'search': return <Icons.search className="w-4 h-4" />;
      case 'index': return <Icons.database className="w-4 h-4" />;
      case 'config': return <Icons.settings className="w-4 h-4" />;
      case 'error': return <Icons.alertCircle className="w-4 h-4" />;
      default: return <Icons.activity className="w-4 h-4" />;
    }
  };

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'search': return 'text-blue-600';
      case 'index': return 'text-green-600';
      case 'config': return 'text-purple-600';
      case 'error': return 'text-red-600';
      default: return 'text-gray-600';
    }
  };

  if (loading) {
    return <OverviewLoading />;
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <GradientHeader 
        title="Dashboard Overview"
        subtitle="Welcome to the Docaiche administration interface"
        gradient="accent"
        className="fade-in-sequence"
      />

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 fade-in-sequence">
        <Card className="hover-lift transition-smooth">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <Icons.fileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : stats ? stats.content_stats?.total_documents?.toLocaleString() || 'No data' : 'API Error'}
            </div>
            <p className="text-xs text-muted-foreground">
              Indexed and searchable
            </p>
          </CardContent>
        </Card>

        <Card className="hover-lift transition-smooth">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collections</CardTitle>
            <Icons.folder className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : stats ? stats.content_stats?.collections || 'No data' : 'API Error'}
            </div>
            <p className="text-xs text-muted-foreground">
              Document collections
            </p>
          </CardContent>
        </Card>

        <Card className="hover-lift transition-smooth">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Providers</CardTitle>
            <Icons.bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : stats ? 'No data' : 'API Error'}
            </div>
            <p className="text-xs text-muted-foreground">
              AI providers configured
            </p>
          </CardContent>
        </Card>

        <Card className="hover-lift transition-smooth">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Searches (24h)</CardTitle>
            <Icons.trendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? '...' : stats ? stats.search_stats?.searches_today?.toLocaleString() || 'No data' : 'API Error'}
            </div>
            <p className="text-xs text-muted-foreground">
              Queries processed
            </p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* System Status */}
        <Card className="hover-lift transition-smooth">
          <CardHeader>
            <CardTitle>System Status</CardTitle>
            <CardDescription>Current system health and uptime</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {loading ? (
              <div>Loading system status...</div>
            ) : stats ? (
              <>
                <div className="flex items-center justify-between">
                  <span>System Status</span>
                  <span className="text-sm text-muted-foreground">API Connected</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Uptime</span>
                  <span className="font-mono">
                    {stats.system_stats?.uptime_seconds ? formatUptime(stats.system_stats.uptime_seconds) : 'No data'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Last Indexed</span>
                  <span className="text-sm text-muted-foreground">
                    {stats.content_stats?.last_update || 'No data'}
                  </span>
                </div>
              </>
            ) : (
              <div className="text-center py-4 text-red-600">
                <div>API Connection Failed</div>
                <div className="text-sm text-muted-foreground">Cannot retrieve system status</div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* AI Providers Quick Status */}
        <Card className="hover-lift transition-smooth">
          <CardHeader>
            <CardTitle>AI Providers</CardTitle>
            <CardDescription>Quick overview of configured providers</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(AI_PROVIDERS).slice(0, 4).map(([id, provider]) => (
              <div key={id} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded" 
                    style={{ backgroundColor: provider.color || '#6b7280' }}
                  />
                  <span>{provider.displayName}</span>
                </div>
                <Badge variant="outline">
                  {provider.category}
                </Badge>
              </div>
            ))}
            <div className="pt-2 border-t">
              <div className="text-sm text-muted-foreground text-center">
                {Object.keys(AI_PROVIDERS).length} providers available
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card className="hover-lift transition-smooth">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
          <CardDescription>Latest system events and operations</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Icons.spinner className="w-6 h-6 animate-spin" />
            </div>
          ) : recentActivity.length > 0 ? (
            <div className="space-y-4">
              {recentActivity.slice(0, 8).map((activity) => (
                <div key={activity.id} className="flex items-start gap-3 pb-3 border-b last:border-b-0 hover:bg-accent/50 p-2 rounded-lg transition-smooth">
                  <div className={`mt-1 ${getActivityColor(activity.type)}`}>
                    {getActivityIcon(activity.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium">{activity.message}</div>
                    {activity.details && (
                      <div className="text-sm text-muted-foreground">{activity.details}</div>
                    )}
                    <div className="text-xs text-muted-foreground mt-1">
                      {new Date(activity.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Icons.activity className="w-8 h-8 mx-auto mb-2" />
              <div>No recent activity</div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}