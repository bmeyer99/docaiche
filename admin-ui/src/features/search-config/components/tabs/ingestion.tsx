'use client';

/**
 * Ingestion configuration tab
 */

import React, { useState } from 'react';
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
  FileText
} from 'lucide-react';

interface IngestionConfigProps {
  onChangeDetected?: () => void;
}

export function IngestionConfig({ onChangeDetected }: IngestionConfigProps) {
  const [rules, setRules] = useState([
    {
      id: '1',
      name: 'Python Documentation',
      enabled: true,
      source_type: 'web',
      workspace: 'python-docs',
      schedule: '0 0 * * *', // Daily at midnight
      filters: {
        url_pattern: 'https://docs.python.org/**',
        content_type: ['text/html', 'text/markdown'],
        min_quality_score: 0.7
      }
    },
    {
      id: '2',
      name: 'GitHub Repositories',
      enabled: true,
      source_type: 'github',
      workspace: 'github-code',
      schedule: '0 */6 * * *', // Every 6 hours
      filters: {
        languages: ['python', 'javascript', 'typescript'],
        stars_min: 100,
        min_quality_score: 0.8
      }
    }
  ]);

  const [qualityThreshold, setQualityThreshold] = useState(0.7);

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
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Add Rule
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {rules.map((rule) => (
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
                        onCheckedChange={(checked) => {
                          setRules(prev => prev.map(r => 
                            r.id === rule.id ? { ...r, enabled: checked } : r
                          ));
                          onChangeDetected?.();
                        }}
                      />
                      <Button size="sm" variant="ghost">
                        Edit
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
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
              Quality Threshold: {(qualityThreshold * 100).toFixed(0)}%
            </Label>
            <Slider
              id="quality-threshold"
              min={0}
              max={1}
              step={0.05}
              value={[qualityThreshold]}
              onValueChange={([value]) => {
                setQualityThreshold(value);
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
                defaultValue="100"
                onChange={() => onChangeDetected?.()}
              />
            </div>
            
            <div>
              <Label htmlFor="max-concurrent">Max Concurrent Jobs</Label>
              <Input
                id="max-concurrent"
                type="number"
                defaultValue="5"
                onChange={() => onChangeDetected?.()}
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="auto-retry"
              defaultChecked
              onCheckedChange={() => onChangeDetected?.()}
            />
            <Label htmlFor="auto-retry">
              Automatically retry failed ingestion jobs
            </Label>
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="dedup"
              defaultChecked
              onCheckedChange={() => onChangeDetected?.()}
            />
            <Label htmlFor="dedup">
              Enable content deduplication
            </Label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent Ingestion Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { status: 'success', name: 'Python 3.12 Documentation', time: '2 hours ago', items: 245 },
              { status: 'running', name: 'React Repository', time: 'In progress', items: 89 },
              { status: 'failed', name: 'Node.js Documentation', time: '4 hours ago', items: 0 }
            ].map((job, i) => (
              <div key={i} className="flex items-center justify-between py-2">
                <div className="flex items-center gap-3">
                  {job.status === 'success' && <CheckCircle className="h-5 w-5 text-green-600" />}
                  {job.status === 'running' && <RefreshCw className="h-5 w-5 text-blue-600 animate-spin" />}
                  {job.status === 'failed' && <AlertCircle className="h-5 w-5 text-red-600" />}
                  
                  <div>
                    <p className="font-medium">{job.name}</p>
                    <p className="text-sm text-muted-foreground">{job.time}</p>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className="text-sm font-medium">{job.items} items</p>
                  <p className="text-xs text-muted-foreground">
                    {job.status === 'success' && 'Completed'}
                    {job.status === 'running' && 'Processing'}
                    {job.status === 'failed' && 'Failed'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}