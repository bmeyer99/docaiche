'use client';

/**
 * PromptCard component for displaying and editing individual prompts
 * Provides expandable/collapsible UI with download, enhance, and reset functionality
 */

import React, { useState, useMemo } from 'react';
import { 
  Card, 
  CardHeader, 
  CardTitle, 
  CardDescription, 
  CardContent,
  CardFooter 
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { 
  Collapsible, 
  CollapsibleContent, 
  CollapsibleTrigger 
} from '@/components/ui/collapsible';
import { 
  ChevronDown, 
  ChevronUp, 
  Download, 
  Sparkles, 
  RotateCcw,
  Variable,
  Thermometer,
  FileJson,
  Edit,
  Check,
  X
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { PromptTemplate } from '../types';
import { downloadJSON } from '../utils/prompt-json-utils';

interface PromptCardProps {
  /**
   * The prompt template data
   */
  prompt: PromptTemplate;
  
  /**
   * Default prompt template for reset functionality
   */
  defaultPrompt?: PromptTemplate;
  
  /**
   * Callback when prompt content changes
   */
  onChange?: (promptId: string, newContent: string) => void;
  
  /**
   * Callback when enhance button is clicked
   */
  onEnhance?: (promptId: string) => void;
  
  /**
   * Callback when reset button is clicked
   */
  onReset?: (promptId: string) => void;
  
  /**
   * Whether the card is in read-only mode
   */
  readOnly?: boolean;
  
  /**
   * Custom class name for the card
   */
  className?: string;
}

export function PromptCard({
  prompt,
  defaultPrompt,
  onChange,
  onEnhance,
  onReset,
  readOnly = false,
  className
}: PromptCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(prompt.template);

  // Check if prompt has been modified from default
  const isModified = useMemo(() => {
    if (!defaultPrompt) return false;
    return prompt.template !== defaultPrompt.template;
  }, [prompt.template, defaultPrompt]);

  // Extract metadata for display
  const metadata = {
    variables: prompt.variables || [],
    temperature: prompt.performance_metrics?.avg_latency_ms 
      ? `${(prompt.performance_metrics.avg_latency_ms / 1000).toFixed(1)}s avg` 
      : 'N/A',
    outputFormat: 'JSON' // This could be extracted from prompt content analysis
  };

  const handleDownload = () => {
    const exportData = {
      version: '1.0.0',
      timestamp: new Date().toISOString(),
      prompt: {
        id: prompt.id,
        name: prompt.name,
        type: prompt.type,
        template: prompt.template,
        variables: prompt.variables,
        version: prompt.version,
        active: prompt.active,
        last_updated: prompt.last_updated,
        performance_metrics: prompt.performance_metrics
      }
    };
    const filename = `${prompt.id}-${new Date().toISOString().split('T')[0]}.json`;
    downloadJSON(exportData, filename);
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedContent(prompt.template);
  };

  const handleSave = () => {
    if (onChange && editedContent !== prompt.template) {
      onChange(prompt.id, editedContent);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditedContent(prompt.template);
    setIsEditing(false);
  };

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditedContent(e.target.value);
  };

  return (
    <Card className={cn('relative overflow-hidden', className)}>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 space-y-1">
            <CardTitle className="flex items-center gap-2">
              {prompt.name}
              {isModified && (
                <Badge variant="outline" className="text-xs">
                  Modified
                </Badge>
              )}
              {prompt.active && (
                <Badge variant="default" className="text-xs">
                  Active
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              {prompt.type} • Version {prompt.version}
            </CardDescription>
          </div>
          
          {/* Expand/Collapse Toggle */}
          <CollapsibleTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
              className="h-8 w-8 p-0"
            >
              {isExpanded ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
            </Button>
          </CollapsibleTrigger>
        </div>

        {/* Metadata badges */}
        <div className="flex flex-wrap gap-2 mt-3">
          {metadata.variables.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              <Variable className="h-3 w-3 mr-1" />
              {metadata.variables.length} variable{metadata.variables.length > 1 ? 's' : ''}
            </Badge>
          )}
          <Badge variant="secondary" className="text-xs">
            <Thermometer className="h-3 w-3 mr-1" />
            {metadata.temperature}
          </Badge>
          <Badge variant="secondary" className="text-xs">
            <FileJson className="h-3 w-3 mr-1" />
            {metadata.outputFormat}
          </Badge>
        </div>
      </CardHeader>

      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleContent>
          <CardContent className="space-y-4">
            {/* Variables list */}
            {metadata.variables.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Variables</h4>
                <div className="flex flex-wrap gap-2">
                  {metadata.variables.map((variable) => (
                    <code
                      key={variable}
                      className="px-2 py-1 bg-muted rounded text-xs font-mono"
                    >
                      {`{{${variable}}}`}
                    </code>
                  ))}
                </div>
              </div>
            )}

            {/* Prompt content */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-medium">Prompt Content</h4>
                {!readOnly && !isEditing && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleEdit}
                    className="h-8"
                  >
                    <Edit className="h-3 w-3 mr-1" />
                    Edit
                  </Button>
                )}
              </div>
              
              {isEditing ? (
                <div className="space-y-2">
                  <Textarea
                    value={editedContent}
                    onChange={handleContentChange}
                    className="min-h-[200px] font-mono text-sm"
                    placeholder="Enter prompt content..."
                  />
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      onClick={handleSave}
                      className="h-8"
                    >
                      <Check className="h-3 w-3 mr-1" />
                      Save
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleCancel}
                      className="h-8"
                    >
                      <X className="h-3 w-3 mr-1" />
                      Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="bg-muted/50 rounded-md p-4">
                  <pre className="whitespace-pre-wrap font-mono text-sm">
                    {prompt.template}
                  </pre>
                </div>
              )}
            </div>

            {/* Performance metrics if available */}
            {prompt.performance_metrics && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium">Performance</h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Average Latency:</span>
                    <span className="ml-2 font-medium">
                      {prompt.performance_metrics.avg_latency_ms}ms
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Success Rate:</span>
                    <span className="ml-2 font-medium">
                      {(prompt.performance_metrics.success_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Last updated */}
            <div className="text-xs text-muted-foreground">
              Last updated: {new Date(prompt.last_updated).toLocaleString()}
            </div>
          </CardContent>

          <CardFooter className="flex gap-2 border-t pt-4">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="h-8"
            >
              <Download className="h-3 w-3 mr-1" />
              Download
            </Button>
            
            {!readOnly && onEnhance && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEnhance(prompt.id)}
                className="h-8"
              >
                <Sparkles className="h-3 w-3 mr-1" />
                Enhance
              </Button>
            )}
            
            {!readOnly && onReset && defaultPrompt && isModified && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => onReset(prompt.id)}
                className="h-8"
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Reset to Default
              </Button>
            )}
          </CardFooter>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}