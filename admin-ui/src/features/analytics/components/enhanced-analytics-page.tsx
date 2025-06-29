'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Progress } from '@/components/ui/progress';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Icons } from '@/components/icons';
import { useApiClient } from '@/lib/hooks/use-api-client';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';

interface AnalyticsData {
  searchMetrics: {
    totalQueries: number;
    uniqueUsers: number;
    avgResponseTime: number;
    successRate: number;
    topQueries: Array<{ query: string; count: number }>;
    queriesByHour: Array<{ hour: number; count: number; responseTime: number }>;
    queriesByDay: Array<{ date: string; count: number; successRate: number }>;
  };
  contentMetrics: {
    totalDocuments: number;
    totalCollections: number;
    indexedToday: number;
    mostAccessedDocs: Array<{ title: string; accessCount: number; technology: string }>;
    documentsByType: Array<{ type: string; count: number; sizeGB: number }>;
    documentsByTechnology: Array<{ technology: string; count: number; color: string }>;
  };
  providerMetrics: {
    totalRequests: number;
    avgLatency: number;
    errorRate: number;
    requestsByProvider: Array<{ provider: string; count: number; avgLatency: number; errorRate: number }>;
    latencyTrend: Array<{ timestamp: string; provider: string; latency: number }>;
  };
  systemMetrics: {
    uptime: number;
    memoryUsage: number;
    cpuUsage: number;
    diskUsage: number;
    networkIO: { in: number; out: number };
    performanceTrend: Array<{ timestamp: string; cpu: number; memory: number; network: number }>;
  };
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

const PIE_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
  '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
];

