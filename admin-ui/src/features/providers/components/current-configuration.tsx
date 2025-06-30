'use client'

import React from 'react'
import { CurrentConfigurationProps } from '../types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

/**
 * CurrentConfiguration - Displays the current model configuration summary
 * 
 * Shows the currently selected models for text generation and embeddings,
 * allowing users to quickly see and modify their configuration.
 */
export function CurrentConfiguration({
  modelSelection,
  providers,
  onEditConfiguration
}: CurrentConfigurationProps) {
  // TODO: Find provider details for selected models
  const textProvider = providers.find(p => p.id === modelSelection.textGeneration.provider)
  const embeddingProvider = providers.find(p => p.id === modelSelection.embeddings.provider)
  
  // Don't show if no configuration exists
  if (!modelSelection.textGeneration.provider && !modelSelection.embeddings.provider) {
    return null
  }
  
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Current Configuration</CardTitle>
          <CardDescription>Your active AI model settings</CardDescription>
        </div>
        <Button variant="outline" size="sm" onClick={onEditConfiguration}>
          Change Models
        </Button>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          {/* Text Generation Configuration */}
          <div className="space-y-1">
            <p className="text-sm font-medium">Text Generation</p>
            {textProvider ? (
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">{textProvider.name}</p>
                <Badge variant="secondary">{modelSelection.textGeneration.model}</Badge>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Not configured</p>
            )}
          </div>
          
          {/* Embeddings Configuration */}
          <div className="space-y-1">
            <p className="text-sm font-medium">Embeddings</p>
            {embeddingProvider ? (
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">{embeddingProvider.name}</p>
                <Badge variant="secondary">{modelSelection.embeddings.model}</Badge>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Not configured</p>
            )}
          </div>
        </div>
        
        {/* Shared provider indicator */}
        {modelSelection.useSharedProvider && (
          <div className="mt-3 pt-3 border-t">
            <Badge variant="outline">Using shared provider</Badge>
          </div>
        )}
      </CardContent>
    </Card>
  )
}