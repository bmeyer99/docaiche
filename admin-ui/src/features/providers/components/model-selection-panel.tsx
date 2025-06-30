'use client'

import React, { useState } from 'react'
import { ModelSelectionPanelProps, Model } from '../types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { PlusCircle, Trash2, AlertCircle } from 'lucide-react'

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
  onSaveModelSelection,
  isSaving = false
}: ModelSelectionPanelProps) {
  const [showAddModel, setShowAddModel] = useState(false)
  const [customModelName, setCustomModelName] = useState('')
  const [addModelProvider, setAddModelProvider] = useState<string>('')
  
  // Filter providers that have been tested and have models available
  const testedProviders = providers.filter(p => p.status === 'configured')
  
  // Get providers that support each capability
  const textProviders = testedProviders.filter(p => p.supportsChat)
  const embeddingProviders = testedProviders.filter(p => p.supportsEmbedding)
  
  // Handle shared provider toggle
  const handleSharedProviderToggle = (checked: boolean) => {
    if (checked && modelSelection.textGeneration.provider) {
      // When enabling shared provider, copy text generation settings to embeddings
      onModelSelectionChange({
        ...modelSelection,
        useSharedProvider: true,
        embeddings: {
          provider: modelSelection.textGeneration.provider,
          model: modelSelection.textGeneration.model
        }
      })
    } else {
      onModelSelectionChange({
        ...modelSelection,
        useSharedProvider: checked
      })
    }
  }
  
  // Handle provider selection
  const handleProviderChange = (type: 'textGeneration' | 'embeddings', providerId: string) => {
    const newSelection = { ...modelSelection }
    
    if (type === 'textGeneration') {
      newSelection.textGeneration = { provider: providerId, model: null }
      if (modelSelection.useSharedProvider) {
        newSelection.embeddings = { provider: providerId, model: null }
      }
    } else {
      newSelection.embeddings = { provider: providerId, model: null }
    }
    
    onModelSelectionChange(newSelection)
  }
  
  // Handle model selection
  const handleModelChange = (type: 'textGeneration' | 'embeddings', modelId: string) => {
    const newSelection = { ...modelSelection }
    
    if (type === 'textGeneration') {
      newSelection.textGeneration.model = modelId
      if (modelSelection.useSharedProvider) {
        newSelection.embeddings.model = modelId
      }
    } else {
      newSelection.embeddings.model = modelId
    }
    
    onModelSelectionChange(newSelection)
  }
  
  // Handle custom model addition
  const handleAddCustomModel = async () => {
    if (!customModelName.trim() || !addModelProvider) return
    
    try {
      await onAddCustomModel(addModelProvider, {
        id: customModelName,
        name: customModelName,
        displayName: customModelName,
        isCustom: true
      })
      setShowAddModel(false)
      setCustomModelName('')
      setAddModelProvider('')
    } catch (error) {
      // Error handled by parent
    }
  }
  
  // Handle model deletion
  const handleDeleteModel = async (providerId: string, modelId: string) => {
    await onRemoveCustomModel(providerId, modelId)
  }
  
  // Handle save
  const handleSave = async () => {
    await onSaveModelSelection()
  }
  
  // Check if selection is valid
  const isSelectionValid = () => {
    const hasTextSelection = modelSelection.textGeneration.provider && modelSelection.textGeneration.model
    const hasEmbeddingSelection = modelSelection.embeddings.provider && modelSelection.embeddings.model
    return hasTextSelection && hasEmbeddingSelection
  }
  
  // Render model options with custom model indicator
  const renderModelOptions = (providerId: string | null) => {
    if (!providerId) return null
    
    const models = availableModels.get(providerId) || []
    return models.map(model => (
      <div key={model.id} className="flex items-center justify-between">
        <SelectItem value={model.id}>
          <span className="flex items-center gap-2">
            {model.displayName || model.name}
            {model.isCustom && (
              <span className="text-xs text-muted-foreground">(custom)</span>
            )}
          </span>
        </SelectItem>
        {model.isCustom && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 ml-2"
            onClick={(e) => {
              e.stopPropagation()
              handleDeleteModel(providerId, model.id)
            }}
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        )}
      </div>
    ))
  }
  
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Model Selection</CardTitle>
          <CardDescription>
            Choose models for text generation and embeddings from your configured providers
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {testedProviders.length === 0 ? (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                No providers have been configured and tested yet. Please configure at least one provider first.
              </AlertDescription>
            </Alert>
          ) : (
            <>
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
                  {/* Provider selector */}
                  <Select
                    value={modelSelection.textGeneration.provider || undefined}
                    onValueChange={(value) => handleProviderChange('textGeneration', value)}
                  >
                    <SelectTrigger className="w-[200px]">
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {textProviders.map(provider => (
                        <SelectItem key={provider.id} value={provider.id}>
                          {provider.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  
                  {/* Model selector */}
                  <Select
                    value={modelSelection.textGeneration.model || undefined}
                    onValueChange={(value) => handleModelChange('textGeneration', value)}
                    disabled={!modelSelection.textGeneration.provider}
                  >
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      {renderModelOptions(modelSelection.textGeneration.provider)}
                    </SelectContent>
                  </Select>
                  
                  {/* Add custom model button */}
                  <Button 
                    variant="outline" 
                    size="icon"
                    disabled={!modelSelection.textGeneration.provider || providers.find(p => p.id === modelSelection.textGeneration.provider)?.isQueryable}
                    onClick={() => {
                      setAddModelProvider(modelSelection.textGeneration.provider!)
                      setShowAddModel(true)
                    }}
                  >
                    <PlusCircle className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              
              {/* Embeddings Model Selection */}
              {!modelSelection.useSharedProvider && (
                <div className="space-y-2">
                  <Label>Embeddings Model</Label>
                  <div className="flex gap-2">
                    {/* Provider selector */}
                    <Select
                      value={modelSelection.embeddings.provider || undefined}
                      onValueChange={(value) => handleProviderChange('embeddings', value)}
                    >
                      <SelectTrigger className="w-[200px]">
                        <SelectValue placeholder="Select provider" />
                      </SelectTrigger>
                      <SelectContent>
                        {embeddingProviders.map(provider => (
                          <SelectItem key={provider.id} value={provider.id}>
                            {provider.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    {/* Model selector */}
                    <Select
                      value={modelSelection.embeddings.model || undefined}
                      onValueChange={(value) => handleModelChange('embeddings', value)}
                      disabled={!modelSelection.embeddings.provider}
                    >
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select model" />
                      </SelectTrigger>
                      <SelectContent>
                        {renderModelOptions(modelSelection.embeddings.provider)}
                      </SelectContent>
                    </Select>
                    
                    {/* Add custom model button */}
                    <Button 
                      variant="outline" 
                      size="icon"
                      disabled={!modelSelection.embeddings.provider || providers.find(p => p.id === modelSelection.embeddings.provider)?.isQueryable}
                      onClick={() => {
                        setAddModelProvider(modelSelection.embeddings.provider!)
                        setShowAddModel(true)
                      }}
                    >
                      <PlusCircle className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              )}
              
              {/* Save button */}
              <Button 
                onClick={handleSave} 
                className="w-full"
                disabled={!isSelectionValid() || isSaving}
              >
                {isSaving ? 'Saving...' : 'Save Model Configuration'}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
      
      {/* Add Custom Model Dialog */}
      <Dialog open={showAddModel} onOpenChange={setShowAddModel}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Custom Model</DialogTitle>
            <DialogDescription>
              Add a custom model name for {providers.find(p => p.id === addModelProvider)?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label htmlFor="model-name">Model Name</Label>
            <Input
              id="model-name"
              value={customModelName}
              onChange={(e) => setCustomModelName(e.target.value)}
              placeholder="e.g., gpt-4-turbo-preview"
              className="mt-2"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddModel(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddCustomModel} disabled={!customModelName.trim()}>
              Add Model
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}