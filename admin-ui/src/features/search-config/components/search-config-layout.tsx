'use client';

/**
 * Main layout component for Search Configuration
 * Provides tabbed navigation and real-time status
 */

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Activity, 
  Bot, 
  Database, 
  Globe, 
  HardDrive, 
  BarChart3, 
  Settings,
  Save,
  X,
  RefreshCw,
  AlertCircle,
  CheckCircle
} from 'lucide-react';
import { useSystemHealth, useConfigChangeNotifications } from '../hooks/use-search-config-websocket';
import { TabConfig } from '../types';

// Import tab components (to be created)
import { SearchConfigDashboard } from './tabs/dashboard';
import { VectorSearchConfig } from './tabs/vector-search';
import { TextAIConfig } from './tabs/text-ai';
import { SearchProvidersConfig } from './tabs/search-providers';
import { IngestionConfig } from './tabs/ingestion';
import { MonitoringConfig } from './tabs/monitoring';
import { SystemSettings } from './tabs/settings';

const TABS: TabConfig[] = [
  { id: 'dashboard', label: 'Dashboard', icon: 'Activity', shortcut: 'Cmd+1' },
  { id: 'vector', label: 'Vector Search', icon: 'Database', shortcut: 'Cmd+2' },
  { id: 'text-ai', label: 'Text AI', icon: 'Bot', shortcut: 'Cmd+3' },
  { id: 'providers', label: 'Search Providers', icon: 'Globe', shortcut: 'Cmd+4' },
  { id: 'ingestion', label: 'Ingestion', icon: 'HardDrive', shortcut: 'Cmd+5' },
  { id: 'monitoring', label: 'Monitoring', icon: 'BarChart3', shortcut: 'Cmd+6' },
  { id: 'settings', label: 'Settings', icon: 'Settings', shortcut: 'Cmd+7' }
];

const ICON_MAP = {
  Activity,
  Database,
  Bot,
  Globe,
  HardDrive,
  BarChart3,
  Settings
};

export function SearchConfigLayout() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'dashboard');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const { overallHealth, isConnected } = useSystemHealth();
  const { pendingChanges, acknowledgeChanges } = useConfigChangeNotifications();

  // Update URL when tab changes
  const handleTabChange = (value: string) => {
    if (hasUnsavedChanges) {
      if (!confirm('You have unsaved changes. Are you sure you want to switch tabs?')) {
        return;
      }
    }
    setActiveTab(value);
    const params = new URLSearchParams(searchParams);
    params.set('tab', value);
    router.push(`?${params.toString()}`);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '7') {
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
      // TODO: Implement save logic
      await new Promise(resolve => setTimeout(resolve, 1000));
      setHasUnsavedChanges(false);
    } catch (error) {
      console.error('Failed to save configuration:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDiscard = () => {
    if (confirm('Are you sure you want to discard all changes?')) {
      setHasUnsavedChanges(false);
      // TODO: Reset form values
    }
  };

  const getHealthBadge = () => {
    if (!isConnected) return <Badge variant="outline">Disconnected</Badge>;
    
    switch (overallHealth) {
      case 'healthy':
        return <Badge className="bg-green-500">All Systems Operational</Badge>;
      case 'degraded':
        return <Badge className="bg-yellow-500">Degraded Performance</Badge>;
      case 'unhealthy':
        return <Badge className="bg-red-500">System Issues</Badge>;
      default:
        return <Badge variant="outline">Unknown</Badge>;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">Search Configuration</h1>
            {getHealthBadge()}
            {!isConnected && (
              <Button size="sm" variant="outline" onClick={() => window.location.reload()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Reconnect
              </Button>
            )}
          </div>
          
          {hasUnsavedChanges && (
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
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
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

      {/* Notifications */}
      {pendingChanges && (
        <Alert className="mx-6 mt-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>Configuration has been updated by another user.</span>
            <Button size="sm" variant="outline" onClick={acknowledgeChanges}>
              Refresh
            </Button>
          </AlertDescription>
        </Alert>
      )}

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
            <TabsContent value="dashboard" className="h-full m-0">
              <SearchConfigDashboard onChangeDetected={() => setHasUnsavedChanges(true)} />
            </TabsContent>
            
            <TabsContent value="vector" className="h-full m-0">
              <VectorSearchConfig onChangeDetected={() => setHasUnsavedChanges(true)} />
            </TabsContent>
            
            <TabsContent value="text-ai" className="h-full m-0">
              <TextAIConfig onChangeDetected={() => setHasUnsavedChanges(true)} />
            </TabsContent>
            
            <TabsContent value="providers" className="h-full m-0">
              <SearchProvidersConfig onChangeDetected={() => setHasUnsavedChanges(true)} />
            </TabsContent>
            
            <TabsContent value="ingestion" className="h-full m-0">
              <IngestionConfig onChangeDetected={() => setHasUnsavedChanges(true)} />
            </TabsContent>
            
            <TabsContent value="monitoring" className="h-full m-0">
              <MonitoringConfig />
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
          <span>⌘1-7 to switch tabs</span>
          <span>⌘S to save</span>
          <span>ESC to cancel</span>
        </div>
      </div>
    </div>
  );
}