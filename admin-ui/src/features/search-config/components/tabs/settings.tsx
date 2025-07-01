'use client';

/**
 * System Settings tab
 */

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { 
  Settings, 
  Upload, 
  Download, 
  RotateCcw,
  Shield,
  Zap,
  Database,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { SearchConfiguration } from '../../types';

interface SystemSettingsProps {
  onChangeDetected?: () => void;
}

export function SystemSettings({ onChangeDetected }: SystemSettingsProps) {
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [isExportDialogOpen, setIsExportDialogOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);

  const { register, handleSubmit, watch, setValue } = useForm<SearchConfiguration>({
    defaultValues: {
      queue_management: {
        max_queue_depth: 100,
        overflow_strategy: 'reject',
        priority_levels: 3,
        stale_timeout_seconds: 300
      },
      rate_limiting: {
        per_user_rate_limit: 60,
        global_rate_limit: 1000,
        burst_size: 10,
        rate_limit_window_seconds: 60
      },
      timeouts: {
        search_timeout_seconds: 30,
        ai_timeout_seconds: 30,
        provider_timeout_seconds: 10,
        cache_ttl_seconds: 3600
      },
      performance_thresholds: {
        max_search_latency_ms: 1000,
        max_ai_latency_ms: 2000,
        min_cache_hit_rate: 0.6,
        max_error_rate: 0.05
      },
      resource_limits: {
        max_concurrent_searches: 50,
        max_ai_calls_per_minute: 100,
        max_provider_calls_per_minute: 500,
        max_cache_size_mb: 1024
      },
      feature_toggles: {
        enable_external_search: true,
        enable_ai_evaluation: true,
        enable_query_refinement: true,
        enable_knowledge_ingestion: true,
        enable_result_caching: true
      },
      advanced_settings: {
        workspace_selection_strategy: 'ai_guided',
        result_ranking_algorithm: 'hybrid',
        external_provider_priority: ['brave', 'google', 'bing']
      }
    }
  });

  const handleExport = async () => {
    // TODO: Export configuration
    const config = watch();
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `search-config-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setIsExportDialogOpen(false);
  };

  const handleImport = async () => {
    if (!importFile) return;
    
    // TODO: Import and validate configuration
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const config = JSON.parse(e.target?.result as string);
        // Validate and apply config
        console.log('Importing config:', config);
        setIsImportDialogOpen(false);
        onChangeDetected?.();
      } catch (error) {
        console.error('Invalid configuration file:', error);
      }
    };
    reader.readAsText(importFile);
  };

  return (
    <div className="p-6 space-y-6">
      <Tabs defaultValue="global" className="space-y-4">
        <TabsList>
          <TabsTrigger value="global">Global Settings</TabsTrigger>
          <TabsTrigger value="queues">Queue Management</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
          <TabsTrigger value="features">Feature Flags</TabsTrigger>
          <TabsTrigger value="maintenance">Maintenance</TabsTrigger>
        </TabsList>

        {/* Global Settings Tab */}
        <TabsContent value="global" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Rate Limiting</CardTitle>
              <CardDescription>
                Configure request rate limits to prevent abuse
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="per_user_rate_limit">Per User Rate Limit</Label>
                  <Input
                    id="per_user_rate_limit"
                    type="number"
                    {...register('rate_limiting.per_user_rate_limit', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                  <p className="text-xs text-muted-foreground mt-1">Requests per minute</p>
                </div>
                
                <div>
                  <Label htmlFor="global_rate_limit">Global Rate Limit</Label>
                  <Input
                    id="global_rate_limit"
                    type="number"
                    {...register('rate_limiting.global_rate_limit', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                  <p className="text-xs text-muted-foreground mt-1">Total requests per minute</p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="burst_size">Burst Size</Label>
                  <Input
                    id="burst_size"
                    type="number"
                    {...register('rate_limiting.burst_size', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
                
                <div>
                  <Label htmlFor="rate_limit_window">Window (seconds)</Label>
                  <Input
                    id="rate_limit_window"
                    type="number"
                    {...register('rate_limiting.rate_limit_window_seconds', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Timeouts</CardTitle>
              <CardDescription>
                Configure timeout values for different operations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="search_timeout">Search Timeout (seconds)</Label>
                  <Input
                    id="search_timeout"
                    type="number"
                    {...register('timeouts.search_timeout_seconds', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
                
                <div>
                  <Label htmlFor="ai_timeout">AI Timeout (seconds)</Label>
                  <Input
                    id="ai_timeout"
                    type="number"
                    {...register('timeouts.ai_timeout_seconds', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="provider_timeout">Provider Timeout (seconds)</Label>
                  <Input
                    id="provider_timeout"
                    type="number"
                    {...register('timeouts.provider_timeout_seconds', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
                
                <div>
                  <Label htmlFor="cache_ttl">Cache TTL (seconds)</Label>
                  <Input
                    id="cache_ttl"
                    type="number"
                    {...register('timeouts.cache_ttl_seconds', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Queue Management Tab */}
        <TabsContent value="queues" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Queue Configuration</CardTitle>
              <CardDescription>
                Manage search request queue behavior
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="max_queue_depth">
                  Maximum Queue Depth: {watch('queue_management.max_queue_depth')}
                </Label>
                <Slider
                  id="max_queue_depth"
                  min={10}
                  max={500}
                  step={10}
                  value={[watch('queue_management.max_queue_depth')]}
                  onValueChange={([value]) => {
                    setValue('queue_management.max_queue_depth', value);
                    onChangeDetected?.();
                  }}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="overflow_strategy">Overflow Strategy</Label>
                <Select
                  value={watch('queue_management.overflow_strategy')}
                  onValueChange={(value: 'reject' | 'evict_oldest') => {
                    setValue('queue_management.overflow_strategy', value);
                    onChangeDetected?.();
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="reject">Reject New Requests</SelectItem>
                    <SelectItem value="evict_oldest">Evict Oldest</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="priority_levels">Priority Levels</Label>
                  <Input
                    id="priority_levels"
                    type="number"
                    {...register('queue_management.priority_levels', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
                
                <div>
                  <Label htmlFor="stale_timeout">Stale Timeout (seconds)</Label>
                  <Input
                    id="stale_timeout"
                    type="number"
                    {...register('queue_management.stale_timeout_seconds', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Performance Tab */}
        <TabsContent value="performance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Performance Thresholds</CardTitle>
              <CardDescription>
                Set performance targets and limits
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="max_search_latency">Max Search Latency (ms)</Label>
                  <Input
                    id="max_search_latency"
                    type="number"
                    {...register('performance_thresholds.max_search_latency_ms', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
                
                <div>
                  <Label htmlFor="max_ai_latency">Max AI Latency (ms)</Label>
                  <Input
                    id="max_ai_latency"
                    type="number"
                    {...register('performance_thresholds.max_ai_latency_ms', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="min_cache_hit_rate">
                  Minimum Cache Hit Rate: {(watch('performance_thresholds.min_cache_hit_rate') * 100).toFixed(0)}%
                </Label>
                <Slider
                  id="min_cache_hit_rate"
                  min={0}
                  max={1}
                  step={0.05}
                  value={[watch('performance_thresholds.min_cache_hit_rate')]}
                  onValueChange={([value]) => {
                    setValue('performance_thresholds.min_cache_hit_rate', value);
                    onChangeDetected?.();
                  }}
                  className="mt-2"
                />
              </div>

              <div>
                <Label htmlFor="max_error_rate">
                  Maximum Error Rate: {(watch('performance_thresholds.max_error_rate') * 100).toFixed(1)}%
                </Label>
                <Slider
                  id="max_error_rate"
                  min={0}
                  max={0.1}
                  step={0.005}
                  value={[watch('performance_thresholds.max_error_rate')]}
                  onValueChange={([value]) => {
                    setValue('performance_thresholds.max_error_rate', value);
                    onChangeDetected?.();
                  }}
                  className="mt-2"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Resource Limits</CardTitle>
              <CardDescription>
                Configure resource usage limits
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="max_concurrent">Max Concurrent Searches</Label>
                  <Input
                    id="max_concurrent"
                    type="number"
                    {...register('resource_limits.max_concurrent_searches', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
                
                <div>
                  <Label htmlFor="max_cache_size">Max Cache Size (MB)</Label>
                  <Input
                    id="max_cache_size"
                    type="number"
                    {...register('resource_limits.max_cache_size_mb', { valueAsNumber: true })}
                    onChange={() => onChangeDetected?.()}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Feature Flags Tab */}
        <TabsContent value="features" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Feature Toggles</CardTitle>
              <CardDescription>
                Enable or disable system features
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>External Search</Label>
                    <p className="text-sm text-muted-foreground">
                      Enable fallback to external search providers
                    </p>
                  </div>
                  <Switch
                    checked={watch('feature_toggles.enable_external_search')}
                    onCheckedChange={(checked) => {
                      setValue('feature_toggles.enable_external_search', checked);
                      onChangeDetected?.();
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>AI Evaluation</Label>
                    <p className="text-sm text-muted-foreground">
                      Use AI to evaluate search result relevance
                    </p>
                  </div>
                  <Switch
                    checked={watch('feature_toggles.enable_ai_evaluation')}
                    onCheckedChange={(checked) => {
                      setValue('feature_toggles.enable_ai_evaluation', checked);
                      onChangeDetected?.();
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Query Refinement</Label>
                    <p className="text-sm text-muted-foreground">
                      Allow AI to refine queries for better results
                    </p>
                  </div>
                  <Switch
                    checked={watch('feature_toggles.enable_query_refinement')}
                    onCheckedChange={(checked) => {
                      setValue('feature_toggles.enable_query_refinement', checked);
                      onChangeDetected?.();
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Knowledge Ingestion</Label>
                    <p className="text-sm text-muted-foreground">
                      Enable automatic content ingestion
                    </p>
                  </div>
                  <Switch
                    checked={watch('feature_toggles.enable_knowledge_ingestion')}
                    onCheckedChange={(checked) => {
                      setValue('feature_toggles.enable_knowledge_ingestion', checked);
                      onChangeDetected?.();
                    }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Result Caching</Label>
                    <p className="text-sm text-muted-foreground">
                      Cache search results for improved performance
                    </p>
                  </div>
                  <Switch
                    checked={watch('feature_toggles.enable_result_caching')}
                    onCheckedChange={(checked) => {
                      setValue('feature_toggles.enable_result_caching', checked);
                      onChangeDetected?.();
                    }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Maintenance Tab */}
        <TabsContent value="maintenance" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Configuration Management</CardTitle>
              <CardDescription>
                Import, export, and reset configuration
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button variant="outline" onClick={() => setIsExportDialogOpen(true)}>
                  <Download className="h-4 w-4 mr-2" />
                  Export Config
                </Button>
                
                <Button variant="outline" onClick={() => setIsImportDialogOpen(true)}>
                  <Upload className="h-4 w-4 mr-2" />
                  Import Config
                </Button>
                
                <Button variant="outline" className="text-red-600">
                  <RotateCcw className="h-4 w-4 mr-2" />
                  Reset to Defaults
                </Button>
              </div>

              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  Always export your current configuration before making significant changes.
                  Configuration changes take effect immediately.
                </AlertDescription>
              </Alert>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>System Maintenance</CardTitle>
              <CardDescription>
                Perform system maintenance tasks
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium">Clear Cache</h4>
                        <p className="text-sm text-muted-foreground mt-1">
                          Remove all cached search results
                        </p>
                      </div>
                      <Button size="sm" variant="destructive">
                        Clear
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium">Rebuild Indexes</h4>
                        <p className="text-sm text-muted-foreground mt-1">
                          Rebuild vector search indexes
                        </p>
                      </div>
                      <Button size="sm" variant="outline">
                        Rebuild
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Export Dialog */}
      <Dialog open={isExportDialogOpen} onOpenChange={setIsExportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Export Configuration</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="flex items-center space-x-2">
              <Switch id="include-secrets" />
              <Label htmlFor="include-secrets">Include secrets (API keys)</Label>
            </div>
            
            <Alert>
              <Shield className="h-4 w-4" />
              <AlertDescription>
                Exported configurations may contain sensitive information. 
                Handle with care.
              </AlertDescription>
            </Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsExportDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleExport}>
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Import Dialog */}
      <Dialog open={isImportDialogOpen} onOpenChange={setIsImportDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Import Configuration</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Configuration File</Label>
              <Input
                type="file"
                accept=".json"
                onChange={(e) => setImportFile(e.target.files?.[0] || null)}
              />
            </div>
            
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Importing will replace your current configuration. 
                Make sure to backup first.
              </AlertDescription>
            </Alert>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsImportDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleImport} disabled={!importFile}>
              <Upload className="h-4 w-4 mr-2" />
              Import
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}