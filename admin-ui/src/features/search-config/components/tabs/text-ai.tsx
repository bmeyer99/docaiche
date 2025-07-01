'use client';

/**
 * Text AI configuration tab
 */

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Bot, 
  Sparkles, 
  Play, 
  History, 
  FlaskConical,
  Lightbulb,
  Code,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { HealthIndicator } from '../shared/health-indicator';
import { TextAIModelConfig, PromptTemplate, ABTest } from '../../types';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface TextAIConfigProps {
  onChangeDetected?: () => void;
}

export function TextAIConfig({ onChangeDetected }: TextAIConfigProps) {
  const [aiStatus, setAiStatus] = useState({
    connected: true,
    provider: 'openai',
    model: 'gpt-4',
    available: true
  });
  const [prompts, setPrompts] = useState<PromptTemplate[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptTemplate | null>(null);
  const [isPromptDialogOpen, setIsPromptDialogOpen] = useState(false);
  const [isTestDialogOpen, setIsTestDialogOpen] = useState(false);
  const [testResults, setTestResults] = useState<any>(null);
  const [abTests, setAbTests] = useState<ABTest[]>([]);

  const { register, handleSubmit, watch, setValue } = useForm<TextAIModelConfig>({
    defaultValues: {
      provider: 'openai',
      model: 'gpt-4',
      api_key: '',
      temperature: 0.3,
      max_tokens: 2000,
      timeout_seconds: 30,
      custom_parameters: {}
    }
  });

  const temperature = watch('temperature');

  // Load prompts
  React.useEffect(() => {
    loadPrompts();
    loadABTests();
  }, []);

  const loadPrompts = async () => {
    // TODO: Load from API
    setPrompts([
      {
        id: 'prompt_001',
        name: 'Query Understanding',
        type: 'query_understanding',
        version: '1.0.0',
        template: `Analyze the following query and extract:
1. User intent
2. Technology domain
3. Key entities

Query: "{query}"

Return as JSON with fields: intent, domain, entities`,
        variables: ['query'],
        active: true,
        performance_metrics: {
          avg_latency_ms: 450,
          success_rate: 0.98
        },
        last_updated: new Date().toISOString()
      },
      {
        id: 'prompt_002',
        name: 'Result Relevance Evaluation',
        type: 'result_relevance',
        version: '1.0.0',
        template: `Evaluate the relevance of these search results for the query.

Query: "{query}"
Results: {results_json}

Score each result 0-1 and explain why.`,
        variables: ['query', 'results_json'],
        active: true,
        performance_metrics: {
          avg_latency_ms: 380,
          success_rate: 0.99
        },
        last_updated: new Date().toISOString()
      }
    ]);
  };

  const loadABTests = async () => {
    // TODO: Load from API
    setAbTests([
      {
        id: 'test_001',
        prompt_type: 'query_understanding',
        status: 'running',
        variants: [
          { id: 'control', version: '1.0.0', traffic: 50 },
          { id: 'variant_a', version: '1.1.0', traffic: 50 }
        ],
        metrics: {
          control: { success_rate: 0.98, avg_latency: 450 },
          variant_a: { success_rate: 0.99, avg_latency: 420 }
        },
        significance: 0.92,
        started_at: new Date().toISOString()
      }
    ]);
  };

  const handlePromptTest = async () => {
    if (!selectedPrompt) return;
    
    // TODO: Test prompt
    setTestResults({
      rendered_prompt: 'Analyze the following query...',
      response: {
        intent: 'information_seeking',
        domain: 'python',
        entities: ['async', 'await']
      },
      execution_time_ms: 450,
      tokens_used: 125
    });
  };

  const handleEnhancePrompt = async () => {
    if (!selectedPrompt) return;
    
    // TODO: Enhance with AI
    alert('AI enhancement would be triggered here');
  };

  return (
    <div className="p-6 space-y-6">
      <Tabs defaultValue="model" className="space-y-4">
        <TabsList>
          <TabsTrigger value="model">Model Configuration</TabsTrigger>
          <TabsTrigger value="prompts">Prompt Templates</TabsTrigger>
          <TabsTrigger value="ab-testing">A/B Testing</TabsTrigger>
        </TabsList>

        {/* Model Configuration Tab */}
        <TabsContent value="model" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>LLM Configuration</CardTitle>
              <CardDescription>
                Configure the language model for intelligent search decisions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit((data) => {
                console.log('Save model config:', data);
                onChangeDetected?.();
              })} className="space-y-4">
                <div className="flex gap-4">
                  <div className="flex-1 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="provider">Provider</Label>
                        <Select
                          value={watch('provider')}
                          onValueChange={(value) => setValue('provider', value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="openai">OpenAI</SelectItem>
                            <SelectItem value="anthropic">Anthropic</SelectItem>
                            <SelectItem value="cohere">Cohere</SelectItem>
                            <SelectItem value="custom">Custom</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div>
                        <Label htmlFor="model">Model</Label>
                        <Select
                          value={watch('model')}
                          onValueChange={(value) => setValue('model', value)}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="gpt-4">GPT-4</SelectItem>
                            <SelectItem value="gpt-3.5-turbo">GPT-3.5 Turbo</SelectItem>
                            <SelectItem value="claude-3-opus">Claude 3 Opus</SelectItem>
                            <SelectItem value="claude-3-sonnet">Claude 3 Sonnet</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div>
                      <Label htmlFor="api_key">API Key</Label>
                      <Input
                        id="api_key"
                        type="password"
                        {...register('api_key')}
                        placeholder="sk-..."
                      />
                    </div>

                    <div>
                      <Label htmlFor="temperature">
                        Temperature: {temperature}
                      </Label>
                      <Slider
                        id="temperature"
                        min={0}
                        max={1}
                        step={0.1}
                        value={[temperature]}
                        onValueChange={([value]) => setValue('temperature', value)}
                        className="mt-2"
                      />
                      <p className="text-xs text-muted-foreground mt-1">
                        Lower values make output more focused and deterministic
                      </p>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="max_tokens">Max Tokens</Label>
                        <Input
                          id="max_tokens"
                          type="number"
                          {...register('max_tokens', { valueAsNumber: true })}
                        />
                      </div>
                      
                      <div>
                        <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
                        <Input
                          id="timeout_seconds"
                          type="number"
                          {...register('timeout_seconds', { valueAsNumber: true })}
                        />
                      </div>
                    </div>
                  </div>

                  <div className="w-64">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Service Status</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <HealthIndicator 
                          status={aiStatus.connected ? 'healthy' : 'unhealthy'}
                          label={aiStatus.connected ? 'Connected' : 'Disconnected'}
                        />
                        
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Provider:</span>
                            <span className="capitalize">{aiStatus.provider}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Model:</span>
                            <span>{aiStatus.model}</span>
                          </div>
                        </div>

                        <div className="pt-2 border-t">
                          <p className="text-xs font-medium mb-1">Today's Usage</p>
                          <div className="space-y-1 text-xs">
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Requests:</span>
                              <span>1,250</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Tokens:</span>
                              <span>450k</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-muted-foreground">Cost:</span>
                              <span>$13.50</span>
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                <div className="flex justify-end">
                  <Button type="submit">Save Model Configuration</Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Prompts Tab */}
        <TabsContent value="prompts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Prompt Templates</CardTitle>
              <CardDescription>
                Manage and optimize prompts for different decision points
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {prompts.map((prompt) => (
                  <Card key={prompt.id} className="cursor-pointer hover:shadow-md transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-medium">{prompt.name}</h4>
                            <Badge variant={prompt.active ? 'default' : 'secondary'}>
                              {prompt.active ? 'Active' : 'Inactive'}
                            </Badge>
                            <Badge variant="outline">v{prompt.version}</Badge>
                          </div>
                          
                          <p className="text-sm text-muted-foreground mb-2">
                            Type: {prompt.type} • Variables: {prompt.variables.join(', ')}
                          </p>

                          {prompt.performance_metrics && (
                            <div className="flex gap-4 text-sm">
                              <span>
                                Latency: {prompt.performance_metrics.avg_latency_ms}ms
                              </span>
                              <span>
                                Success: {(prompt.performance_metrics.success_rate * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}
                        </div>

                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSelectedPrompt(prompt);
                              setIsPromptDialogOpen(true);
                            }}
                          >
                            <Code className="h-4 w-4 mr-2" />
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSelectedPrompt(prompt);
                              setIsTestDialogOpen(true);
                            }}
                          >
                            <Play className="h-4 w-4 mr-2" />
                            Test
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setSelectedPrompt(prompt);
                              handleEnhancePrompt();
                            }}
                          >
                            <Sparkles className="h-4 w-4 mr-2" />
                            Enhance
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* A/B Testing Tab */}
        <TabsContent value="ab-testing" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>A/B Tests</CardTitle>
                  <CardDescription>
                    Run experiments to optimize prompt performance
                  </CardDescription>
                </div>
                <Button>
                  <FlaskConical className="h-4 w-4 mr-2" />
                  New Test
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {abTests.map((test) => (
                  <Card key={test.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h4 className="font-medium">
                            {test.prompt_type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                          </h4>
                          <div className="flex items-center gap-2 mt-1">
                            <Badge variant={test.status === 'running' ? 'default' : 'secondary'}>
                              {test.status}
                            </Badge>
                            <span className="text-sm text-muted-foreground">
                              Started {new Date(test.started_at).toLocaleDateString()}
                            </span>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium">
                            Significance: {(test.significance * 100).toFixed(0)}%
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {test.significance >= 0.95 ? 'Conclusive' : 'Need more data'}
                          </p>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        {test.variants.map((variant) => (
                          <div key={variant.id} className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium">
                                {variant.id === 'control' ? 'Control' : 'Variant A'}
                              </span>
                              <Badge variant="outline">{variant.traffic}%</Badge>
                            </div>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Success:</span>
                                <span>
                                  {(test.metrics[variant.id].success_rate * 100).toFixed(1)}%
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-muted-foreground">Latency:</span>
                                <span>{test.metrics[variant.id].avg_latency}ms</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Prompt Edit Dialog */}
      <Dialog open={isPromptDialogOpen} onOpenChange={setIsPromptDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Edit Prompt Template</DialogTitle>
          </DialogHeader>
          {selectedPrompt && (
            <div className="space-y-4">
              <div>
                <Label>Template</Label>
                <Textarea
                  value={selectedPrompt.template}
                  onChange={(e) => {
                    // Update template
                  }}
                  rows={10}
                  className="font-mono text-sm"
                />
              </div>
              <div>
                <Label>Variables</Label>
                <p className="text-sm text-muted-foreground">
                  Available variables: {selectedPrompt.variables.join(', ')}
                </p>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsPromptDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => {
              // Save prompt
              setIsPromptDialogOpen(false);
              onChangeDetected?.();
            }}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Dialog */}
      <Dialog open={isTestDialogOpen} onOpenChange={setIsTestDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Test Prompt</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Test Input</Label>
              <Textarea
                placeholder='{"query": "python async await tutorial"}'
                rows={3}
              />
            </div>
            
            <Button onClick={handlePromptTest} className="w-full">
              <Play className="h-4 w-4 mr-2" />
              Run Test
            </Button>

            {testResults && (
              <div className="space-y-4">
                <div>
                  <Label>Rendered Prompt</Label>
                  <pre className="bg-muted p-3 rounded text-sm overflow-auto">
                    {testResults.rendered_prompt}
                  </pre>
                </div>
                
                <div>
                  <Label>Response</Label>
                  <pre className="bg-muted p-3 rounded text-sm overflow-auto">
                    {JSON.stringify(testResults.response, null, 2)}
                  </pre>
                </div>

                <div className="flex gap-4 text-sm">
                  <span>Execution Time: {testResults.execution_time_ms}ms</span>
                  <span>Tokens Used: {testResults.tokens_used}</span>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsTestDialogOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}