'use client';

import { useState, useEffect, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Icons } from '@/components/icons';
// import { useApiClient } from '@/lib/hooks/use-api-client';
import { AnalyticsOverviewCards } from './analytics-overview-cards';
import { AnalyticsSearchMetrics } from './analytics-search-metrics';
import { AnalyticsContentMetrics } from './analytics-content-metrics';
import { AnalyticsProviderMetrics } from './analytics-provider-metrics';
import { AnalyticsSystemMetrics } from './analytics-system-metrics';

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

export default function EnhancedAnalyticsPageRefactored() {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('24h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [chartType, setChartType] = useState<'line' | 'area' | 'bar'>('area');
  const [showDetails, setShowDetails] = useState(false);

  const generateMockData = (): AnalyticsData => {
    // Generate mock hourly data
    const hourlyData = Array.from({ length: 24 }, (_, i) => ({
      hour: i,
      count: Math.floor(Math.random() * 100) + 50,
      responseTime: Math.floor(Math.random() * 200) + 50
    }));

    // Generate mock daily data
    const dailyData = Array.from({ length: 7 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (6 - i));
      return {
        date: date.toISOString().split('T')[0],
        count: Math.floor(Math.random() * 1000) + 500,
        successRate: 85 + Math.random() * 15
      };
    });

    // Generate mock provider data
    const providers = ['openai', 'anthropic', 'ollama', 'mistral'];
    const providerData = providers.map(provider => ({
      provider,
      count: Math.floor(Math.random() * 5000) + 1000,
      avgLatency: Math.floor(Math.random() * 500) + 100,
      errorRate: Math.random() * 5
    }));

    // Generate latency trend
    const latencyTrend = providers.flatMap(provider => 
      Array.from({ length: 12 }, (_, i) => {
        const date = new Date();
        date.setHours(date.getHours() - (11 - i));
        return {
          timestamp: date.toISOString(),
          provider,
          latency: Math.floor(Math.random() * 300) + 50
        };
      })
    );

    // Generate performance trend
    const performanceTrend = Array.from({ length: 24 }, (_, i) => {
      const date = new Date();
      date.setHours(date.getHours() - (23 - i));
      return {
        timestamp: date.toISOString(),
        cpu: Math.random() * 100,
        memory: Math.random() * 100,
        network: Math.random() * 50
      };
    });

    return {
      searchMetrics: {
        totalQueries: Math.floor(Math.random() * 50000) + 10000,
        uniqueUsers: Math.floor(Math.random() * 1000) + 200,
        avgResponseTime: Math.floor(Math.random() * 300) + 100,
        successRate: 85 + Math.random() * 15,
        topQueries: [
          { query: 'React hooks best practices', count: 523 },
          { query: 'TypeScript generics', count: 412 },
          { query: 'Next.js 14 features', count: 389 },
          { query: 'Tailwind CSS utilities', count: 356 },
          { query: 'Node.js performance', count: 298 }
        ],
        queriesByHour: hourlyData,
        queriesByDay: dailyData
      },
      contentMetrics: {
        totalDocuments: Math.floor(Math.random() * 10000) + 5000,
        totalCollections: Math.floor(Math.random() * 50) + 20,
        indexedToday: Math.floor(Math.random() * 100) + 50,
        mostAccessedDocs: [
          { title: 'React 18 Migration Guide', accessCount: 1523, technology: 'React' },
          { title: 'TypeScript 5.0 Features', accessCount: 1245, technology: 'TypeScript' },
          { title: 'Next.js App Router Tutorial', accessCount: 987, technology: 'Next.js' },
          { title: 'Tailwind CSS Components', accessCount: 876, technology: 'CSS' },
          { title: 'Node.js Best Practices', accessCount: 765, technology: 'Node.js' }
        ],
        documentsByType: [
          { type: 'pdf', count: 2456, sizeGB: 12.3 },
          { type: 'html', count: 3789, sizeGB: 8.7 },
          { type: 'md', count: 1234, sizeGB: 2.1 },
          { type: 'docx', count: 567, sizeGB: 4.5 }
        ],
        documentsByTechnology: [
          { technology: 'React', count: 2345, color: '#61dafb' },
          { technology: 'TypeScript', count: 1987, color: '#3178c6' },
          { technology: 'Node.js', count: 1654, color: '#339933' },
          { technology: 'Python', count: 1432, color: '#3776ab' },
          { technology: 'Docker', count: 987, color: '#2496ed' }
        ]
      },
      providerMetrics: {
        totalRequests: providerData.reduce((sum, p) => sum + p.count, 0),
        avgLatency: providerData.reduce((sum, p) => sum + p.avgLatency, 0) / providerData.length,
        errorRate: providerData.reduce((sum, p) => sum + p.errorRate, 0) / providerData.length,
        requestsByProvider: providerData,
        latencyTrend
      },
      systemMetrics: {
        uptime: Math.floor(Math.random() * 2592000) + 86400, // 1-30 days in seconds
        memoryUsage: Math.random() * 100,
        cpuUsage: Math.random() * 100,
        diskUsage: Math.random() * 100,
        networkIO: {
          in: Math.floor(Math.random() * 1073741824), // Up to 1GB
          out: Math.floor(Math.random() * 1073741824)
        },
        performanceTrend
      }
    };
  };

  const loadAnalytics = useCallback(async () => {
    try {
      // In a real app, this would fetch from the API
      // const data = await apiClient.getAnalytics(timeRange);
      
      // For now, use mock data
      const mockData = generateMockData();
      setAnalytics(mockData);
    } catch (error) {
      // Handle error silently
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(loadAnalytics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [autoRefresh, loadAnalytics]);

  if (loading) {
    return (
      <div className="flex flex-col gap-6 p-6">
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
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            Analytics Dashboard
          </h1>
          <p className="text-muted-foreground">
            Comprehensive analytics and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Label htmlFor="details-toggle" className="text-sm">
              Detailed View
            </Label>
            <Switch
              id="details-toggle"
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
          <Select value={chartType} onValueChange={(value) => setChartType(value as 'line' | 'area' | 'bar')}>
            <SelectTrigger className="w-28">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="line">Line</SelectItem>
              <SelectItem value="area">Area</SelectItem>
              <SelectItem value="bar">Bar</SelectItem>
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

      {/* Overview Cards */}
      <AnalyticsOverviewCards analytics={analytics} />

      {/* Tabbed Content */}
      <Tabs defaultValue="search" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="search">Search Analytics</TabsTrigger>
          <TabsTrigger value="content">Content Analytics</TabsTrigger>
          <TabsTrigger value="providers">Provider Performance</TabsTrigger>
          <TabsTrigger value="system">System Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="search">
          <AnalyticsSearchMetrics 
            searchMetrics={analytics?.searchMetrics || null} 
            chartType={chartType}
          />
        </TabsContent>

        <TabsContent value="content">
          <AnalyticsContentMetrics 
            contentMetrics={analytics?.contentMetrics || null}
          />
        </TabsContent>

        <TabsContent value="providers">
          <AnalyticsProviderMetrics 
            providerMetrics={analytics?.providerMetrics || null}
          />
        </TabsContent>

        <TabsContent value="system">
          <AnalyticsSystemMetrics 
            systemMetrics={analytics?.systemMetrics || null}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}