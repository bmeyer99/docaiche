/**
 * MCP Providers Tab Component
 * 
 * Displays and manages external search providers with CRUD operations.
 */

'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { AlertModal } from '@/components/modal/alert-modal';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { 
  Plus, 
  MoreHorizontal, 
  Settings, 
  TestTube, 
  Trash2,
  RefreshCw,
  ExternalLink,
  Info
} from 'lucide-react';
import { useMCPProviders } from '../../hooks/use-mcp-providers';
import { MCPProviderForm } from '../shared/mcp-provider-form';
import type { MCPProvider } from '@/lib/config/api';

export function MCPProvidersTab() {
  const { data, isLoading, error, refetch, deleteProvider, testProvider } = useMCPProviders();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingProvider, setEditingProvider] = useState<MCPProvider | null>(null);
  const [deletingProvider, setDeletingProvider] = useState<MCPProvider | null>(null);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  
  // Find the active provider (lowest priority among enabled providers)
  const activeProvider = data?.providers
    .filter(p => p.config.enabled)
    .sort((a, b) => a.config.priority - b.config.priority)[0];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'unhealthy':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'healthy':
        return <Badge className="bg-green-100 text-green-800">Healthy</Badge>;
      case 'degraded':
        return <Badge variant="outline" className="border-yellow-500 text-yellow-700">Degraded</Badge>;
      case 'unhealthy':
        return <Badge variant="destructive">Unhealthy</Badge>;
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  const handleDelete = async () => {
    if (!deletingProvider) return;
    
    const success = await deleteProvider(deletingProvider.provider_id);
    if (success) {
      setDeletingProvider(null);
    }
  };

  const handleTest = async (providerId: string) => {
    setTestingProvider(providerId);
    await testProvider(providerId);
    setTestingProvider(null);
  };

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-muted-foreground mb-4">Failed to load providers</p>
          <Button onClick={refetch} variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Button onClick={refetch} variant="outline" size="sm">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
        <Button onClick={() => setShowCreateForm(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Provider
        </Button>
      </div>

      {/* Providers Table */}
      {isLoading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Provider</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Performance</TableHead>
                <TableHead>
                  <div className="flex items-center gap-2">
                    Enabled
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <Info className="h-3 w-3 text-muted-foreground" />
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>The provider with the lowest priority number that is enabled will be active</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </div>
                </TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.providers.map((provider) => (
                <TableRow key={provider.provider_id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center space-x-3">
                      <div 
                        className={`w-3 h-3 rounded-full ${getStatusColor(provider.health.status)}`}
                      />
                      <span>{provider.provider_id}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {provider.config.provider_type}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {getStatusBadge(provider.health.status)}
                  </TableCell>
                  <TableCell>{provider.config.priority}</TableCell>
                  <TableCell>
                    <div className="text-sm">
                      <div>{provider.health.response_time_ms}ms</div>
                      <div className="text-muted-foreground">
                        {Math.round((provider.health.success_rate || 0) * 100)}% success
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Badge variant={provider.config.enabled ? 'default' : 'secondary'}>
                        {provider.config.enabled ? 'Enabled' : 'Disabled'}
                      </Badge>
                      {provider.provider_id === activeProvider?.provider_id && (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300">
                          Active
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => setEditingProvider(provider)}
                        >
                          <Settings className="mr-2 h-4 w-4" />
                          Configure
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => handleTest(provider.provider_id)}
                          disabled={testingProvider === provider.provider_id}
                        >
                          <TestTube className="mr-2 h-4 w-4" />
                          {testingProvider === provider.provider_id ? 'Testing...' : 'Test'}
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          onClick={() => setDeletingProvider(provider)}
                          className="text-red-600"
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              )) || []}
            </TableBody>
          </Table>
          
          {(!data?.providers || data.providers.length === 0) && (
            <div className="text-center py-8">
              <p className="text-muted-foreground mb-4">No providers configured</p>
              <Button onClick={() => setShowCreateForm(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Add Your First Provider
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* Create Provider Form */}
      {showCreateForm && (
        <MCPProviderForm
          isOpen={showCreateForm}
          onClose={() => setShowCreateForm(false)}
          onSuccess={() => {
            setShowCreateForm(false);
            refetch();
          }}
        />
      )}

      {/* Edit Provider Form */}
      {editingProvider && (
        <MCPProviderForm
          isOpen={!!editingProvider}
          provider={editingProvider}
          onClose={() => setEditingProvider(null)}
          onSuccess={() => {
            setEditingProvider(null);
            refetch();
          }}
        />
      )}

      {/* Delete Confirmation */}
      <AlertModal
        isOpen={!!deletingProvider}
        onClose={() => setDeletingProvider(null)}
        onConfirm={handleDelete}
        loading={false}
      />
    </div>
  );
}