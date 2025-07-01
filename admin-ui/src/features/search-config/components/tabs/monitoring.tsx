'use client';

/**
 * Monitoring configuration tab
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
  ExternalLink
} from 'lucide-react';
import { HealthIndicator } from '../shared/health-indicator';

interface MonitoringConfigProps {
  // No onChangeDetected since this is read-only monitoring
}

export function MonitoringConfig({}: MonitoringConfigProps) {
  const [logFilter, setLogFilter] = useState('');
  const [logLevel, setLogLevel] = useState('all');
  const [alerts, setAlerts] = useState([
    {
      id: '1',
      name: 'High Error Rate',
      condition: 'error_rate > 3%',
      severity: 'medium',
      enabled: true,
      triggered: false
    },
    {
      id: '2',
      name: 'Queue Overflow',
      condition: 'queue_depth > 80',
      severity: 'high',
      enabled: true,
      triggered: true
    },
    {
      id: '3',
      name: 'Slow Response Time',
      condition: 'avg_latency > 1000ms',
      severity: 'low',
      enabled: false,
      triggered: false
    }
  ]);

  const logs = [
    { time: '10:45:23', level: 'INFO', component: 'search.orchestrator', message: 'Search completed in 485ms' },
    { time: '10:45:20', level: 'ERROR', component: 'provider.brave', message: 'Rate limit exceeded, circuit breaker opened' },
    { time: '10:45:18', level: 'WARN', component: 'queue.manager', message: 'Queue depth approaching limit: 75/100' },
    { time: '10:45:15', level: 'INFO', component: 'cache.manager', message: 'Cache hit for query hash: abc123...' },
    { time: '10:45:12', level: 'DEBUG', component: 'vector.search', message: 'Querying workspace: python-docs' }
  ];

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
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="cursor-pointer hover:shadow-md transition-shadow">
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

                <Card className="cursor-pointer hover:shadow-md transition-shadow">
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

                <Card className="cursor-pointer hover:shadow-md transition-shadow">
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

                <Card className="cursor-pointer hover:shadow-md transition-shadow">
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
                      icon={<Search className="h-4 w-4" />}
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
                      {logs.map((log, i) => (
                        <TableRow key={i}>
                          <TableCell className="text-muted-foreground">
                            {log.time}
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
                      ))}
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
                {alerts.map((alert) => (
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
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <Switch checked={alert.enabled} />
                          <Button size="sm" variant="ghost">
                            Configure
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                
                <Button variant="outline" className="w-full">
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
}

// Add missing imports
import { Textarea } from '@/components/ui/textarea';
import { Plus, RefreshCw } from 'lucide-react';