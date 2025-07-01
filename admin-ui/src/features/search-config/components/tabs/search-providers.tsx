'use client';

/**
 * Search Providers configuration tab
 */

import React, { useState, useRef, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Progress } from '@/components/ui/progress';
import { 
  Plus, 
  DollarSign, 
  Zap, 
  BarChart3,
  AlertCircle,
  CheckCircle,
  PlayCircle
} from 'lucide-react';
import { ProviderCard } from '../shared/provider-card';
import { HealthIndicator } from '../shared/health-indicator';
import { ProviderStatus, ProviderConfig } from '../../types';

interface SearchProvidersConfigProps {
  onChangeDetected?: () => void;
}

export function SearchProvidersConfig({ onChangeDetected }: SearchProvidersConfigProps) {
  const [providers, setProviders] = useState<ProviderStatus[]>([]);
  const [providerConfigs, setProviderConfigs] = useState<Record<string, ProviderConfig>>({});

  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [isConfigDialogOpen, setIsConfigDialogOpen] = useState(false);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [testResults, setTestResults] = useState<Record<string, any>>({});

  // Fetch providers data on component mount
  useEffect(() => {
    fetchProviders();
  }, []);

  const fetchProviders = async () => {
    try {
      const response = await fetch('/api/v1/mcp/providers');
      if (response.ok) {
        const data = await response.json();
        setProviders(data.providers || []);
        setProviderConfigs(data.configs || {});
      }
    } catch (error) {
      console.error('Failed to fetch providers:', error);
      // Keep empty arrays/objects on error
    }
  };

  // Cost tracking
  const totalMonthlyCost = Object.values(providerConfigs).reduce(
    (sum, config) => sum + (config.cost_limits?.monthly_budget_usd || 0), 0
  );
  const totalDailyRequests = Object.values(providerConfigs).reduce(
    (sum, config) => sum + (config.rate_limits?.requests_per_day || 0), 0
  );

  const handleDragEnd = (result: any) => {
    if (!result.destination) return;

    const items = Array.from(providers);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    // Update priorities based on new order
    const updatedProviders = items.map((provider, index) => ({
      ...provider,
      priority: 100 - (index * 10)
    }));

    setProviders(updatedProviders);
    onChangeDetected?.();
  };

  const handleProviderToggle = (providerId: string, enabled: boolean) => {
    setProviders(prev =>
      prev.map(p => p.id === providerId ? { ...p, enabled } : p)
    );
    setProviderConfigs(prev => ({
      ...prev,
      [providerId]: { ...prev[providerId], enabled }
    }));
    onChangeDetected?.();
  };

  const handleTestProvider = async (providerId: string) => {
    setTestResults(prev => ({ ...prev, [providerId]: { loading: true } }));
    
    try {
      const response = await fetch(`/api/v1/mcp/providers/${providerId}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: 'test search query' }),
      });
      
      if (response.ok) {
        const result = await response.json();
        setTestResults(prev => ({
          ...prev,
          [providerId]: {
            success: true,
            execution_time_ms: result.execution_time_ms,
            results_count: result.results_count,
            sample_results: result.sample_results
          }
        }));
      } else {
        const error = await response.json();
        setTestResults(prev => ({
          ...prev,
          [providerId]: { success: false, error: error.detail || 'Test failed' }
        }));
      }
    } catch (error) {
      setTestResults(prev => ({
        ...prev,
        [providerId]: { success: false, error: 'Network error' }
      }));
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Active Providers</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {providers.filter(p => p.enabled).length} / {providers.length}
            </div>
            <Progress 
              value={(providers.filter(p => p.enabled).length / providers.length) * 100}
              className="mt-2"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Total Monthly Cost</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${totalMonthlyCost.toFixed(2)}</div>
            <p className="text-sm text-muted-foreground mt-1">
              Across all providers
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Daily Request Capacity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalDailyRequests.toLocaleString()}</div>
            <p className="text-sm text-muted-foreground mt-1">
              Combined limit
            </p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="providers" className="space-y-4">
        <TabsList>
          <TabsTrigger value="providers">Providers</TabsTrigger>
          <TabsTrigger value="costs">Cost Management</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        {/* Providers Tab */}
        <TabsContent value="providers" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Search Providers</CardTitle>
                  <CardDescription>
                    Drag to reorder provider priority. Higher priority providers are tried first.
                  </CardDescription>
                </div>
                <Button onClick={() => setIsAddDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Provider
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <DragDropContext onDragEnd={handleDragEnd}>
                <Droppable droppableId="providers">
                  {(provided) => (
                    <div
                      {...provided.droppableProps}
                      ref={provided.innerRef}
                      className="space-y-3"
                    >
                      {providers.map((provider, index) => (
                        <Draggable key={provider.id} draggableId={provider.id} index={index}>
                          {(provided, snapshot) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              style={provided.draggableProps.style}
                              className={snapshot.isDragging ? 'opacity-50' : ''}
                            >
                              <ProviderCard
                                provider={provider}
                                config={providerConfigs[provider.id]}
                                onConfigure={() => {
                                  setSelectedProvider(provider.id);
                                  setIsConfigDialogOpen(true);
                                }}
                                onTest={() => handleTestProvider(provider.id)}
                                onToggle={(enabled) => handleProviderToggle(provider.id, enabled)}
                                draggable
                              />
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </DragDropContext>

              {/* Test Results */}
              {Object.entries(testResults).map(([providerId, result]) => (
                <Alert key={providerId} className="mt-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {result.loading ? (
                      'Testing provider...'
                    ) : result.success ? (
                      <div>
                        <CheckCircle className="h-4 w-4 inline mr-2 text-green-600" />
                        Test successful: {result.results_count} results in {result.execution_time_ms}ms
                      </div>
                    ) : (
                      <div>
                        <AlertCircle className="h-4 w-4 inline mr-2 text-red-600" />
                        Test failed: {result.error}
                      </div>
                    )}
                  </AlertDescription>
                </Alert>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cost Management Tab */}
        <TabsContent value="costs" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Cost Tracking & Limits</CardTitle>
              <CardDescription>
                Monitor and control search provider costs
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {Object.values(providerConfigs).map((config) => (
                <div key={config.id} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-medium">{config.name}</h4>
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-sm">Monthly Budget</Label>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-2xl font-bold">
                          ${config.cost_limits?.monthly_budget_usd || 0}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          / month
                        </span>
                      </div>
                    </div>
                    
                    <div>
                      <Label className="text-sm">Cost per Request</Label>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-2xl font-bold">
                          ${config.cost_limits?.cost_per_request || 0}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          / request
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3">
                    <div className="flex justify-between text-sm mb-1">
                      <span>Current Month Usage</span>
                      <span>${(config as any).current_month_cost || 0} / ${config.cost_limits?.monthly_budget_usd || 0}</span>
                    </div>
                    <Progress value={((config as any).current_month_cost || 0) / (config.cost_limits?.monthly_budget_usd || 100) * 100} />
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Provider Performance</CardTitle>
              <CardDescription>
                Real-time performance metrics and comparisons
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {providers.map((provider) => (
                  <div key={provider.id} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium">{provider.name}</h4>
                      <HealthIndicator status={provider.health} size="sm" />
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Avg Latency</span>
                        <p className="font-medium">
                          {provider.latency_ms ? `${provider.latency_ms}ms` : 'N/A'}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Error Rate</span>
                        <p className="font-medium">
                          {(provider.error_rate * 100).toFixed(1)}%
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Rate Limit</span>
                        <p className="font-medium">
                          {provider.rate_limit_remaining ?? 'N/A'} remaining
                        </p>
                      </div>
                    </div>

                    {provider.health === 'healthy' && (
                      <div className="mt-3">
                        <Progress 
                          value={100 - (provider.error_rate * 100)} 
                          className="h-2"
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Reliability Score
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Configuration Dialog */}
      <Dialog open={isConfigDialogOpen} onOpenChange={setIsConfigDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Configure {selectedProvider && providerConfigs[selectedProvider]?.name}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Provider-specific configuration form would go here */}
            <Alert>
              <AlertDescription>
                Provider configuration form to be implemented based on provider type
              </AlertDescription>
            </Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsConfigDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              // TODO: Save configuration
              setIsConfigDialogOpen(false);
              onChangeDetected?.();
            }}>
              Save Configuration
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Provider Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Search Provider</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Provider Type</Label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Select a provider type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="brave">Brave Search</SelectItem>
                  <SelectItem value="google">Google Custom Search</SelectItem>
                  <SelectItem value="bing">Bing Web Search</SelectItem>
                  <SelectItem value="duckduckgo">DuckDuckGo</SelectItem>
                  <SelectItem value="searxng">SearXNG</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label>Provider Name</Label>
              <Input placeholder="My Search Provider" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsAddDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              // TODO: Add provider
              setIsAddDialogOpen(false);
              onChangeDetected?.();
            }}>
              Add Provider
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}