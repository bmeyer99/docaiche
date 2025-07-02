'use client';

/**
 * Monitoring configuration tab
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { 
  BarChart3, 
  Bell, 
  Filter, 
  Download,
  AlertTriangle,
  Info,
  CheckCircle,
  Search,
  ExternalLink,
  Plus,
  RefreshCw,
  Loader2
} from 'lucide-react';
import { HealthIndicator } from '../shared/health-indicator';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';

interface MonitoringConfigProps {
  // No onChangeDetected since this is read-only monitoring
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: string;
  component: string;
  message: string;
  metadata?: any;
}

interface AlertRule {
  id: string;
  name: string;
  condition: string;
  severity: 'low' | 'medium' | 'high';
  enabled: boolean;
  triggered: boolean;
  last_triggered?: string;
}

export function MonitoringConfig({}: MonitoringConfigProps) {
  const [logFilter, setLogFilter] = useState('');
  const [logLevel, setLogLevel] = useState('all');
  const [alerts, setAlerts] = useState<AlertRule[]>([]);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [dashboardUrls, setDashboardUrls] = useState<any>({});
  const apiClient = useApiClient();
  const { toast } = useToast();

  useEffect(() => {
    loadMonitoringData();
  }, []);

  const loadMonitoringData = async () => {
    try {
      setIsLoading(true);
      
      // Load alert rules
      const alertsResponse = await apiClient.getAlertRules();
      if (alertsResponse) {
        setAlerts(alertsResponse);
      }
      
      // Load recent logs
      const logsResponse = await apiClient.getLogs({ limit: 50 });
      if (logsResponse) {
        setLogs(logsResponse);
      }
      
      // Load dashboard configuration
      const dashboardsResponse = await apiClient.getDashboardUrls();
      if (dashboardsResponse) {
        setDashboardUrls(dashboardsResponse);
      }
    } catch (error) {
      console.error('Failed to load monitoring data:', error);
      toast({
        title: "Failed to load monitoring data",
        description: "Some monitoring features may not work correctly",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'destructive';
      case 'medium': return 'default';
      case 'low': return 'secondary';
      default: return 'outline';
    }
  };

  const getLogLevelIcon = (level: string) => {
    switch (level) {
      case 'ERROR': return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'WARN': return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'INFO': return <Info className="h-4 w-4 text-blue-600" />;
      case 'DEBUG': return <Info className="h-4 w-4 text-gray-600" />;
      default: return null;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <Tabs defaultValue="dashboards" className="space-y-4">
        <TabsList>
          <TabsTrigger value="dashboards">Dashboards</TabsTrigger>
          <TabsTrigger value="logs">Logs</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
          <TabsTrigger value="custom">Custom Metrics</TabsTrigger>
        </TabsList>

        {/* Dashboards Tab */}
        <TabsContent value="dashboards" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Monitoring Dashboards</CardTitle>
              <CardDescription>
                Access pre-configured monitoring dashboards
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card 
                    className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => dashboardUrls.search_performance && window.open(dashboardUrls.search_performance, '_blank')}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium flex items-center gap-2">
                            Search Performance
                            <ExternalLink className="h-3 w-3" />
                          </h4>
                          <p className="text-sm text-muted-foreground mt-1">
                            Latency, throughput, and error rates
                          </p>
                        </div>
                        <BarChart3 className="h-5 w-5 text-muted-foreground" />
                      </div>
                    </CardContent>
                  </Card>

                  <Card 
                    className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => dashboardUrls.provider_health && window.open(dashboardUrls.provider_health, '_blank')}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium flex items-center gap-2">
                            Provider Health
                            <ExternalLink className="h-3 w-3" />
                          </h4>
                          <p className="text-sm text-muted-foreground mt-1">
                            Provider status and performance metrics
                          </p>
                        </div>
                        <HealthIndicator status="healthy" showLabel={false} size="sm" />
                      </div>
                    </CardContent>
                  </Card>

                  <Card 
                    className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => dashboardUrls.system_resources && window.open(dashboardUrls.system_resources, '_blank')}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium flex items-center gap-2">
                            System Resources
                            <ExternalLink className="h-3 w-3" />
                          </h4>
                          <p className="text-sm text-muted-foreground mt-1">
                            CPU, memory, and queue utilization
                          </p>
                        </div>
                        <BarChart3 className="h-5 w-5 text-muted-foreground" />
                      </div>
                    </CardContent>
                  </Card>

                  <Card 
                    className="cursor-pointer hover:shadow-md transition-shadow"
                    onClick={() => dashboardUrls.cost_analysis && window.open(dashboardUrls.cost_analysis, '_blank')}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="font-medium flex items-center gap-2">
                            Cost Analysis
                            <ExternalLink className="h-3 w-3" />
                          </h4>
                          <p className="text-sm text-muted-foreground mt-1">
                            Provider costs and budget tracking
                          </p>
                        </div>
                        <BarChart3 className="h-5 w-5 text-muted-foreground" />
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              <div className="mt-6 p-4 bg-muted rounded-lg">
                <p className="text-sm text-muted-foreground">
                  <Info className="h-4 w-4 inline mr-1" />
                  Dashboards open in Grafana. Ensure you're logged in to view them.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Logs Tab */}
        <TabsContent value="logs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>System Logs</CardTitle>
              <CardDescription>
                Real-time log streaming and search
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Input
                      placeholder="Search logs..."
                      value={logFilter}
                      onChange={(e) => setLogFilter(e.target.value)}
                      className="w-full"
                    />
                  </div>
                  <Select value={logLevel} onValueChange={setLogLevel}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Levels</SelectItem>
                      <SelectItem value="error">Error</SelectItem>
                      <SelectItem value="warn">Warning</SelectItem>
                      <SelectItem value="info">Info</SelectItem>
                      <SelectItem value="debug">Debug</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button variant="outline">
                    <Download className="h-4 w-4 mr-2" />
                    Export
                  </Button>
                </div>

                <div className="border rounded-lg overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="w-24">Time</TableHead>
                        <TableHead className="w-20">Level</TableHead>
                        <TableHead className="w-48">Component</TableHead>
                        <TableHead>Message</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody className="font-mono text-sm">
                      {logs.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                            {isLoading ? (
                              <div className="flex items-center justify-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Loading logs...
                              </div>
                            ) : (
                              'No logs found'
                            )}
                          </TableCell>
                        </TableRow>
                      ) : (
                        logs.filter(log => 
                          (logLevel === 'all' || log.level.toLowerCase() === logLevel) &&
                          (logFilter === '' || 
                           log.message.toLowerCase().includes(logFilter.toLowerCase()) ||
                           log.component.toLowerCase().includes(logFilter.toLowerCase()))
                        ).map((log) => (
                          <TableRow key={log.id}>
                            <TableCell className="text-muted-foreground">
                              {new Date(log.timestamp).toLocaleTimeString()}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center gap-1">
                                {getLogLevelIcon(log.level)}
                                <span>{log.level}</span>
                              </div>
                            </TableCell>
                            <TableCell className="text-muted-foreground">
                              {log.component}
                            </TableCell>
                            <TableCell>{log.message}</TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Alert Configuration</CardTitle>
              <CardDescription>
                Configure monitoring alerts and notifications
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {isLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                  </div>
                ) : alerts.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground">
                    <Bell className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No alert rules configured</p>
                    <p className="text-sm mt-2">Click "Add Alert Rule" to create your first alert</p>
                  </div>
                ) : (
                  alerts.map((alert) => (
                    <Card key={alert.id} className={alert.triggered ? 'border-red-500' : ''}>
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="font-medium">{alert.name}</h4>
                              <Badge variant={getSeverityColor(alert.severity)}>
                                {alert.severity}
                              </Badge>
                              {alert.triggered && (
                                <Badge variant="destructive">
                                  <Bell className="h-3 w-3 mr-1" />
                                  Triggered
                                </Badge>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground">
                              Condition: <code className="bg-muted px-1 rounded">{alert.condition}</code>
                            </p>
                            {alert.last_triggered && (
                              <p className="text-xs text-muted-foreground mt-1">
                                Last triggered: {new Date(alert.last_triggered).toLocaleString()}
                              </p>
                            )}
                          </div>
                          
                          <div className="flex items-center gap-2">
                            <Switch 
                              checked={alert.enabled}
                              onCheckedChange={(checked) => toggleAlert(alert.id, checked)}
                            />
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => configureAlert(alert.id)}
                            >
                              Configure
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
                
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={() => {
                    toast({
                      title: "Coming soon",
                      description: "Alert rule creation will be implemented"
                    });
                  }}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Add Alert Rule
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Custom Metrics Tab */}
        <TabsContent value="custom" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Custom Metrics Builder</CardTitle>
              <CardDescription>
                Create custom dashboards and metric queries
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label>Metric Query</Label>
                  <Textarea
                    placeholder="rate(search_requests_total[5m])"
                    className="font-mono"
                    rows={3}
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Visualization Type</Label>
                    <Select defaultValue="line">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="line">Line Chart</SelectItem>
                        <SelectItem value="bar">Bar Chart</SelectItem>
                        <SelectItem value="gauge">Gauge</SelectItem>
                        <SelectItem value="stat">Single Stat</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label>Time Range</Label>
                    <Select defaultValue="1h">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="5m">Last 5 minutes</SelectItem>
                        <SelectItem value="1h">Last hour</SelectItem>
                        <SelectItem value="24h">Last 24 hours</SelectItem>
                        <SelectItem value="7d">Last 7 days</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                
                <div className="flex justify-end gap-2">
                  <Button variant="outline">Preview</Button>
                  <Button>Save to Dashboard</Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );

  const toggleAlert = async (alertId: string, enabled: boolean) => {
    try {
      await apiClient.updateAlertRule(alertId, { enabled });
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId ? { ...alert, enabled } : alert
      ));
      toast({
        title: "Alert updated",
        description: `Alert rule ${enabled ? 'enabled' : 'disabled'}`
      });
    } catch (error) {
      toast({
        title: "Failed to update alert",
        description: "Unable to update alert rule",
        variant: "destructive"
      });
    }
  };

  const configureAlert = (alertId: string) => {
    toast({
      title: "Coming soon",
      description: "Alert configuration dialog will be implemented"
    });
  };
}