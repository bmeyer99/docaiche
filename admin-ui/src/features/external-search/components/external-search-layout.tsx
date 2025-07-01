/**
 * External Search Layout Component
 * 
 * Main layout for the external search management interface with tabbed navigation.
 */

'use client';

import React from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { MCPProvidersTab } from './tabs/mcp-providers';
import { MCPConfigTab } from './tabs/mcp-config';
import { MCPPerformanceTab } from './tabs/mcp-performance';
import { MCPTestingTab } from './tabs/mcp-testing';
import { useMCPProviders } from '../hooks/use-mcp-providers';
import { Skeleton } from '@/components/ui/skeleton';

export function ExternalSearchLayout() {
  const { data: providers, isLoading } = useMCPProviders();

  const healthyCount = providers?.healthy_count || 0;
  const totalCount = providers?.total_count || 0;

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Providers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {isLoading ? <Skeleton className="h-8 w-16" /> : totalCount}
            </div>
            <p className="text-xs text-muted-foreground">
              External search providers configured
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Health Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              <div className="text-2xl font-bold">
                {isLoading ? <Skeleton className="h-8 w-16" /> : healthyCount}
              </div>
              <Badge variant={healthyCount === totalCount ? 'default' : 'destructive'}>
                {isLoading ? '...' : healthyCount === totalCount ? 'Healthy' : 'Issues'}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Providers responding normally
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Enhancement Active</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              <Badge variant="default">ON</Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Search results being enhanced
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue="providers" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="providers">Providers</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="testing">Testing</TabsTrigger>
        </TabsList>

        <TabsContent value="providers" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>External Search Providers</CardTitle>
              <CardDescription>
                Manage external search providers like Brave Search, Google, and DuckDuckGo
                to enhance search results with web content.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MCPProvidersTab />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Search Configuration</CardTitle>
              <CardDescription>
                Configure how external search providers are used and how results are cached.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MCPConfigTab />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Metrics</CardTitle>
              <CardDescription>
                Monitor external search performance, cache efficiency, and provider statistics.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MCPPerformanceTab />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="testing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Provider Testing</CardTitle>
              <CardDescription>
                Test external search providers and compare results from different sources.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MCPTestingTab />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}