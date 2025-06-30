/**
 * Performance Monitoring Dashboard
 * Provides real-time performance metrics and analysis
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Icons } from '@/components/icons';
import { 
  useAdvancedPerformanceMonitor,
  useBundlePerformanceTracker 
} from '@/lib/utils/performance-helpers';

interface PerformanceDashboardProps {
  className?: string;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function PerformanceDashboard({ 
  className, 
  autoRefresh = true, 
  refreshInterval = 5000 
}: PerformanceDashboardProps) {
  const [report, setReport] = useState<any>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const { generateReport, clearMetrics } = useAdvancedPerformanceMonitor('PerformanceDashboard');
  const { trackInitialLoad } = useBundlePerformanceTracker();

  useEffect(() => {
    // Track initial load on mount
    trackInitialLoad();
  }, [trackInitialLoad]);

  const refreshReport = useCallback(() => {
    const newReport = generateReport();
    setReport(newReport);
  }, [generateReport]);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(refreshReport, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, refreshReport]);

  useEffect(() => {
    refreshReport();
  }, [refreshReport]);

  const { slowComponents, bundleHealth } = useMemo(() => {
    if (!report) return { slowComponents: [], healthyComponents: [], bundleHealth: 'good' };

    const slow = report.slowComponents || [];
    
    let health = 'good';
    if (slow.length > 5) health = 'poor';
    else if (slow.length > 2) health = 'warning';

    return {
      slowComponents: slow,
      bundleHealth: health
    };
  }, [report]);

  if (!report) {
    return (
      <div className="animate-pulse bg-muted h-32 rounded-lg flex items-center justify-center">
        <Icons.spinner className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className={className}>
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg">Performance Monitor</CardTitle>
              <CardDescription>Real-time application performance metrics</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={bundleHealth === 'good' ? 'default' : bundleHealth === 'warning' ? 'secondary' : 'destructive'}>
                {bundleHealth.toUpperCase()}
              </Badge>
              <Button
                variant="outline"
                size="sm"
                onClick={refreshReport}
                className="flex items-center gap-1"
              >
                <Icons.refresh className="w-4 h-4" />
                Refresh
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
              >
                {isExpanded ? 'Collapse' : 'Expand'}
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <Card>
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-primary">
                  {report.summary.totalComponents}
                </div>
                <p className="text-xs text-muted-foreground">Total Components</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-destructive">
                  {report.summary.slowComponents}
                </div>
                <p className="text-xs text-muted-foreground">Slow Components</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-success">
                  {report.summary.totalBundleSize}
                </div>
                <p className="text-xs text-muted-foreground">Bundle Size</p>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-4">
                <div className="text-2xl font-bold text-info">
                  {report.summary.loadedChunks}
                </div>
                <p className="text-xs text-muted-foreground">Loaded Chunks</p>
              </CardContent>
            </Card>
          </div>

          {isExpanded && (
            <Tabs defaultValue="components" className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="components">Components</TabsTrigger>
                <TabsTrigger value="bundle">Bundle</TabsTrigger>
                <TabsTrigger value="actions">Actions</TabsTrigger>
              </TabsList>

              <TabsContent value="components" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Slow Components</CardTitle>
                    <CardDescription>Components taking longer than 16ms to render</CardDescription>
                  </CardHeader>
                  <CardContent>
                    {slowComponents.length === 0 ? (
                      <p className="text-center text-muted-foreground py-4">
                        No slow components detected
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {slowComponents.map((component: any, index: number) => (
                          <div
                            key={index}
                            className="flex items-center justify-between p-3 bg-muted rounded-lg"
                          >
                            <div>
                              <div className="font-medium">{component.name}</div>
                              <div className="text-sm text-muted-foreground">
                                {component.renderCount} renders
                                {component.warnings > 0 && (
                                  <Badge variant="destructive" className="ml-2">
                                    {component.warnings} warnings
                                  </Badge>
                                )}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="font-mono text-sm font-medium">
                                {component.averageTime}
                              </div>
                              <div className="text-xs text-muted-foreground">
                                max: {component.maxTime}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="bundle" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Bundle Performance</CardTitle>
                    <CardDescription>Chunk loading times and sizes</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-sm font-medium">Total Size</div>
                          <div className="text-2xl font-bold">{report.bundleMetrics.totalSize}</div>
                        </div>
                        <div>
                          <div className="text-sm font-medium">Chunk Count</div>
                          <div className="text-2xl font-bold">{report.bundleMetrics.chunkCount}</div>
                        </div>
                      </div>

                      {report.bundleMetrics.slowestChunks.length > 0 && (
                        <div>
                          <div className="text-sm font-medium mb-2">Slowest Chunks</div>
                          <div className="space-y-1">
                            {report.bundleMetrics.slowestChunks.map((chunk: any, index: number) => (
                              <div
                                key={index}
                                className="flex items-center justify-between p-2 bg-muted rounded"
                              >
                                <span className="text-sm">{chunk.name}</span>
                                <span className="text-sm font-mono">{chunk.time}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="actions" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Performance Actions</CardTitle>
                    <CardDescription>Tools to manage and optimize performance</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Button
                          variant="outline"
                          onClick={clearMetrics}
                          className="flex items-center gap-2"
                        >
                          <Icons.trash className="w-4 h-4" />
                          Clear All Metrics
                        </Button>

                        <Button
                          variant="outline"
                          onClick={() => {
                            const reportData = JSON.stringify(report, null, 2);
                            const blob = new Blob([reportData], { type: 'application/json' });
                            const url = URL.createObjectURL(blob);
                            const a = document.createElement('a');
                            a.href = url;
                            a.download = `performance-report-${new Date().toISOString()}.json`;
                            a.click();
                            URL.revokeObjectURL(url);
                          }}
                          className="flex items-center gap-2"
                        >
                          <Icons.download className="w-4 h-4" />
                          Export Report
                        </Button>
                      </div>

                      <div className="bg-muted p-4 rounded-lg">
                        <h4 className="font-medium mb-2">Performance Tips</h4>
                        <ul className="text-sm space-y-1 text-muted-foreground">
                          <li>• Components over 16ms cause frame drops</li>
                          <li>• Use React.memo for expensive components</li>
                          <li>• Debounce user inputs to reduce renders</li>
                          <li>• Split large bundles into smaller chunks</li>
                          <li>• Use virtual scrolling for large lists</li>
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Compact performance indicator for production use
 */
export function PerformanceIndicator({ className }: { className?: string }) {
  const [status, setStatus] = useState<'good' | 'warning' | 'poor'>('good');
  const { generateReport } = useAdvancedPerformanceMonitor('PerformanceIndicator');

  useEffect(() => {
    const checkPerformance = () => {
      const report = generateReport();
      const slowComponents = report.slowComponents?.length || 0;
      
      if (slowComponents > 5) setStatus('poor');
      else if (slowComponents > 2) setStatus('warning');
      else setStatus('good');
    };

    const interval = setInterval(checkPerformance, 10000);
    checkPerformance();

    return () => clearInterval(interval);
  }, [generateReport]);

  const statusConfig = {
    good: { color: 'bg-green-500', text: 'Good' },
    warning: { color: 'bg-yellow-500', text: 'Warning' },
    poor: { color: 'bg-red-500', text: 'Poor' }
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${statusConfig[status].color}`} />
      <span className="text-xs text-muted-foreground">
        Performance: {statusConfig[status].text}
      </span>
    </div>
  );
}