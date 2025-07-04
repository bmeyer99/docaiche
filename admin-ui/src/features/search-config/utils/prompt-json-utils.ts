/**
 * Utility functions for JSON validation, formatting, and processing for system prompts
 */

import { SystemPrompt } from '../components/system-prompts-manager';

/**
 * JSON export format for system prompts
 */
export interface SystemPromptsExport {
  version: string;
  timestamp: string;
  metadata: {
    exportedBy?: string;
    description?: string;
    totalPrompts: number;
  };
  prompts: SystemPromptExport[];
}

export interface SystemPromptExport {
  id: string;
  name: string;
  description: string;
  category: 'search' | 'refinement' | 'evaluation' | 'enhancement' | 'system';
  template: string;
  variables: string[];
  version: string;
  active: boolean;
  lastModified: string;
  metadata?: {
    author?: string;
    tags?: string[];
    usage_count?: number;
    performance_score?: number;
  };
}

/**
 * Validate imported JSON structure
 */
export function validatePromptJSON(data: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // Check root structure
  if (!data || typeof data !== 'object') {
    errors.push('Invalid JSON structure: root must be an object');
    return { valid: false, errors };
  }

  // Check for prompts array
  if (!data.prompts || !Array.isArray(data.prompts)) {
    errors.push('Missing or invalid "prompts" array');
    return { valid: false, errors };
  }

  // Validate each prompt
  data.prompts.forEach((prompt: any, index: number) => {
    const promptErrors = validateSinglePrompt(prompt, index);
    errors.push(...promptErrors);
  });

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Validate a single prompt structure
 */
function validateSinglePrompt(prompt: any, index: number): string[] {
  const errors: string[] = [];
  const prefix = `Prompt ${index + 1}`;

  // Required fields
  if (!prompt.id || typeof prompt.id !== 'string') {
    errors.push(`${prefix}: Missing or invalid "id" field`);
  }

  if (!prompt.name || typeof prompt.name !== 'string') {
    errors.push(`${prefix}: Missing or invalid "name" field`);
  }

  if (!prompt.template || typeof prompt.template !== 'string') {
    errors.push(`${prefix}: Missing or invalid "template" field`);
  }

  if (!prompt.category) {
    errors.push(`${prefix}: Missing "category" field`);
  } else if (!['search', 'refinement', 'evaluation', 'enhancement', 'system'].includes(prompt.category)) {
    errors.push(`${prefix}: Invalid category "${prompt.category}"`);
  }

  // Optional but typed fields
  if (prompt.variables && !Array.isArray(prompt.variables)) {
    errors.push(`${prefix}: "variables" must be an array`);
  }

  if (prompt.active !== undefined && typeof prompt.active !== 'boolean') {
    errors.push(`${prefix}: "active" must be a boolean`);
  }

  return errors;
}

/**
 * Format prompts for export
 */
export function formatPromptsForExport(prompts: SystemPrompt[]): SystemPromptsExport {
  return {
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    metadata: {
      totalPrompts: prompts.length,
      description: 'System prompts export from Docaiche admin'
    },
    prompts: prompts.map(formatSinglePromptForExport)
  };
}

/**
 * Format a single prompt for export
 */
function formatSinglePromptForExport(prompt: SystemPrompt): SystemPromptExport {
  return {
    id: prompt.id,
    name: prompt.name,
    description: prompt.description,
    category: prompt.category,
    template: prompt.template,
    variables: prompt.variables,
    version: prompt.version,
    active: prompt.active,
    lastModified: prompt.lastModified,
    metadata: (prompt as any).metadata || {}
  };
}

/**
 * Format a single prompt for JSON download
 */
export function formatSinglePromptJSON(prompt: SystemPrompt): string {
  const exportData = {
    version: '1.0.0',
    timestamp: new Date().toISOString(),
    prompt: formatSinglePromptForExport(prompt)
  };
  
  return JSON.stringify(exportData, null, 2);
}

/**
 * Merge imported prompts with existing prompts
 */
export function mergePrompts(
  existing: SystemPrompt[],
  imported: SystemPromptExport[]
): {
  merged: SystemPrompt[];
  added: string[];
  updated: string[];
  unchanged: string[];
} {
  const result = {
    merged: [...existing],
    added: [] as string[],
    updated: [] as string[],
    unchanged: [] as string[]
  };

  const existingMap = new Map(existing.map(p => [p.id, p]));

  imported.forEach(importedPrompt => {
    const existingPrompt = existingMap.get(importedPrompt.id);

    if (!existingPrompt) {
      // New prompt
      result.merged.push({
        ...importedPrompt,
        type: importedPrompt.description, // Use description as type fallback
        lastModified: new Date().toISOString()
      } as SystemPrompt);
      result.added.push(importedPrompt.name);
    } else {
      // Check if content changed
      if (existingPrompt.template !== importedPrompt.template ||
          JSON.stringify(existingPrompt.variables) !== JSON.stringify(importedPrompt.variables)) {
        // Update existing prompt
        const index = result.merged.findIndex(p => p.id === importedPrompt.id);
        if (index !== -1) {
          result.merged[index] = {
            ...existingPrompt,
            ...importedPrompt,
            type: existingPrompt.type || importedPrompt.description, // Preserve type field
            lastModified: new Date().toISOString()
          } as SystemPrompt;
        }
        result.updated.push(importedPrompt.name);
      } else {
        result.unchanged.push(importedPrompt.name);
      }
    }
  });

  return result;
}

/**
 * Create a preview of changes that will be applied
 */
export function createImportPreview(
  existing: SystemPrompt[],
  imported: SystemPromptExport[]
): {
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
} {
  const changes: Array<{
    promptName: string;
    changeType: 'add' | 'update' | 'unchanged';
    oldValue?: string;
    newValue?: string;
  }> = [];

  const existingMap = new Map(existing.map(p => [p.id, p]));
  let toAdd = 0;
  let toUpdate = 0;
  let unchanged = 0;

  imported.forEach(importedPrompt => {
    const existingPrompt = existingMap.get(importedPrompt.id);

    if (!existingPrompt) {
      changes.push({
        promptName: importedPrompt.name,
        changeType: 'add',
        newValue: importedPrompt.template
      });
      toAdd++;
    } else if (existingPrompt.template !== importedPrompt.template) {
      changes.push({
        promptName: importedPrompt.name,
        changeType: 'update',
        oldValue: existingPrompt.template,
        newValue: importedPrompt.template
      });
      toUpdate++;
    } else {
      changes.push({
        promptName: importedPrompt.name,
        changeType: 'unchanged'
      });
      unchanged++;
    }
  });

  return {
    changes,
    summary: {
      total: imported.length,
      toAdd,
      toUpdate,
      unchanged
    }
  };
}

/**
 * Download JSON file
 */
export function downloadJSON(data: any, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}