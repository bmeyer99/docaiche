'use client';

/**
 * Main layout component for Search Configuration
 * Provides tabbed navigation for system configuration
 */

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Users, 
  Bot, 
  Database, 
  Globe, 
  HardDrive, 
  BarChart3, 
  Settings,
  Save,
  X,
  Loader2
} from 'lucide-react';
import { TabConfig } from '../types';
import { ConfigProvider, useSearchConfig } from '../contexts/config-context';
import { useProviderSettings, useModelSelection } from '@/lib/hooks/use-provider-settings';
import { useSearchConfigForm } from '../hooks/use-search-config-form';

// Import tab components
import { ProvidersConfig } from './tabs/providers';
import { VectorSearchConfig } from './tabs/vector-search';
import { EmbeddingAIConfig } from './tabs/embedding-ai';
import { TextAIConfig } from './tabs/text-ai';
import { IngestionConfig } from './tabs/ingestion';
import { SystemSettings } from './tabs/settings';

const TABS: TabConfig[] = [
  { id: 'providers', label: 'AI Providers', icon: 'Users', shortcut: 'Cmd+1' },
  { id: 'vector', label: 'Vector Search', icon: 'Database', shortcut: 'Cmd+2' },
  { id: 'embedding-ai', label: 'Embedding AI', icon: 'Bot', shortcut: 'Cmd+3' },
  { id: 'text-ai', label: 'Text AI', icon: 'Bot', shortcut: 'Cmd+4' },
  { id: 'ingestion', label: 'Ingestion', icon: 'HardDrive', shortcut: 'Cmd+5', badge: 'Soon' },
  { id: 'settings', label: 'Settings', icon: 'Settings', shortcut: 'Cmd+6', badge: 'Soon' }
];

const ICON_MAP = {
  Users,
  Database,
  Bot,
  Globe,
  HardDrive,
  BarChart3,
  Settings
};

function SearchConfigContent() {
  const { 
    isLoading, 
    loading,
    vectorConfig, 
    embeddingConfig, 
    modelParameters,
    reloadConfigurations
  } = useSearchConfig();
  const { providers, isLoading: providersLoading, loadSettings } = useProviderSettings();
  const { modelSelection, isLoading: modelSelectionLoading } = useModelSelection();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams?.get('tab') || 'providers');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  // Use centralized form management
  const { isDirty, saveForm, resetForm } = useSearchConfigForm();
  

  // Update URL when tab changes
  const handleTabChange = (value: string) => {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved changes. Are you sure you want to switch tabs?')) {
        return;
      }
    }
    setActiveTab(value);
    const params = new URLSearchParams(searchParams || '');
    params.set('tab', value);
    router.push(`?${params.toString()}`);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '6') {
        e.preventDefault();
        const tabIndex = parseInt(e.key) - 1;
        if (TABS[tabIndex]) {
          handleTabChange(TABS[tabIndex].id);
        }
      }
      // Save shortcut
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        if (hasUnsavedChanges) {
          handleSave();
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [hasUnsavedChanges]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveForm();
      setHasUnsavedChanges(false);
    } catch (error) {
      console.error('Failed to save configuration:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    if (confirm('Are you sure you want to discard all changes?')) {
      resetForm();
      setHasUnsavedChanges(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <Loader2 className="h-8 w-8 animate-spin mx-auto" />
          <p className="text-muted-foreground">Loading configurations...</p>
        </div>
      </div>
    );
  }

  if (loading.loadError) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center space-y-4">
          <p className="text-destructive">{loading.loadError}</p>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Search Configuration</h1>
          
          {(hasUnsavedChanges || isDirty) && (
            <div className="flex items-center gap-2">
              <Button 
                size="sm" 
                variant="outline" 
                onClick={handleDiscard}
                disabled={isSaving}
              >
                <X className="h-4 w-4 mr-2" />
                Discard
              </Button>
              <Button 
                size="sm"
                onClick={handleSave}
                disabled={isSaving}
              >
                {isSaving ? (
                  <>
                    <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          )}
        </div>
      </div>


      {/* Tabs */}
      <div className="flex-1 overflow-hidden">
        <Tabs value={activeTab} onValueChange={handleTabChange} className="h-full">
          <div className="border-b px-6">
            <TabsList className="h-12 bg-transparent p-0 border-b-0">
              {TABS.map((tab) => {
                const Icon = ICON_MAP[tab.icon as keyof typeof ICON_MAP];
                return (
                  <TabsTrigger
                    key={tab.id}
                    value={tab.id}
                    className="h-12 px-4 border-b-2 border-transparent data-[state=active]:border-primary rounded-none"
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    {tab.label}
                    {tab.badge && (
                      <Badge variant="secondary" className="ml-2">
                        {tab.badge}
                      </Badge>
                    )}
                  </TabsTrigger>
                );
              })}
            </TabsList>
          </div>

          <div className="flex-1 overflow-auto">
            <TabsContent value="providers" className="h-full m-0">
              <ProvidersConfig 
                onChangeDetected={() => setHasUnsavedChanges(true)} 
                onProviderUpdate={async () => {
                  // Refresh provider settings and configurations after successful test
                  try {
                    await Promise.all([
                      loadSettings(),
                      reloadConfigurations()
                    ]);
                  } catch (error) {
                    console.error('Failed to refresh after provider update:', error);
                  }
                }}
              />
            </TabsContent>
            
            <TabsContent value="vector" className="h-full m-0">
              <VectorSearchConfig 
                onChangeDetected={() => setHasUnsavedChanges(true)} 
                onSaveSuccess={() => setHasUnsavedChanges(false)}
              />
            </TabsContent>
            
            <TabsContent value="embedding-ai" className="h-full m-0">
              <EmbeddingAIConfig 
                onChangeDetected={() => setHasUnsavedChanges(true)} 
                onSaveSuccess={() => setHasUnsavedChanges(false)}
              />
            </TabsContent>
            
            <TabsContent value="text-ai" className="h-full m-0">
              <TextAIConfig 
                onChangeDetected={() => setHasUnsavedChanges(true)} 
                onSaveSuccess={() => setHasUnsavedChanges(false)}
              />
            </TabsContent>
            
            <TabsContent value="ingestion" className="h-full m-0">
              <IngestionConfig onChangeDetected={() => setHasUnsavedChanges(true)} />
            </TabsContent>
            
            <TabsContent value="settings" className="h-full m-0">
              <SystemSettings onChangeDetected={() => setHasUnsavedChanges(true)} />
            </TabsContent>
          </div>
        </Tabs>
      </div>

      {/* Keyboard shortcuts help */}
      <div className="border-t px-6 py-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <span>Keyboard shortcuts:</span>
          <span>⌘1-6 to switch tabs</span>
          <span>⌘S to save</span>
          <span>ESC to cancel</span>
        </div>
      </div>
    </div>
  );
}

export function SearchConfigLayout() {
  return (
    <ConfigProvider>
      <SearchConfigContent />
    </ConfigProvider>
  );
}