'use client';

/**
 * Ingestion configuration tab
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { 
  Plus, 
  Calendar, 
  Filter, 
  Folder,
  Clock,
  CheckCircle,
  AlertCircle,
  FileText,
  RefreshCw,
  Loader2,
  Trash2
} from 'lucide-react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { useSearchConfig } from '../../contexts/config-context';

interface IngestionConfigProps {
  onChangeDetected?: () => void;
}

interface IngestionRule {
  id: string;
  name: string;
  enabled: boolean;
  source_type: string;
  workspace: string;
  schedule?: string;
  filters?: any;
  config?: any;
}

interface IngestionSettings {
  quality_threshold: number;
  batch_size: number;
  max_concurrent_jobs: number;
  auto_retry_enabled: boolean;
  deduplication_enabled: boolean;
}

export function IngestionConfig({ onChangeDetected }: IngestionConfigProps) {
  const apiClient = useApiClient();
  const { toast } = useToast();
  const { 
    ingestionRules: loadedRules, 
    ingestionSettings: loadedSettings, 
    updateIngestionRules, 
    updateIngestionSettings 
  } = useSearchConfig();
  
  // Use pre-loaded configuration
  const [rules, setRules] = useState<IngestionRule[]>(loadedRules || []);
  const [settings, setSettings] = useState<IngestionSettings>(
    loadedSettings || {
      quality_threshold: 0.7,
      batch_size: 100,
      max_concurrent_jobs: 5,
      auto_retry_enabled: true,
      deduplication_enabled: true
    }
  );
  const [recentJobs, setRecentJobs] = useState<any[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Update local state when context changes
  useEffect(() => {
    if (loadedRules) {
      setRules(loadedRules);
    }
    if (loadedSettings) {
      setSettings(loadedSettings);
    }
  }, [loadedRules, loadedSettings]);
  
  // Load recent jobs (not pre-loaded)
  useEffect(() => {
    loadRecentJobs();
  }, []);

  const loadRecentJobs = async () => {
    try {
      const jobsResponse = await apiClient.getIngestionJobs({ limit: 10 });
      if (jobsResponse) {
        setRecentJobs(jobsResponse);
      }
    } catch (error: any) {
      // Handle 404 gracefully - endpoint not implemented yet
      if (error?.message?.includes('404')) {
        console.warn('[Ingestion] Recent jobs endpoint not implemented yet (/ingestion/jobs)');
        setRecentJobs([]); // Set empty array instead of undefined
      } else {
        console.error('Failed to load recent jobs:', error);
      }
    }
  };

  const toggleRule = async (ruleId: string, enabled: boolean) => {
    try {
      await apiClient.updateIngestionRule(ruleId, { enabled });
      setRules(prev => prev.map(rule => 
        rule.id === ruleId ? { ...rule, enabled } : rule
      ));
      toast({
        title: "Rule updated",
        description: `Ingestion rule ${enabled ? 'enabled' : 'disabled'}`
      });
      onChangeDetected?.();
    } catch (error) {
      toast({
        title: "Failed to update rule",
        description: "Unable to update ingestion rule",
        variant: "destructive"
      });
    }
  };

  const deleteRule = async (ruleId: string) => {
    if (!confirm('Are you sure you want to delete this ingestion rule?')) {
      return;
    }
    
    try {
      await apiClient.deleteIngestionRule(ruleId);
      const updatedRules = rules.filter(rule => rule.id !== ruleId);
      setRules(updatedRules);
      updateIngestionRules(updatedRules);
      toast({
        title: "Rule deleted",
        description: "Ingestion rule deleted successfully"
      });
    } catch (error) {
      toast({
        title: "Failed to delete rule",
        description: "Unable to delete ingestion rule",
        variant: "destructive"
      });
    }
  };

  const saveSettings = async () => {
    try {
      setIsSaving(true);
      const updated = await apiClient.updateIngestionSettings(settings);
      updateIngestionSettings(updated);
      toast({
        title: "Settings saved",
        description: "Ingestion settings updated successfully"
      });
    } catch (error) {
      toast({
        title: "Failed to save settings",
        description: "Unable to save ingestion settings",
        variant: "destructive"
      });
    } finally {
      setIsSaving(false);
    }
  };


  return (
    <div className="p-6 space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Content Ingestion Rules</CardTitle>
              <CardDescription>
                Configure automated content ingestion and workspace assignment
              </CardDescription>
            </div>
            <Button onClick={() => {
              // TODO: Add new rule dialog
              toast({
                title: "Coming soon",
                description: "Rule creation dialog will be implemented"
              });
            }}>
              <Plus className="h-4 w-4 mr-2" />
              Add Rule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {rules.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No ingestion rules configured</p>
                <p className="text-sm mt-2">Click "Add Rule" to create your first ingestion rule</p>
              </div>
            ) : (
              rules.map((rule) => (
              <Card key={rule.id}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <h4 className="font-medium">{rule.name}</h4>
                        <Badge variant={rule.enabled ? 'default' : 'secondary'}>
                          {rule.enabled ? 'Active' : 'Inactive'}
                        </Badge>
                        <Badge variant="outline">
                          <FileText className="h-3 w-3 mr-1" />
                          {rule.source_type}
                        </Badge>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <div className="flex items-center gap-1 text-muted-foreground">
                            <Folder className="h-3 w-3" />
                            <span>Workspace:</span>
                          </div>
                          <p className="font-medium">{rule.workspace}</p>
                        </div>
                        
                        <div>
                          <div className="flex items-center gap-1 text-muted-foreground">
                            <Clock className="h-3 w-3" />
                            <span>Schedule:</span>
                          </div>
                          <p className="font-medium">
                            {rule.schedule === '0 0 * * *' ? 'Daily' : 'Every 6 hours'}
                          </p>
                        </div>
                      </div>

                      <div className="mt-2 text-sm">
                        <span className="text-muted-foreground">Quality threshold:</span>
                        <span className="ml-2 font-medium">
                          {rule.filters.min_quality_score * 100}%
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Switch 
                        checked={rule.enabled}
                        onCheckedChange={(checked) => toggleRule(rule.id, checked)}
                      />
                      <Button 
                        size="sm" 
                        variant="ghost"
                        onClick={() => {
                          // TODO: Add edit rule dialog
                          toast({
                            title: "Coming soon",
                            description: "Rule editing will be implemented"
                          });
                        }}
                      >
                        Edit
                      </Button>
                      <Button 
                        size="sm" 
                        variant="ghost"
                        onClick={() => deleteRule(rule.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Global Ingestion Settings</CardTitle>
          <CardDescription>
            Configure default settings for all content ingestion
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="quality-threshold">
              Quality Threshold: {(settings.quality_threshold * 100).toFixed(0)}%
            </Label>
            <Slider
              id="quality-threshold"
              min={0}
              max={1}
              step={0.05}
              value={[settings.quality_threshold]}
              onValueChange={([value]) => {
                setSettings(prev => ({ ...prev, quality_threshold: value }));
                onChangeDetected?.();
              }}
              className="mt-2"
            />
            <p className="text-xs text-muted-foreground mt-1">
              Content below this quality score will be rejected
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="batch-size">Batch Size</Label>
              <Input
                id="batch-size"
                type="number"
                value={settings.batch_size}
                onChange={(e) => {
                  setSettings(prev => ({ ...prev, batch_size: parseInt(e.target.value) || 100 }));
                  onChangeDetected?.();
                }}
              />
            </div>
            
            <div>
              <Label htmlFor="max-concurrent">Max Concurrent Jobs</Label>
              <Input
                id="max-concurrent"
                type="number"
                value={settings.max_concurrent_jobs}
                onChange={(e) => {
                  setSettings(prev => ({ ...prev, max_concurrent_jobs: parseInt(e.target.value) || 5 }));
                  onChangeDetected?.();
                }}
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="auto-retry"
              checked={settings.auto_retry_enabled}
              onCheckedChange={(checked) => {
                setSettings(prev => ({ ...prev, auto_retry_enabled: checked }));
                onChangeDetected?.();
              }}
            />
            <Label htmlFor="auto-retry">
              Automatically retry failed ingestion jobs
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="dedup"
              checked={settings.deduplication_enabled}
              onCheckedChange={(checked) => {
                setSettings(prev => ({ ...prev, deduplication_enabled: checked }));
                onChangeDetected?.();
              }}
            />
            <Label htmlFor="dedup">
              Enable content deduplication
            </Label>
          </div>

          <div className="flex justify-end pt-4">
            <Button 
              onClick={saveSettings}
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Settings'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Ingestion Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentJobs.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Clock className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No ingestion jobs found</p>
                <p className="text-sm mt-2">Jobs will appear here when ingestion rules are run</p>
              </div>
            ) : (
              recentJobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  {job.status === 'completed' && <CheckCircle className="h-5 w-5 text-green-600" />}
                  {job.status === 'running' && <RefreshCw className="h-5 w-5 text-blue-600 animate-spin" />}
                  {job.status === 'failed' && <AlertCircle className="h-5 w-5 text-red-600" />}
                  {job.status === 'pending' && <Clock className="h-5 w-5 text-gray-400" />}
                  
                  <div>
                    <p className="font-medium">{job.rule_name || 'Manual Ingestion'}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(job.started_at || job.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="text-sm font-medium">{job.documents_processed || 0} items</p>
                  <p className="text-xs text-muted-foreground">
                    {job.status === 'completed' && 'Completed'}
                    {job.status === 'running' && 'Processing'}
                    {job.status === 'failed' && job.error || 'Failed'}
                    {job.status === 'pending' && 'Waiting'}
                  </p>
                </div>
              </div>
            ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}