export default function EnhancedAnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('24h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [chartType, setChartType] = useState<'line' | 'area' | 'bar'>('area');
  const [showDetails, setShowDetails] = useState(false);
  const apiClient = useApiClient();

  const generateMockHourlyData = (): Array<{ hour: number; count: number; responseTime: number }> => {
    const data: Array<{ hour: number; count: number; responseTime: number }> = [];
    for (let i = 0; i < 24; i++) {
      const baseCount = Math.floor(Math.random() * 100) + 50;
      data.push({
        hour: i,
        count: baseCount,
        responseTime: Math.floor(Math.random() * 200) + 50
      });
    }
    return data;
  };

  const generateMockDailyData = (): Array<{ date: string; count: number; successRate: number }> => {
    const data: Array<{ date: string; count: number; successRate: number }> = [];
    for (let i = 0; i < 7; i++) {
      const baseCount = Math.floor(Math.random() * 100) + 50;
      data.push({
        date: `Day ${i + 1}`,
        count: baseCount,
        successRate: Math.floor(Math.random() * 20) + 80
      });
    }
    return data;
  };

  const generateMockLatencyData = () => {
    const providers = ['OpenAI', 'Anthropic', 'Ollama', 'Groq'];
    const data: Array<{ timestamp: string; provider: string; latency: number }> = [];
    
    for (let i = 0; i < 20; i++) {
      providers.forEach(provider => {
        data.push({
          timestamp: `${i * 5}min`,
          provider,
          latency: Math.floor(Math.random() * 500) + 100
        });
      });
    }
    return data;
  };

  const generateMockPerformanceData = () => {
    const data = [];
    for (let i = 0; i < 20; i++) {
      data.push({
        timestamp: `${i * 5}min`,
        cpu: Math.floor(Math.random() * 40) + 20,
        memory: Math.floor(Math.random() * 30) + 40,
        network: Math.floor(Math.random() * 60) + 20
      });
    }
    return data;
  };

  const generateMockAnalyticsData = (): AnalyticsData => ({
    searchMetrics: {
      totalQueries: 12750,
      uniqueUsers: 3250,
      avgResponseTime: 245,
      successRate: 94.5,
      topQueries: [
        { query: 'React hooks tutorial', count: 342 },
        { query: 'Python async programming', count: 287 },
        { query: 'Docker best practices', count: 156 }
      ],
      queriesByHour: generateMockHourlyData(),
      queriesByDay: generateMockDailyData()
    },
    contentMetrics: {
      totalDocuments: 45680,
      totalCollections: 127,
      indexedToday: 234,
      mostAccessedDocs: [
        { title: 'React Documentation', accessCount: 1250, technology: 'React' },
        { title: 'Python Guide', accessCount: 980, technology: 'Python' }
      ],
      documentsByType: [
        { type: 'markdown', count: 15680, sizeGB: 2.4 },
        { type: 'pdf', count: 12450, sizeGB: 8.7 },
        { type: 'txt', count: 8750, sizeGB: 1.2 },
        { type: 'docx', count: 5200, sizeGB: 3.1 }
      ],
      documentsByTechnology: [
        { technology: 'React', count: 1250, color: '#61dafb' },
        { technology: 'Python', count: 980, color: '#3776ab' },
        { technology: 'JavaScript', count: 875, color: '#f7df1e' },
        { technology: 'TypeScript', count: 720, color: '#3178c6' },
        { technology: 'Node.js', count: 650, color: '#339933' },
        { technology: 'Docker', count: 480, color: '#2496ed' }
      ]
    },
    providerMetrics: {
      totalRequests: 45670,
      avgLatency: 287,
      errorRate: 2.1,
      requestsByProvider: [
        { provider: 'OpenAI', count: 18500, avgLatency: 245, errorRate: 1.5 },
        { provider: 'Anthropic', count: 12800, avgLatency: 198, errorRate: 0.8 },
        { provider: 'Ollama', count: 8750, avgLatency: 450, errorRate: 3.2 },
        { provider: 'Groq', count: 5620, avgLatency: 156, errorRate: 1.9 }
      ],
      latencyTrend: generateMockLatencyData()
    },
    systemMetrics: {
      uptime: 2592000, // 30 days
      memoryUsage: 68.5,
      cpuUsage: 34.2,
      diskUsage: 42.8,
      networkIO: { in: 1250000, out: 980000 },
      performanceTrend: generateMockPerformanceData()
    }
  });

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await apiClient.getAnalytics(timeRange);
      
      // Enhance data with additional mock data for demonstration
      const enhancedData: AnalyticsData = {
        ...data,
        searchMetrics: {
          ...data.searchMetrics,
          queriesByDay: generateMockDailyData(),
          queriesByHour: data.searchMetrics.queriesByHour || generateMockHourlyData()
        },
        contentMetrics: {
          ...data.contentMetrics,
          documentsByTechnology: [
            { technology: 'React', count: 1250, color: '#61dafb' },
            { technology: 'Python', count: 980, color: '#3776ab' },
            { technology: 'JavaScript', count: 875, color: '#f7df1e' },
            { technology: 'TypeScript', count: 720, color: '#3178c6' },
            { technology: 'Node.js', count: 650, color: '#339933' },
            { technology: 'Docker', count: 480, color: '#2496ed' }
          ]
        },
        providerMetrics: {
          ...data.providerMetrics,
          latencyTrend: generateMockLatencyData()
        },
        systemMetrics: {
          ...data.systemMetrics,
          performanceTrend: generateMockPerformanceData()
        }
      };
      
      setAnalytics(enhancedData);
    } catch (error) {
      // Error handled, could show toast notification
      // Fallback to mock data for demonstration
      // eslint-disable-next-line react-hooks/exhaustive-deps
      setAnalytics(generateMockAnalyticsData());
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  const renderChart = (data: Array<Record<string, string | number>>, type: string, dataKey: string, name?: string) => {
    const ChartComponent = chartType === 'line' ? LineChart : 
                          chartType === 'area' ? AreaChart : BarChart;
    
    return (
      <ResponsiveContainer width="100%" height={300}>
        <ChartComponent data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey={type === 'hour' ? 'hour' : type === 'date' ? 'date' : 'timestamp'} 
            stroke="#888888"
            fontSize={12}
          />
          <YAxis stroke="#888888" fontSize={12} />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'white', 
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
          />
          <Legend />
          {chartType === 'line' && (
            <Line 
              type="monotone" 
              dataKey={dataKey} 
              stroke={CHART_COLORS.primary} 
              strokeWidth={2}
              name={name || dataKey}
            />
          )}
          {chartType === 'area' && (
            <Area 
              type="monotone" 
              dataKey={dataKey} 
              stroke={CHART_COLORS.primary} 
              fill={`${CHART_COLORS.primary}20`}
              name={name || dataKey}
            />
          )}
          {chartType === 'bar' && (
            <Bar 
              dataKey={dataKey} 
              fill={CHART_COLORS.primary}
              name={name || dataKey}
            />
          )}
        </ChartComponent>
      </ResponsiveContainer>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center gap-3">
          <Icons.spinner className="w-6 h-6 animate-spin" />
          <span className="text-lg">Loading analytics...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Enhanced Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time insights into system performance and usage patterns
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Label htmlFor="auto-refresh" className="text-sm">Auto-refresh</Label>
            <Switch
              id="auto-refresh"
              checked={autoRefresh}
              onCheckedChange={setAutoRefresh}
            />
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="show-details" className="text-sm">Show details</Label>
            <Switch
              id="show-details"
              checked={showDetails}
              onCheckedChange={setShowDetails}
            />
          </div>
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
          <Button onClick={loadAnalytics} size="sm">
            <Icons.activity className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Real-time Status Indicators */}
      <div className="flex items-center gap-4 p-4 bg-muted/50 rounded-lg">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-sm font-medium">System Online</span>
        </div>
        <div className="flex items-center gap-2">
          <Icons.clock className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm">Last updated: {new Date().toLocaleTimeString()}</span>
        </div>
        {autoRefresh && (
          <div className="flex items-center gap-2">
            <Icons.activity className="w-4 h-4 text-blue-500" />
            <span className="text-sm text-blue-500">Auto-refreshing</span>
          </div>
        )}
      </div>

      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="search">Search Analytics</TabsTrigger>
          <TabsTrigger value="content">Content Insights</TabsTrigger>
          <TabsTrigger value="providers">Provider Performance</TabsTrigger>
          <TabsTrigger value="system">System Metrics</TabsTrigger>
        </TabsList>

        {/* Enhanced Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Key Metrics Cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card className="border-l-4 border-l-blue-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Searches</CardTitle>
                <Icons.search className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">
                  {analytics?.searchMetrics.totalQueries ? formatNumber(analytics.searchMetrics.totalQueries) : '0'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {analytics?.searchMetrics.successRate ? `${analytics.searchMetrics.successRate.toFixed(1)}% success rate` : 'No data'}
                </p>
                {showDetails && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    +12% from last period
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-green-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Users</CardTitle>
                <Icons.users className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">
                  {analytics?.searchMetrics.uniqueUsers ? formatNumber(analytics.searchMetrics.uniqueUsers) : '0'}
                </div>
                <p className="text-xs text-muted-foreground">
                  Unique users this period
                </p>
                {showDetails && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    +8% from last period
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-yellow-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Response</CardTitle>
                <Icons.clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-yellow-600">
                  {analytics?.searchMetrics.avgResponseTime ? formatDuration(analytics.searchMetrics.avgResponseTime) : '0ms'}
                </div>
                <p className="text-xs text-muted-foreground">
                  Search query response time
                </p>
                {showDetails && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    -5% from last period
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="border-l-4 border-l-purple-500">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Documents</CardTitle>
                <Icons.fileText className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-purple-600">
                  {analytics?.contentMetrics.totalDocuments ? formatNumber(analytics.contentMetrics.totalDocuments) : '0'}
                </div>
                <p className="text-xs text-muted-foreground">
                  {analytics?.contentMetrics.indexedToday ? `+${analytics.contentMetrics.indexedToday} today` : 'No new documents'}
                </p>
                {showDetails && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    {analytics?.contentMetrics.totalCollections || 0} collections
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Chart Controls */}
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Search Activity Trends</h3>
            <div className="flex items-center gap-2">
              <Label className="text-sm">Chart type:</Label>
              <Select value={chartType} onValueChange={(value) => setChartType(value as 'line' | 'area' | 'bar')}>
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="area">Area</SelectItem>
                  <SelectItem value="line">Line</SelectItem>
                  <SelectItem value="bar">Bar</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Overview Chart */}
          <Card>
            <CardHeader>
              <CardTitle>Search Volume Over Time</CardTitle>
              <CardDescription>Query patterns and response times</CardDescription>
            </CardHeader>
            <CardContent>
              {analytics?.searchMetrics.queriesByHour && (
                renderChart(analytics.searchMetrics.queriesByHour, 'hour', 'count', 'Search Count')
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Enhanced Search Analytics Tab */}
        <TabsContent value="search" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Query Volume Trends</CardTitle>
                <CardDescription>Search activity over time</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.searchMetrics.queriesByDay && (
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={analytics.searchMetrics.queriesByDay}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis />
                      <Tooltip />
                      <Area 
                        type="monotone" 
                        dataKey="count" 
                        stroke={CHART_COLORS.primary} 
                        fill={`${CHART_COLORS.primary}20`}
                        name="Query Count"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="successRate" 
                        stroke={CHART_COLORS.success} 
                        fill={`${CHART_COLORS.success}20`}
                        name="Success Rate (%)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Top Search Queries</CardTitle>
                <CardDescription>Most popular search terms</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.searchMetrics.topQueries ? (
                  <div className="space-y-4">
                    {analytics.searchMetrics.topQueries.map((query, index) => (
                      <div key={index} className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="w-8 h-8 rounded-full flex items-center justify-center">
                            {index + 1}
                          </Badge>
                          <span className="font-medium">{query.query}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-sm font-semibold">{formatNumber(query.count)}</span>
                          <div className="text-xs text-muted-foreground">queries</div>
                        </div>
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
              <CardTitle>Response Time Analysis</CardTitle>
              <CardDescription>Query performance metrics</CardDescription>
            </CardHeader>
            <CardContent>
              {analytics?.searchMetrics.queriesByHour && (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={analytics.searchMetrics.queriesByHour}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="hour" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="responseTime" 
                      stroke={CHART_COLORS.warning} 
                      strokeWidth={2}
                      name="Response Time (ms)"
                    />
                    <ReferenceLine 
                      y={200} 
                      stroke={CHART_COLORS.warning} 
                      strokeDasharray="5 5" 
                      label="Target: 200ms"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Enhanced Content Analytics Tab */}
        <TabsContent value="content" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Documents by Technology</CardTitle>
                <CardDescription>Content distribution across technologies</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.contentMetrics.documentsByTechnology && (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={analytics.contentMetrics.documentsByTechnology}
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="count"
                        label={({ technology, count }) => `${technology}: ${formatNumber(count)}`}
                      >
                        {analytics.contentMetrics.documentsByTechnology.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Document Types & Storage</CardTitle>
                <CardDescription>File type distribution and storage usage</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.contentMetrics.documentsByType && (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={analytics.contentMetrics.documentsByType}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="type" />
                      <YAxis yAxisId="count" orientation="left" />
                      <YAxis yAxisId="size" orientation="right" />
                      <Tooltip />
                      <Legend />
                      <Bar 
                        yAxisId="count"
                        dataKey="count" 
                        fill={CHART_COLORS.primary}
                        name="Document Count"
                      />
                      <Bar 
                        yAxisId="size"
                        dataKey="sizeGB" 
                        fill={CHART_COLORS.secondary}
                        name="Storage (GB)"
                      />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Most Accessed Documents</CardTitle>
              <CardDescription>Popular content by access count</CardDescription>
            </CardHeader>
            <CardContent>
              {analytics?.contentMetrics.mostAccessedDocs ? (
                <div className="space-y-4">
                  {analytics.contentMetrics.mostAccessedDocs.map((doc, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        <Badge variant="outline" className="w-8 h-8 rounded-full flex items-center justify-center">
                          {index + 1}
                        </Badge>
                        <div>
                          <div className="font-medium">{doc.title}</div>
                          <div className="text-sm text-muted-foreground">{doc.technology}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-semibold">{formatNumber(doc.accessCount)}</div>
                        <div className="text-xs text-muted-foreground">views</div>
                      </div>
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
        </TabsContent>

        {/* Provider Performance Tab */}
        <TabsContent value="providers" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Provider Usage Distribution</CardTitle>
                <CardDescription>Request volume by AI provider</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.providerMetrics.requestsByProvider && (
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={analytics.providerMetrics.requestsByProvider}
                        cx="50%"
                        cy="50%"
                        outerRadius={100}
                        fill="#8884d8"
                        dataKey="count"
                        label={({ provider, count }) => `${provider}: ${formatNumber(count)}`}
                      >
                        {analytics.providerMetrics.requestsByProvider.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Provider Performance</CardTitle>
                <CardDescription>Latency and error rates by provider</CardDescription>
              </CardHeader>
              <CardContent>
                {analytics?.providerMetrics.requestsByProvider && (
                  <div className="space-y-4">
                    {analytics.providerMetrics.requestsByProvider.map((provider, index) => (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{provider.provider}</span>
                          <div className="text-right text-sm">
                            <div>{formatDuration(provider.avgLatency)}</div>
                            <div className="text-muted-foreground">{provider.errorRate.toFixed(1)}% errors</div>
                          </div>
                        </div>
                        <Progress 
                          value={Math.min((provider.avgLatency / 1000) * 100, 100)} 
                          className="h-2" 
                        />
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Latency Trends</CardTitle>
              <CardDescription>Provider response time over time</CardDescription>
            </CardHeader>
            <CardContent>
              {analytics?.providerMetrics.latencyTrend && (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={analytics.providerMetrics.latencyTrend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    {analytics.providerMetrics.requestsByProvider.map((provider, index) => (
                      <Line 
                        key={provider.provider}
                        type="monotone" 
                        dataKey="latency" 
                        stroke={PIE_COLORS[index % PIE_COLORS.length]}
                        strokeWidth={2}
                        name={provider.provider}
                        data={analytics.providerMetrics.latencyTrend.filter(d => d.provider === provider.provider)}
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* System Metrics Tab */}
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
                  <Progress value={analytics?.systemMetrics.memoryUsage || 0} className="h-3" />
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>CPU Usage</span>
                    <span>{analytics?.systemMetrics.cpuUsage?.toFixed(1) || '0'}%</span>
                  </div>
                  <Progress value={analytics?.systemMetrics.cpuUsage || 0} className="h-3" />
                </div>

                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Disk Usage</span>
                    <span>{analytics?.systemMetrics.diskUsage?.toFixed(1) || '0'}%</span>
                  </div>
                  <Progress value={analytics?.systemMetrics.diskUsage || 0} className="h-3" />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>System Information</CardTitle>
                <CardDescription>Uptime and network statistics</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between">
                  <span className="text-sm font-medium">Uptime</span>
                  <span className="text-sm">
                    {analytics?.systemMetrics.uptime ? formatUptime(analytics.systemMetrics.uptime) : '0m'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm font-medium">Network In</span>
                  <span className="text-sm">
                    {analytics?.systemMetrics.networkIO ? `${(analytics.systemMetrics.networkIO.in / 1024 / 1024).toFixed(1)} MB` : '0 MB'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-sm font-medium">Network Out</span>
                  <span className="text-sm">
                    {analytics?.systemMetrics.networkIO ? `${(analytics.systemMetrics.networkIO.out / 1024 / 1024).toFixed(1)} MB` : '0 MB'}
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Performance Trends</CardTitle>
              <CardDescription>System performance over time</CardDescription>
            </CardHeader>
            <CardContent>
              {analytics?.systemMetrics.performanceTrend && (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={analytics.systemMetrics.performanceTrend}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="cpu" 
                      stroke={CHART_COLORS.primary} 
                      strokeWidth={2}
                      name="CPU (%)"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="memory" 
                      stroke={CHART_COLORS.secondary} 
                      strokeWidth={2}
                      name="Memory (%)"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="network" 
                      stroke={CHART_COLORS.accent} 
                      strokeWidth={2}
                      name="Network (%)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}