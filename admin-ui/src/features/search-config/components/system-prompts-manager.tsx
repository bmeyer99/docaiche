'use client';

/**
 * System Prompts Manager Component
 * 
 * Provides a unified interface for managing all 10 system prompts
 * with bulk operations and change tracking.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import {
  Save,
  Download,
  Upload,
  AlertCircle,
  CheckCircle,
  Loader2,
  Info,
  RefreshCw,
  Sparkles,
  ArrowRight,
  X
} from 'lucide-react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';
import { PromptCard } from './prompt-card';
import { PromptTemplate } from '../types';

// TypeScript interfaces for system prompts
export interface SystemPrompt {
  id: string;
  name: string;
  type: string;
  description: string;
  category: 'search' | 'refinement' | 'evaluation' | 'enhancement' | 'system';
  template: string;
  variables: string[];
  version: string;
  active: boolean;
  lastModified: string;
  performance_metrics?: {
    avg_latency_ms: number;
    success_rate: number;
  };
}

export interface SystemPromptsResponse {
  prompts: PromptTemplate[];
  total: number;
}

interface SystemPromptsManagerProps {
  onChangeDetected?: () => void;
  onSaveSuccess?: () => void;
}

// Enhancement dialog state
interface EnhancementDialogState {
  isOpen: boolean;
  promptId: string | null;
  originalPrompt: string;
  enhancedPrompt: string;
  isEnhancing: boolean;
}


// Prompt categories with descriptions - mapped from backend prompt types
const PROMPT_CATEGORIES = {
  search: {
    label: 'Search & Query Analysis',
    description: 'Understanding and processing search queries',
    color: 'bg-blue-500',
    types: ['query_understanding', 'external_search_query']
  },
  refinement: {
    label: 'Query Refinement',
    description: 'Improving and refining search queries',
    color: 'bg-purple-500',
    types: ['query_refinement']
  },
  evaluation: {
    label: 'Result Evaluation',
    description: 'Evaluating search results and quality',
    color: 'bg-green-500',
    types: ['result_relevance', 'external_search_decision']
  },
  enhancement: {
    label: 'Content Enhancement',
    description: 'Extracting and formatting content',
    color: 'bg-orange-500',
    types: ['content_extraction', 'response_format']
  },
  system: {
    label: 'System Analysis',
    description: 'System behavior and analysis prompts',
    color: 'bg-gray-500',
    types: ['learning_opportunities', 'provider_selection', 'failure_analysis']
  }
};

// Map prompt types to categories
const getPromptCategory = (promptType: string): keyof typeof PROMPT_CATEGORIES => {
  for (const [category, info] of Object.entries(PROMPT_CATEGORIES)) {
    if (info.types.includes(promptType)) {
      return category as keyof typeof PROMPT_CATEGORIES;
    }
  }
  return 'system'; // default fallback
};

export function SystemPromptsManager({ onChangeDetected, onSaveSuccess }: SystemPromptsManagerProps) {
  const [prompts, setPrompts] = useState<SystemPrompt[]>([]);
  const [modifiedPrompts, setModifiedPrompts] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [showFloatingSave, setShowFloatingSave] = useState(false);
  const [saveProgress, setSaveProgress] = useState(0);
  const [isFloatingVisible, setIsFloatingVisible] = useState(false);
  const [enhancementDialog, setEnhancementDialog] = useState<EnhancementDialogState>({
    isOpen: false,
    promptId: null,
    originalPrompt: '',
    enhancedPrompt: '',
    isEnhancing: false
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const floatingButtonRef = useRef<HTMLDivElement>(null);
  
  const apiClient = useApiClient();
  const { toast } = useToast();

  // Load all system prompts on mount
  useEffect(() => {
    loadSystemPrompts();
  }, []);

  // Add keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl+S or Cmd+S to save
      if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        if (modifiedPrompts.size > 0 && !isSaving) {
          handleSaveAll();
        }
      }
      // Escape to cancel floating save
      if (event.key === 'Escape' && showFloatingSave) {
        setShowFloatingSave(false);
        setIsFloatingVisible(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [modifiedPrompts.size, isSaving, showFloatingSave]);

  // Prevent accidental navigation away with unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (modifiedPrompts.size > 0) {
        event.preventDefault();
        event.returnValue = '';
        return '';
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [modifiedPrompts.size]);

  // Track scroll position for floating save button
  useEffect(() => {
    let scrollTimeout: NodeJS.Timeout;
    
    const handleScroll = () => {
      if (scrollContainerRef.current) {
        const scrollTop = scrollContainerRef.current.scrollTop;
        const shouldShow = scrollTop > 100 && modifiedPrompts.size > 0;
        
        if (shouldShow !== showFloatingSave) {
          setShowFloatingSave(shouldShow);
          
          // Add smooth transition effect
          if (shouldShow) {
            // Delay visibility to allow for mounting animation
            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
              setIsFloatingVisible(true);
            }, 50);
          } else {
            setIsFloatingVisible(false);
          }
        }
      }
    };

    const container = scrollContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll, { passive: true });
      return () => {
        container.removeEventListener('scroll', handleScroll);
        clearTimeout(scrollTimeout);
      };
    }
  }, [modifiedPrompts.size, showFloatingSave]);

  const loadSystemPrompts = async () => {
    try {
      setIsLoading(true);
      // Fetch all 10 system prompts from the API
      const response = await apiClient.get<SystemPromptsResponse>('/admin/search/text-ai/prompts');
      
      if (response.prompts && response.prompts.length > 0) {
        // Map the backend prompts to our frontend format
        const mappedPrompts = response.prompts.map(prompt => {
          // Generate description based on prompt type
          const descriptions: Record<string, string> = {
            'query_understanding': 'Analyze and understand search queries to identify intent and key concepts',
            'result_relevance': 'Evaluate the relevance of search results against the original query',
            'query_refinement': 'Refine and improve search queries for better results',
            'external_search_decision': 'Decide whether to perform external search based on results',
            'external_search_query': 'Generate optimized queries for external search providers',
            'content_extraction': 'Extract relevant content from documentation and sources',
            'response_format': 'Format search results based on user preferences',
            'learning_opportunities': 'Identify knowledge gaps and learning opportunities',
            'provider_selection': 'Select the optimal search provider for queries',
            'failure_analysis': 'Analyze failed searches to improve future performance'
          };
          
          return {
            ...prompt,
            category: getPromptCategory(prompt.type),
            description: descriptions[prompt.type] || `${prompt.name} prompt template`,
            lastModified: (prompt as any).last_updated || new Date().toISOString()
          };
        });
        setPrompts(mappedPrompts);
      } else {
        // If no prompts exist, the backend should have initialized defaults
        toast({
          title: 'No prompts found',
          description: 'Loading default prompt templates.',
          variant: 'default'
        });
        // Try loading again after a short delay
        setTimeout(() => loadSystemPrompts(), 1000);
      }
    } catch (error) {
      console.error('Failed to load system prompts:', error);
      toast({
        title: 'Failed to load prompts',
        description: 'Please check your connection and try again.',
        variant: 'destructive'
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Helper function to extract variables from template text
  const extractVariables = (template: string): string[] => {
    const matches = template.match(/\{(\w+)\}/g) || [];
    return [...new Set(matches.map(match => match.slice(1, -1)))];
  };

  const handlePromptChange = (promptId: string, newTemplate: string) => {
    setPrompts(prev => prev.map(prompt => 
      prompt.id === promptId 
        ? { 
            ...prompt, 
            template: newTemplate, 
            lastModified: new Date().toISOString(),
            variables: extractVariables(newTemplate)
          }
        : prompt
    ));
    
    setModifiedPrompts(prev => new Set(prev).add(promptId));
    onChangeDetected?.();
  };
  
  const handlePromptEnhance = async (promptId: string) => {
    // Find the prompt to enhance
    const prompt = prompts.find(p => p.id === promptId);
    if (!prompt) return;

    // Open dialog and start enhancing
    setEnhancementDialog({
      isOpen: true,
      promptId,
      originalPrompt: prompt.template,
      enhancedPrompt: '',
      isEnhancing: true
    });

    try {
      // Call the enhancement API
      const response = await apiClient.post(`/admin/search/text-ai/prompts/${prompt.type}/enhance`, {
        optimization_goals: ['clarity', 'accuracy', 'efficiency']
      });
      
      if (response && (response as any).enhanced_template) {
        // Update dialog with enhanced version
        setEnhancementDialog(prev => ({
          ...prev,
          enhancedPrompt: (response as any).enhanced_template,
          isEnhancing: false
        }));
      } else {
        throw new Error('No enhanced template returned');
      }
    } catch (error: any) {
      console.error('Enhancement failed:', error);
      toast({
        title: 'Enhancement failed',
        description: error.message || 'Could not enhance the prompt at this time',
        variant: 'destructive'
      });
      
      // Close dialog on error
      setEnhancementDialog({
        isOpen: false,
        promptId: null,
        originalPrompt: '',
        enhancedPrompt: '',
        isEnhancing: false
      });
    }
  };

  const handleAcceptEnhancement = () => {
    if (!enhancementDialog.promptId || !enhancementDialog.enhancedPrompt) return;

    // Apply the enhanced prompt
    handlePromptChange(enhancementDialog.promptId, enhancementDialog.enhancedPrompt);

    toast({
      title: 'Enhancement applied',
      description: 'The prompt has been updated with AI improvements'
    });

    // Close dialog
    setEnhancementDialog({
      isOpen: false,
      promptId: null,
      originalPrompt: '',
      enhancedPrompt: '',
      isEnhancing: false
    });
  };

  const handleRejectEnhancement = () => {
    // Simply close the dialog without applying changes
    setEnhancementDialog({
      isOpen: false,
      promptId: null,
      originalPrompt: '',
      enhancedPrompt: '',
      isEnhancing: false
    });
  };


  const handleSaveAll = async () => {
    if (modifiedPrompts.size === 0) return;

    setIsSaving(true);
    setSaveProgress(0);
    
    try {
      // Get only modified prompts
      const promptsToSave = prompts.filter(p => modifiedPrompts.has(p.id));
      const totalPrompts = promptsToSave.length;
      let savedCount = 0;
      
      // Save each modified prompt individually to the backend with progress tracking
      const savePromises = promptsToSave.map(async (prompt, index) => {
        const updateRequest = {
          template: prompt.template,
          active: prompt.active,
          notes: `Updated via admin UI at ${new Date().toISOString()}`,
          performance_metrics: prompt.performance_metrics
        };
        
        try {
          const result = await apiClient.put(`/admin/search/text-ai/prompts/${prompt.type}`, updateRequest);
          savedCount++;
          setSaveProgress((savedCount / totalPrompts) * 100);
          return result;
        } catch (error) {
          console.error(`Failed to save prompt ${prompt.type}:`, error);
          throw error;
        }
      });
      
      await Promise.all(savePromises);
      
      setModifiedPrompts(new Set());
      setSaveProgress(100);
      onSaveSuccess?.();
      
      toast({
        title: 'Prompts saved successfully',
        description: `Updated ${promptsToSave.length} system prompt${promptsToSave.length > 1 ? 's' : ''}`,
        duration: 3000
      });
      
      // Reload prompts to get updated versions
      await loadSystemPrompts();
    } catch (error: any) {
      toast({
        title: 'Failed to save prompts',
        description: error.message || 'Please try again',
        variant: 'destructive'
      });
    } finally {
      setIsSaving(false);
      setSaveProgress(0);
    }
  };

  const handleDownloadAll = () => {
    const exportData = {
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      prompts: prompts
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `system-prompts-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast({
      title: 'Prompts exported',
      description: 'System prompts have been downloaded as JSON'
    });
  };

  const handleUploadJSON = () => {
    fileInputRef.current?.click();
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);
      
      if (!data.prompts || !Array.isArray(data.prompts)) {
        throw new Error('Invalid file format');
      }

      // Validate prompts structure
      const validPrompts = data.prompts.filter((p: any) => 
        p.id && p.name && p.template && p.category
      );

      if (validPrompts.length === 0) {
        throw new Error('No valid prompts found in file');
      }

      setPrompts(validPrompts);
      setModifiedPrompts(new Set(validPrompts.map((p: SystemPrompt) => p.id)));
      onChangeDetected?.();

      toast({
        title: 'Prompts imported',
        description: `Loaded ${validPrompts.length} prompts from file`
      });
    } catch (error) {
      toast({
        title: 'Import failed',
        description: 'Please check the file format and try again',
        variant: 'destructive'
      });
    }

    // Reset file input
    if (event.target) {
      event.target.value = '';
    }
  };

  const handleCancelAllChanges = () => {
    if (modifiedPrompts.size === 0) return;
    
    // Show confirmation dialog
    if (window.confirm(`Are you sure you want to discard ${modifiedPrompts.size} unsaved change${modifiedPrompts.size > 1 ? 's' : ''}?`)) {
      setModifiedPrompts(new Set());
      loadSystemPrompts(); // Reload to get original values
      
      toast({
        title: 'Changes discarded',
        description: 'All unsaved changes have been discarded'
      });
    }
  };

  const handleResetPrompt = async (promptId: string) => {
    try {
      // Find the prompt to reset
      const prompt = prompts.find(p => p.id === promptId);
      if (!prompt) return;
      
      // Get the default version from the backend
      const response = await apiClient.get<any[]>(`/admin/search/text-ai/prompts/${prompt.type}/versions`);
      
      if (response && response.length > 0) {
        // Find the initial version (usually the last in the list)
        const initialVersion = response[response.length - 1];
        
        // Update the prompt with the initial version content
        // Note: We'll need to fetch the full prompt data for this version
        const defaultPromptResponse = await apiClient.get<PromptTemplate>(
          `/admin/search/text-ai/prompts/${prompt.type}?version=${initialVersion.version}`
        );
        
        if (defaultPromptResponse) {
          setPrompts(prev => prev.map(p => 
            p.id === promptId 
              ? {
                  ...p,
                  template: defaultPromptResponse.template,
                  variables: defaultPromptResponse.variables,
                  version: defaultPromptResponse.version
                }
              : p
          ));
          
          setModifiedPrompts(prev => {
            const newSet = new Set(prev);
            newSet.add(promptId);
            return newSet;
          });

          toast({
            title: 'Prompt reset',
            description: 'Restored to initial template version'
          });
        }
      }
    } catch (error) {
      toast({
        title: 'Failed to reset prompt',
        description: 'Could not load default template',
        variant: 'destructive'
      });
    }
  };

  // Convert SystemPrompt to PromptTemplate for PromptCard
  const toPromptTemplate = (prompt: SystemPrompt): PromptTemplate => ({
    id: prompt.id,
    name: prompt.name,
    type: prompt.type,
    version: prompt.version,
    template: prompt.template,
    variables: prompt.variables,
    active: prompt.active,
    performance_metrics: prompt.performance_metrics,
    last_updated: prompt.lastModified
  });

  // Group prompts by category
  const promptsByCategory = prompts.reduce((acc, prompt) => {
    if (!acc[prompt.category]) {
      acc[prompt.category] = [];
    }
    acc[prompt.category].push(prompt);
    return acc;
  }, {} as Record<string, SystemPrompt[]>);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="text-muted-foreground">Loading system prompts...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative h-full">
      {/* Header */}
      <div className="p-6 border-b">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">System Prompts Manager</h2>
            <p className="text-muted-foreground mt-1">
              Manage all 10 system prompts used throughout the application
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Badge variant={modifiedPrompts.size > 0 ? 'default' : 'secondary'}>
              {modifiedPrompts.size} modified
            </Badge>
            <Button
              variant="outline"
              size="sm"
              onClick={loadSystemPrompts}
              disabled={isLoading}
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="p-6 border-b bg-muted/30">
        <div className="flex items-center justify-between">
          <Alert className="flex-1 mr-4">
            <Info className="h-4 w-4" />
            <AlertDescription>
              System prompts define how the AI interprets and responds to different aspects of search functionality.
              Each prompt can include variables in {'{curly braces}'} that will be replaced with actual values.
            </AlertDescription>
          </Alert>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={handleDownloadAll}
            >
              <Download className="h-4 w-4 mr-2" />
              Download All
            </Button>
            <Button
              variant="outline"
              onClick={handleUploadJSON}
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload JSON
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              className="hidden"
            />
          </div>
        </div>
      </div>

      {/* Scrollable content area */}
      <ScrollArea ref={scrollContainerRef} className="h-[calc(100%-13rem)]">
        <div className="p-6 space-y-8">
          {Object.entries(promptsByCategory).map(([category, categoryPrompts]) => {
            const categoryInfo = PROMPT_CATEGORIES[category as keyof typeof PROMPT_CATEGORIES];
            
            return (
              <div key={category} className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className={cn('w-2 h-8 rounded-full', categoryInfo.color)} />
                  <div>
                    <h3 className="text-lg font-semibold">{categoryInfo.label}</h3>
                    <p className="text-sm text-muted-foreground">{categoryInfo.description}</p>
                  </div>
                </div>

                <div className="grid gap-4">
                  {categoryPrompts.map((prompt) => {
                    // Find if we have a default/original version for this prompt
                    const defaultPrompt = prompts.find(p => 
                      p.type === prompt.type && p.version === '1.0.0'
                    );
                    
                    return (
                      <div
                        key={prompt.id}
                        className={cn(
                          'transition-all rounded-lg',
                          modifiedPrompts.has(prompt.id) && 'ring-2 ring-primary ring-offset-2'
                        )}
                      >
                        <PromptCard
                          prompt={toPromptTemplate(prompt)}
                          defaultPrompt={defaultPrompt ? toPromptTemplate(defaultPrompt) : undefined}
                          onChange={handlePromptChange}
                          onEnhance={handlePromptEnhance}
                          onReset={handleResetPrompt}
                          readOnly={false}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      </ScrollArea>

      {/* Enhanced Floating save button */}
      {showFloatingSave && (
        <div
          ref={floatingButtonRef}
          className={cn(
            "fixed top-20 left-1/2 -translate-x-1/2 z-50 transition-all duration-300 ease-in-out",
            "max-w-[95vw] sm:max-w-[90vw] md:max-w-[600px]",
            isFloatingVisible ? "translate-y-0 opacity-100 floating-save-enter" : "-translate-y-full opacity-0 floating-save-exit",
            modifiedPrompts.size > 0 && "floating-save-glow"
          )}
        >
          <div className="bg-background/95 backdrop-blur-custom border rounded-lg shadow-floating-lg p-3 sm:p-4">
            <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-4">
              {/* Modified count indicator */}
              <div className="flex items-center gap-2">
                <div className="relative">
                  <div className="absolute inset-0 bg-primary/20 blur-lg rounded-full animate-pulse" />
                  <Badge 
                    variant="default" 
                    className="relative bg-primary text-primary-foreground font-bold"
                  >
                    {modifiedPrompts.size}
                  </Badge>
                </div>
                <span className="text-sm font-medium">
                  unsaved prompt{modifiedPrompts.size > 1 ? 's' : ''}
                </span>
              </div>

              {/* Progress indicator during save */}
              {isSaving && saveProgress > 0 && (
                <div className="w-full sm:w-32 h-2 bg-muted rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-primary progress-bar transition-all duration-300"
                    style={{ 
                      width: `${saveProgress}%`,
                      '--progress-width': `${saveProgress}%`
                    } as React.CSSProperties & { '--progress-width': string }}
                  />
                </div>
              )}

              {/* Action buttons */}
              <div className="flex items-center gap-2 w-full sm:w-auto justify-center sm:justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCancelAllChanges}
                  disabled={isSaving}
                  className="hover:bg-destructive/10 hover:text-destructive flex-1 sm:flex-none"
                >
                  <X className="h-4 w-4 mr-2 sm:mr-1" />
                  <span className="hidden sm:inline">Cancel</span>
                </Button>
                <Button
                  size="sm"
                  onClick={handleSaveAll}
                  disabled={isSaving || modifiedPrompts.size === 0}
                  className="min-w-[100px] flex-1 sm:flex-none"
                  title="Save all changes (Ctrl+S)"
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      <span className="hidden sm:inline">
                        {saveProgress > 0 ? `${Math.round(saveProgress)}%` : 'Saving...'}
                      </span>
                      <span className="sm:hidden">
                        {saveProgress > 0 ? `${Math.round(saveProgress)}%` : 'Saving'}
                      </span>
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      <span className="hidden sm:inline">Save All</span>
                      <span className="sm:hidden">Save</span>
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Fixed save button at bottom - enhanced */}
      <div className="absolute bottom-0 left-0 right-0 border-t bg-background/95 backdrop-blur-sm p-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-0">
          <div className="text-sm text-muted-foreground">
            {modifiedPrompts.size > 0 ? (
              <span className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 text-amber-500" />
                You have unsaved changes to {modifiedPrompts.size} prompt{modifiedPrompts.size > 1 ? 's' : ''}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-500" />
                All prompts are up to date
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2 w-full sm:w-auto">
            {modifiedPrompts.size > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCancelAllChanges}
                disabled={isSaving}
                className="hover:bg-destructive/10 hover:text-destructive flex-1 sm:flex-none"
              >
                <X className="h-4 w-4 mr-2" />
                Cancel All
              </Button>
            )}
            <Button
              onClick={handleSaveAll}
              disabled={isSaving || modifiedPrompts.size === 0}
              className="flex-1 sm:flex-none"
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  {saveProgress > 0 ? `Saving... ${Math.round(saveProgress)}%` : 'Saving...'}
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save All Changes
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Enhancement Confirmation Dialog */}
      <Dialog 
        open={enhancementDialog.isOpen} 
        onOpenChange={(open) => {
          if (!open && !enhancementDialog.isEnhancing) {
            handleRejectEnhancement();
          }
        }}
      >
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle>
              {enhancementDialog.isEnhancing ? 'Enhancing Prompt...' : 'Review Enhanced Prompt'}
            </DialogTitle>
            <DialogDescription>
              {enhancementDialog.isEnhancing 
                ? 'AI is analyzing and improving your prompt for better clarity, accuracy, and efficiency.'
                : 'Review the AI-enhanced version of your prompt. You can accept the improvements or keep the original.'
              }
            </DialogDescription>
          </DialogHeader>

          {enhancementDialog.isEnhancing ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center space-y-4">
                <Sparkles className="h-12 w-12 mx-auto text-primary animate-pulse" />
                <Loader2 className="h-8 w-8 mx-auto animate-spin" />
                <p className="text-muted-foreground">Analyzing prompt structure and optimizing...</p>
              </div>
            </div>
          ) : (
            <div className="space-y-4 overflow-y-auto max-h-[50vh]">
              {/* Original Prompt */}
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-muted-foreground">Original Prompt</h4>
                <div className="relative">
                  <Textarea
                    value={enhancementDialog.originalPrompt}
                    readOnly
                    className="min-h-[150px] font-mono text-sm bg-muted/50"
                  />
                </div>
              </div>

              {/* Arrow indicator */}
              <div className="flex justify-center">
                <ArrowRight className="h-6 w-6 text-muted-foreground" />
              </div>

              {/* Enhanced Prompt */}
              <div className="space-y-2">
                <h4 className="text-sm font-medium flex items-center gap-2">
                  Enhanced Prompt
                  <Badge variant="default" className="text-xs">
                    <Sparkles className="h-3 w-3 mr-1" />
                    AI Enhanced
                  </Badge>
                </h4>
                <div className="relative">
                  <Textarea
                    value={enhancementDialog.enhancedPrompt}
                    readOnly
                    className="min-h-[150px] font-mono text-sm bg-primary/5 border-primary/20"
                  />
                </div>
              </div>

              {/* Enhancement summary */}
              {enhancementDialog.enhancedPrompt && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    The AI has optimized this prompt for clarity, accuracy, and efficiency. 
                    Key improvements may include better variable usage, clearer instructions, 
                    and more structured output formatting.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {!enhancementDialog.isEnhancing && (
            <DialogFooter>
              <Button
                variant="outline"
                onClick={handleRejectEnhancement}
              >
                Keep Original
              </Button>
              <Button
                onClick={handleAcceptEnhancement}
                disabled={!enhancementDialog.enhancedPrompt}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Accept Enhancement
              </Button>
            </DialogFooter>
          )}
        </DialogContent>
      </Dialog>

    </div>
  );
}