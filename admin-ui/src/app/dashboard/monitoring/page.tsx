'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CalendarDateRangePicker } from '@/components/date-range-picker';
import { RefreshCw, Maximize2, Activity, Database, Server, Globe } from 'lucide-react';

export default function MonitoringPage() {
  const [selectedTimeRange, setSelectedTimeRange] = useState('1h');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedView, setSelectedView] = useState('overview');

  return (
    <div className="flex-1 space-y-4 p-8 pt-6">
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Interactive Monitoring</h2>
        <div className="flex items-center space-x-2">
          <CalendarDateRangePicker />
          <Select value={selectedTimeRange} onValueChange={setSelectedTimeRange}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Select time range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5m">Last 5 minutes</SelectItem>
              <SelectItem value="15m">Last 15 minutes</SelectItem>
              <SelectItem value="1h">Last 1 hour</SelectItem>
              <SelectItem value="6h">Last 6 hours</SelectItem>
              <SelectItem value="24h">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant={autoRefresh ? "default" : "outline"}
            size="icon"
            onClick={() => setAutoRefresh(!autoRefresh)}
            title={autoRefresh ? "Auto-refresh enabled" : "Auto-refresh disabled"}
          >
            <RefreshCw className={`h-4 w-4 ${autoRefresh ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <Tabs value={selectedView} onValueChange={setSelectedView} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">System Overview</TabsTrigger>
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="infrastructure">Infrastructure</TabsTrigger>
          <TabsTrigger value="custom">Custom Dashboards</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Requests</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">45,231</div>
                <p className="text-xs text-muted-foreground">
                  +20.1% from last hour
                </p>
                <div className="mt-4 h-[80px]" id="requests-mini-chart">
                  {/* Mini chart will go here */}
                </div>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Error Rate</CardTitle>
                <Globe className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">0.12%</div>
                <p className="text-xs text-muted-foreground">
                  -4.5% from last hour
                </p>
                <div className="mt-4 h-[80px]" id="errors-mini-chart">
                  {/* Mini chart will go here */}
                </div>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Avg Response Time</CardTitle>
                <Server className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">124ms</div>
                <p className="text-xs text-muted-foreground">
                  +2ms from last hour
                </p>
                <div className="mt-4 h-[80px]" id="latency-mini-chart">
                  {/* Mini chart will go here */}
                </div>
              </CardContent>
            </Card>

            <Card className="cursor-pointer hover:shadow-lg transition-shadow">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Services</CardTitle>
                <Database className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">12/12</div>
                <p className="text-xs text-muted-foreground">
                  All services healthy
                </p>
                <div className="mt-4 h-[80px]" id="services-mini-chart">
                  {/* Mini chart will go here */}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Request Volume</CardTitle>
                <Button size="icon" variant="ghost">
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]" id="request-volume-chart">
                  {/* Main interactive chart will go here */}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle>Service Health</CardTitle>
                <Button size="icon" variant="ghost">
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </CardHeader>
              <CardContent>
                <div className="h-[300px]" id="service-health-chart">
                  {/* Service health chart will go here */}
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>System Metrics Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[400px]" id="system-timeline-chart">
                {/* Timeline chart will go here */}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="services" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Service-Level Monitoring</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Service-specific dashboards will be implemented here</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="infrastructure" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Infrastructure Monitoring</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Container and system-level metrics will be shown here</p>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="custom" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Custom Dashboards</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-muted-foreground">Create and manage custom dashboard views</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}