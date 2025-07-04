'use client';

/**
 * Import Preview Modal Component
 * Shows a preview of changes before applying imported prompts
 */

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  AlertCircle,
  Plus,
  Edit,
  Check,
  FileJson,
  Upload
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface ImportPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  preview: {
    changes: Array<{
      promptName: string;
      changeType: 'add' | 'update' | 'unchanged';
      oldValue?: string;
      newValue?: string;
    }>;
    summary: {
      total: number;
      toAdd: number;
      toUpdate: number;
      unchanged: number;
    };
  };
  isImporting?: boolean;
}

export function ImportPreviewModal({
  isOpen,
  onClose,
  onConfirm,
  preview,
  isImporting = false
}: ImportPreviewModalProps) {
  const { changes, summary } = preview;

  // Group changes by type
  const addedPrompts = changes.filter(c => c.changeType === 'add');
  const updatedPrompts = changes.filter(c => c.changeType === 'update');
  const unchangedPrompts = changes.filter(c => c.changeType === 'unchanged');

  const hasChanges = summary.toAdd > 0 || summary.toUpdate > 0;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileJson className="h-5 w-5" />
            Import Preview
          </DialogTitle>
          <DialogDescription>
            Review the changes that will be applied to your system prompts
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Summary */}
          <div className="grid grid-cols-4 gap-3">
            <div className="flex flex-col items-center p-3 bg-muted rounded-lg">
              <span className="text-2xl font-bold">{summary.total}</span>
              <span className="text-sm text-muted-foreground">Total Prompts</span>
            </div>
            <div className="flex flex-col items-center p-3 bg-green-50 dark:bg-green-950/20 rounded-lg">
              <span className="text-2xl font-bold text-green-600 dark:text-green-400">{summary.toAdd}</span>
              <span className="text-sm text-muted-foreground">To Add</span>
            </div>
            <div className="flex flex-col items-center p-3 bg-blue-50 dark:bg-blue-950/20 rounded-lg">
              <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">{summary.toUpdate}</span>
              <span className="text-sm text-muted-foreground">To Update</span>
            </div>
            <div className="flex flex-col items-center p-3 bg-muted rounded-lg">
              <span className="text-2xl font-bold text-muted-foreground">{summary.unchanged}</span>
              <span className="text-sm text-muted-foreground">Unchanged</span>
            </div>
          </div>

          {!hasChanges && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                No changes will be applied. All imported prompts are identical to existing ones.
              </AlertDescription>
            </Alert>
          )}

          {hasChanges && (
            <Tabs defaultValue={summary.toAdd > 0 ? 'add' : 'update'} className="w-full">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="add" disabled={addedPrompts.length === 0}>
                  <Plus className="h-4 w-4 mr-2" />
                  New ({addedPrompts.length})
                </TabsTrigger>
                <TabsTrigger value="update" disabled={updatedPrompts.length === 0}>
                  <Edit className="h-4 w-4 mr-2" />
                  Updates ({updatedPrompts.length})
                </TabsTrigger>
                <TabsTrigger value="unchanged" disabled={unchangedPrompts.length === 0}>
                  <Check className="h-4 w-4 mr-2" />
                  Unchanged ({unchangedPrompts.length})
                </TabsTrigger>
              </TabsList>

              <TabsContent value="add" className="mt-4">
                <ScrollArea className="h-[300px] rounded-md border p-4">
                  <div className="space-y-4">
                    {addedPrompts.map((change, index) => (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="default" className="bg-green-600">New</Badge>
                          <span className="font-medium">{change.promptName}</span>
                        </div>
                        {change.newValue && (
                          <pre className="text-sm bg-muted p-3 rounded-md overflow-x-auto">
                            {change.newValue}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="update" className="mt-4">
                <ScrollArea className="h-[300px] rounded-md border p-4">
                  <div className="space-y-4">
                    {updatedPrompts.map((change, index) => (
                      <div key={index} className="space-y-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="default" className="bg-blue-600">Update</Badge>
                          <span className="font-medium">{change.promptName}</span>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <span className="text-sm text-muted-foreground">Current:</span>
                            <pre className="text-sm bg-red-50 dark:bg-red-950/20 p-3 rounded-md mt-1 overflow-x-auto">
                              {change.oldValue}
                            </pre>
                          </div>
                          <div>
                            <span className="text-sm text-muted-foreground">New:</span>
                            <pre className="text-sm bg-green-50 dark:bg-green-950/20 p-3 rounded-md mt-1 overflow-x-auto">
                              {change.newValue}
                            </pre>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>

              <TabsContent value="unchanged" className="mt-4">
                <ScrollArea className="h-[300px] rounded-md border p-4">
                  <div className="space-y-2">
                    {unchangedPrompts.map((change, index) => (
                      <div key={index} className="flex items-center gap-2 p-2 rounded-md hover:bg-muted">
                        <Check className="h-4 w-4 text-green-600" />
                        <span className="text-sm">{change.promptName}</span>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </TabsContent>
            </Tabs>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={onClose}
            disabled={isImporting}
          >
            Cancel
          </Button>
          <Button
            onClick={onConfirm}
            disabled={!hasChanges || isImporting}
          >
            {isImporting ? (
              <>
                <Upload className="h-4 w-4 mr-2 animate-bounce" />
                Importing...
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                Apply Changes
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}