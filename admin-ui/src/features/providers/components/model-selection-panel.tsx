'use client'

import React from 'react'
import { ModelSelectionPanelProps } from '../types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { PlusCircle } from 'lucide-react'

/**
 * ModelSelectionPanel - Interface for selecting models for text generation and embeddings
 * 
 * Allows users to choose models from tested providers, add custom models,
 * and optionally use the same provider for both text and embeddings.
 */
export function ModelSelectionPanel({
  providers,
  availableModels,
  modelSelection,
  onModelSelectionChange,
  onAddCustomModel,
  onRemoveCustomModel,
  onSaveModelSelection
}: ModelSelectionPanelProps) {
  // TODO: Filter providers that have been tested and have models available
  const testedProviders = providers.filter(p => p.status === 'configured')
  
  // TODO: Handle shared provider toggle
  const handleSharedProviderToggle = (checked: boolean) => {
    // Implementation pending
  }
  
  // TODO: Handle model selection changes
  const handleModelChange = (type: 'textGeneration' | 'embeddings', provider: string, model: string) => {
    // Implementation pending
  }
  
  // TODO: Handle custom model addition
  const handleAddCustomModel = (providerId: string) => {
    // Implementation pending - will show modal/dialog
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Model Selection</CardTitle>
        <CardDescription>
          Choose models for text generation and embeddings from your configured providers
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Use same provider toggle */}
        <div className="flex items-center space-x-2">
          <Switch 
            id="shared-provider"
            checked={modelSelection.useSharedProvider}
            onCheckedChange={handleSharedProviderToggle}
          />
          <Label htmlFor="shared-provider">Use the same provider for both text and embeddings</Label>
        </div>
        
        {/* Text Generation Model Selection */}
        <div className="space-y-2">
          <Label>Text Generation Model</Label>
          <div className="flex gap-2">
            {/* TODO: Provider selector */}
            <Select>
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                {/* TODO: Render tested providers */}
              </SelectContent>
            </Select>
            
            {/* TODO: Model selector */}
            <Select>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="Select model" />
              </SelectTrigger>
              <SelectContent>
                {/* TODO: Render available models */}
              </SelectContent>
            </Select>
            
            {/* Add custom model button */}
            <Button variant="outline" size="icon">
              <PlusCircle className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        {/* Embeddings Model Selection */}
        {!modelSelection.useSharedProvider && (
          <div className="space-y-2">
            <Label>Embeddings Model</Label>
            {/* TODO: Similar structure as text generation */}
          </div>
        )}
        
        {/* Save button */}
        <Button onClick={onSaveModelSelection} className="w-full">
          Save Model Configuration
        </Button>
      </CardContent>
    </Card>
  )
}