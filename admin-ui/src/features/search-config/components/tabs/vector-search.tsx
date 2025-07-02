'use client';

/**
 * Vector Search configuration tab
 */

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { 
  Plus, 
  Settings, 
  PlayCircle, 
  Check, 
  X, 
  RefreshCw,
  Database,
  Search,
  Tag,
  Folder
} from 'lucide-react';
import { HealthIndicator } from '../shared/health-indicator';
import { VectorConnectionConfig, WorkspaceConfig } from '../../types';

interface VectorSearchConfigProps {
  onChangeDetected?: () => void;
}

export function VectorSearchConfig({ onChangeDetected }: VectorSearchConfigProps) {
  const [connectionStatus, setConnectionStatus] = useState({
    connected: true,
    endpoint: 'http://localhost:3001/api',
    version: '1.0.0',
    workspaces_count: 5
  });
  const [workspaces, setWorkspaces] = useState<WorkspaceConfig[]>([]);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [selectedWorkspace, setSelectedWorkspace] = useState<WorkspaceConfig | null>(null);
  const [isWorkspaceDialogOpen, setIsWorkspaceDialogOpen] = useState(false);
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState<any[]>([]);

  const { register, handleSubmit, watch, setValue } = useForm<VectorConnectionConfig>({
    defaultValues: {
      base_url: 'http://localhost:3001/api',
      api_key: '',
      timeout_seconds: 30,
      max_retries: 3,
      verify_ssl: true
    }
  });

  useEffect(() => {
    // Load workspaces
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    // TODO: Load from API
    setWorkspaces([
      {
        id: 'ws_001',
        name: 'Python Documentation',
        slug: 'python-docs',
        description: 'Official Python documentation and tutorials',
        technologies: ['python'],
        tags: ['official', 'documentation'],
        priority: 100,
        active: true,
        search_settings: { similarity_threshold: 0.7 }
      },
      {
        id: 'ws_002',
        name: 'JavaScript MDN',
        slug: 'javascript-mdn',
        description: 'MDN Web Docs for JavaScript',
        technologies: ['javascript', 'typescript'],
        tags: ['mdn', 'web'],
        priority: 90,
        active: true,
        search_settings: { similarity_threshold: 0.75 }
      }
    ]);
  };

  const handleConnectionTest = async () => {
    setIsTestingConnection(true);
    try {
      // TODO: Test connection
      await new Promise(resolve => setTimeout(resolve, 1500));
      setConnectionStatus(prev => ({ ...prev, connected: true }));
    } catch (error) {
      setConnectionStatus(prev => ({ ...prev, connected: false }));
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleWorkspaceToggle = (workspaceId: string, enabled: boolean) => {
    setWorkspaces(prev => 
      prev.map(ws => 
        ws.id === workspaceId ? { ...ws, active: enabled } : ws
      )
    );
    onChangeDetected?.();
  };

  const handleTestSearch = async () => {
    if (!testQuery.trim()) return;
    
    // TODO: Perform test search
    setTestResults([
      {
        id: '1',
        title: 'Python Async/Await Tutorial',
        content: 'Learn how to use async and await in Python...',
        score: 0.95,
        workspace: 'python-docs'
      },
      {
        id: '2',
        title: 'Understanding Python Coroutines',
        content: 'Deep dive into Python coroutines and event loops...',
        score: 0.87,
        workspace: 'python-docs'
      }
    ]);
  };

  return (
    <div className="p-6 space-y-6">
      <Tabs defaultValue="connection" className="space-y-4">
        <TabsList>
          <TabsTrigger value="connection">Connection</TabsTrigger>
          <TabsTrigger value="workspaces">Workspaces</TabsTrigger>
          <TabsTrigger value="testing">Testing</TabsTrigger>
        </TabsList>

        {/* Connection Tab */}
        <TabsContent value="connection" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Weaviate Connection</CardTitle>
              <CardDescription>
                Configure the connection to your Weaviate vector database
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit((data) => {
                console.log('Save connection config:', data);
                onChangeDetected?.();
              })} className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="flex-1 space-y-4">
                    <div>
                      <Label htmlFor="base_url">Base URL</Label>
                      <Input
                        id="base_url"
                        {...register('base_url')}
                        placeholder="http://localhost:3001/api"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="api_key">API Key (Optional)</Label>
                      <Input
                        id="api_key"
                        type="password"
                        {...register('api_key')}
                        placeholder="Enter API key if required"
                      />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
                        <Input
                          id="timeout_seconds"
                          type="number"
                          {...register('timeout_seconds', { valueAsNumber: true })}
                        />
                      </div>
                      
                      <div>
                        <Label htmlFor="max_retries">Max Retries</Label>
                        <Input
                          id="max_retries"
                          type="number"
                          {...register('max_retries', { valueAsNumber: true })}
                        />
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="verify_ssl"
                        {...register('verify_ssl')}
                      />
                      <Label htmlFor="verify_ssl">Verify SSL Certificate</Label>
                    </div>
                  </div>

                  <div className="w-64 space-y-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Connection Status</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <HealthIndicator 
                          status={connectionStatus.connected ? 'healthy' : 'unhealthy'}
                          label={connectionStatus.connected ? 'Connected' : 'Disconnected'}
                        />
                        
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Version:</span>
                            <span>{connectionStatus.version || 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Workspaces:</span>
                            <span>{connectionStatus.workspaces_count}</span>
                          </div>
                        </div>
                        
                        <Button 
                          size="sm" 
                          className="w-full"
                          onClick={handleConnectionTest}
                          disabled={isTestingConnection}
                        >
                          {isTestingConnection ? (
                            <>
                              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                              Testing...
                            </>
                          ) : (
                            <>
                              <PlayCircle className="h-4 w-4 mr-2" />
                              Test Connection
                            </>
                          )}
                        </Button>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button type="submit">Save Connection Settings</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Workspaces Tab */}
        <TabsContent value="workspaces" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Workspace Management</CardTitle>
                  <CardDescription>
                    Configure workspaces and technology mappings
                  </CardDescription>
                </div>
                <Button onClick={() => setIsWorkspaceDialogOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Workspace
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Technologies</TableHead>
                    <TableHead>Tags</TableHead>
                    <TableHead>Priority</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {workspaces.map((workspace) => (
                    <TableRow key={workspace.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{workspace.name}</p>
                          <p className="text-sm text-muted-foreground">{workspace.description}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1 flex-wrap">
                          {workspace.technologies.map(tech => (
                            <Badge key={tech} variant="secondary">
                              {tech}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1 flex-wrap">
                          {workspace.tags.map(tag => (
                            <Badge key={tag} variant="outline">
                              <Tag className="h-3 w-3 mr-1" />
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell>{workspace.priority}</TableCell>
                      <TableCell>
                        <Switch
                          checked={workspace.active}
                          onCheckedChange={(checked) => handleWorkspaceToggle(workspace.id, checked)}
                        />
                      </TableCell>
                      <TableCell>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setSelectedWorkspace(workspace);
                            setIsWorkspaceDialogOpen(true);
                          }}
                        >
                          <Settings className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Testing Tab */}
        <TabsContent value="testing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Test Vector Search</CardTitle>
              <CardDescription>
                Test search queries against your configured workspaces
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <Input
                  placeholder="Enter a test query..."
                  value={testQuery}
                  onChange={(e) => setTestQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleTestSearch()}
                />
                <Button onClick={handleTestSearch}>
                  <Search className="h-4 w-4 mr-2" />
                  Search
                </Button>
              </div>

              {testResults.length > 0 && (
                <div className="space-y-3">
                  <h4 className="font-medium">Results ({testResults.length})</h4>
                  {testResults.map((result) => (
                    <Card key={result.id}>
                      <CardContent className="pt-4">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h5 className="font-medium">{result.title}</h5>
                            <p className="text-sm text-muted-foreground mt-1">
                              {result.content}
                            </p>
                          </div>
                          <div className="ml-4 text-right">
                            <Badge variant="secondary">{result.workspace}</Badge>
                            <p className="text-sm text-muted-foreground mt-1">
                              Score: {(result.score * 100).toFixed(0)}%
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Workspace Dialog */}
      <Dialog open={isWorkspaceDialogOpen} onOpenChange={setIsWorkspaceDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {selectedWorkspace ? 'Edit Workspace' : 'Add Workspace'}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {/* Workspace form fields would go here */}
            <p className="text-muted-foreground">
              Workspace configuration form to be implemented
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsWorkspaceDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              // TODO: Save workspace
              setIsWorkspaceDialogOpen(false);
              onChangeDetected?.();
            }}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}