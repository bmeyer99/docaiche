'use client'

import React from 'react'
import { ProviderCardsProps, ProviderInfo, ProviderCategory } from '../types'
import { Card } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

/**
 * ProviderCards - Displays available AI providers grouped by category
 * 
 * Shows provider cards with status indicators, allowing users to select
 * a provider for configuration. Providers are organized into Local, Cloud,
 * and Enterprise categories.
 */
export function ProviderCards({
  providers,
  selectedProvider,
  selectedCategory,
  onProviderSelect,
  onCategoryChange
}: ProviderCardsProps) {
  // Group providers by category
  const providersByCategory = providers.reduce((acc, provider) => {
    if (!acc[provider.category]) {
      acc[provider.category] = []
    }
    acc[provider.category].push(provider)
    return acc
  }, {} as Record<ProviderCategory, ProviderInfo[]>)
  
  // Status badge variant mapping
  const getStatusVariant = (status: ProviderInfo['status']) => {
    switch (status) {
      case 'configured':
        return 'default'
      case 'failed':
        return 'destructive'
      case 'testing':
        return 'secondary'
      default:
        return 'outline'
    }
  }
  
  // Status display text
  const getStatusText = (status: ProviderInfo['status']) => {
    switch (status) {
      case 'configured':
        return 'Configured'
      case 'failed':
        return 'Failed'
      case 'testing':
        return 'Testing...'
      default:
        return 'Not Configured'
    }
  }
  
  // Render a single provider card
  const renderProviderCard = (provider: ProviderInfo) => {
    return (
      <Card 
        key={provider.id}
        className={cn(
          "cursor-pointer transition-all p-4 provider-card",
          "hover:shadow-md hover:border-primary/50",
          selectedProvider === provider.id && "ring-2 ring-primary border-primary selected"
        )}
        onClick={() => {
          console.log('[ProviderCard] Clicked provider:', provider.id)
          onProviderSelect(provider.id)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onProviderSelect(provider.id)
          }
        }}
        role="button"
        tabIndex={0}
        aria-label={`Select ${provider.name} provider`}
        aria-pressed={selectedProvider === provider.id}
      >
        <div className="space-y-2">
          <div className="flex items-start justify-between">
            <h4 className="font-medium">{provider.name}</h4>
            <Badge variant={getStatusVariant(provider.status)} className="text-xs">
              {getStatusText(provider.status)}
            </Badge>
          </div>
          
          <p className="text-sm text-muted-foreground line-clamp-2">
            {provider.description}
          </p>
          
          <div className="flex gap-2 mt-2">
            {provider.supportsChat && (
              <Badge variant="secondary" className="text-xs">
                Chat
              </Badge>
            )}
            {provider.supportsEmbedding && (
              <Badge variant="secondary" className="text-xs">
                Embeddings
              </Badge>
            )}
            {provider.isQueryable && (
              <Badge variant="secondary" className="text-xs">
                Auto-detect
              </Badge>
            )}
          </div>
        </div>
      </Card>
    )
  }
  
  return (
    <div className="w-full max-w-sm">
      <Tabs value={selectedCategory} onValueChange={(value) => onCategoryChange(value as ProviderCategory)}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="local">Local</TabsTrigger>
          <TabsTrigger value="cloud">Cloud</TabsTrigger>
          <TabsTrigger value="enterprise">Enterprise</TabsTrigger>
        </TabsList>
        
        <TabsContent value="local" className="space-y-2 mt-4">
          {providersByCategory.local?.length > 0 ? (
            providersByCategory.local.map(renderProviderCard)
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No local providers available
            </p>
          )}
        </TabsContent>
        
        <TabsContent value="cloud" className="space-y-2 mt-4">
          {providersByCategory.cloud?.length > 0 ? (
            providersByCategory.cloud.map(renderProviderCard)
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No cloud providers available
            </p>
          )}
        </TabsContent>
        
        <TabsContent value="enterprise" className="space-y-2 mt-4">
          {providersByCategory.enterprise?.length > 0 ? (
            providersByCategory.enterprise.map(renderProviderCard)
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No enterprise providers available
            </p>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}