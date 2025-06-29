'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Icons } from '@/components/icons';
import { useApiClient } from '@/lib/hooks/use-api-client';

interface AnalyticsData {
  searchMetrics: {
    totalQueries: number;
    uniqueUsers: number;
    avgResponseTime: number;
    successRate: number;
    topQueries: Array<{ query: string; count: number }>;
    queriesByHour: Array<{ hour: number; count: number }>;
  };
  contentMetrics: {
    totalDocuments: number;
    totalCollections: number;
    indexedToday: number;
    mostAccessedDocs: Array<{ title: string; accessCount: number }>;
    documentsByType: Array<{ type: string; count: number }>;
  };
  providerMetrics: {
    totalRequests: number;
    avgLatency: number;
    errorRate: number;
    requestsByProvider: Array<{ provider: string; count: number; avgLatency: number }>;
  };
  systemMetrics: {
    uptime: number;
    memoryUsage: number;
    cpuUsage: number;
    diskUsage: number;
    networkIO: { in: number; out: number };
  };
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('24h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const apiClient = useApiClient();

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await apiClient.getAnalytics(timeRange);
      setAnalytics(data);
    } catch (error) {
      // Error silently handled, could show toast notification here
    } finally {
      setLoading(false);
    }
  }, [apiClient, timeRange]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(loadAnalytics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [autoRefresh, loadAnalytics]);

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

  const formatBytes = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  if (loading) {
    return (
      <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Icons.spinner className="w-8 h-8 animate-spin mx-auto mb-4" />
            <div className="text-muted-foreground">Loading analytics...</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6 h-full overflow-y-auto">
        <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            Comprehensive analytics and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last Hour</SelectItem>
              <SelectItem value="24h">Last 24 Hours</SelectItem>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <Icons.arrowRight className={`w-4 h-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
            {autoRefresh ? 'Auto Refresh On' : 'Auto Refresh Off'}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="search">Search Analytics</TabsTrigger>
          <TabsTrigger value="content">Content Analytics</TabsTrigger>
          <TabsTrigger value="system">System Performance</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
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

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Top Search Queries</CardTitle>
                <CardDescription>Most frequently searched terms</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.searchMetrics.topQueries && analytics.searchMetrics.topQueries.length > 0 ? (
                  <div className="space-y-3">
                    {analytics.searchMetrics.topQueries.slice(0, 5).map((query, index) => (
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

            <Card>
              <CardHeader>
                <CardTitle>Provider Performance</CardTitle>
                <CardDescription>AI provider usage and latency</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.providerMetrics.requestsByProvider && analytics.providerMetrics.requestsByProvider.length > 0 ? (
                  <div className="space-y-3">
                    {analytics.providerMetrics.requestsByProvider.map((provider, index) => (
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
                          </div>
                        </div>
                        <Progress 
                          value={(provider.count / analytics.providerMetrics.totalRequests) * 100} 
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
          </div>
        </TabsContent>

        {/* Search Analytics Tab */}
        <TabsContent value="search" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Search Volume by Hour</CardTitle>
                <CardDescription>Query patterns throughout the day</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-muted-foreground">
                  <Icons.barChart className="w-8 h-8 mx-auto mb-2" />
                  <div>Chart visualization would go here</div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Search Success Rate</CardTitle>
                <CardDescription>Percentage of successful queries</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="text-center">
                  <div className="text-4xl font-bold text-green-600">
                    {analytics?.searchMetrics.successRate?.toFixed(1) || '0'}%
                  </div>
                  <div className="text-sm text-muted-foreground">Success Rate</div>
                </div>
                <Progress 
                  value={analytics?.searchMetrics.successRate || 0} 
                  className="h-3" 
                />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Content Analytics Tab */}
        <TabsContent value="content" className="space-y-6">
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                <Icons.fileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {analytics?.contentMetrics.totalDocuments ? formatNumber(analytics.contentMetrics.totalDocuments) : '0'}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Collections</CardTitle>
                <Icons.folder className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {analytics?.contentMetrics.totalCollections || '0'}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Indexed Today</CardTitle>
                <Icons.add className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {analytics?.contentMetrics.indexedToday || '0'}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Most Accessed Documents</CardTitle>
                <CardDescription>Popular content based on search results</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.contentMetrics.mostAccessedDocs && analytics.contentMetrics.mostAccessedDocs.length > 0 ? (
                  <div className="space-y-3">
                    {analytics.contentMetrics.mostAccessedDocs.slice(0, 5).map((doc, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{index + 1}</Badge>
                          <span className="font-medium truncate">{doc.title}</span>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {formatNumber(doc.accessCount)} views
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No access data available
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Documents by Type</CardTitle>
                <CardDescription>File format distribution</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.contentMetrics.documentsByType && analytics.contentMetrics.documentsByType.length > 0 ? (
                  <div className="space-y-3">
                    {analytics.contentMetrics.documentsByType.map((type, index) => (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{type.type.toUpperCase()}</span>
                          <span className="text-sm text-muted-foreground">
                            {formatNumber(type.count)} files
                          </span>
                        </div>
                        <Progress 
                          value={(type.count / analytics.contentMetrics.totalDocuments) * 100} 
                          className="h-2" 
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    No document type data available
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* System Performance Tab */}
        <TabsContent value="system" className="space-y-6">
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
                    <span>{analytics?.systemMetrics.memoryUsage?.toFixed(1) || '0'}%</span>
                  </div>
                  <Progress value={analytics?.systemMetrics.memoryUsage || 0} className="h-2" />
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>CPU Usage</span>
                    <span>{analytics?.systemMetrics.cpuUsage?.toFixed(1) || '0'}%</span>
                  </div>
                  <Progress value={analytics?.systemMetrics.cpuUsage || 0} className="h-2" />
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Disk Usage</span>
                    <span>{analytics?.systemMetrics.diskUsage?.toFixed(1) || '0'}%</span>
                  </div>
                  <Progress value={analytics?.systemMetrics.diskUsage || 0} className="h-2" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Network I/O</CardTitle>
                <CardDescription>Data transfer statistics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">
                      {analytics?.systemMetrics.networkIO ? formatBytes(analytics.systemMetrics.networkIO.in) : '0 B'}
                    </div>
                    <div className="text-sm text-muted-foreground">Incoming</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {analytics?.systemMetrics.networkIO ? formatBytes(analytics.systemMetrics.networkIO.out) : '0 B'}
                    </div>
                    <div className="text-sm text-muted-foreground">Outgoing</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}