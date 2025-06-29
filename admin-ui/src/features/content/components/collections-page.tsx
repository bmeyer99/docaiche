'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { Icons } from '@/components/icons';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { CircuitBreakerIndicator } from '@/components/ui/circuit-breaker-indicator';
import { useDebouncedApi } from '@/lib/hooks/use-debounced-api';

interface Collection {
  id: string;
  name: string;
  description: string;
  documentCount: number;
  totalSize: number;
  lastModified: string;
  technology: string[];
  status: 'active' | 'indexing' | 'error';
  indexingProgress?: number;
}

export default function CollectionsPage() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [newCollection, setNewCollection] = useState({
    name: '',
    description: '',
    technology: ''
  });
  const { toast } = useToast();
  const apiClient = useApiClient();
  
  // Use debounced API hook
  const {
    data: collectionsData,
    loading: collectionsLoading,
    refetch: refetchCollections,
    canMakeRequest,
    circuitState
  } = useDebouncedApi(
    () => apiClient.getCollections(),
    'collections-api',
    {
      debounceMs: 2000,
      onSuccess: () => {
        // Data is handled in the component render
      },
      onError: (error) => {
        // Collections load failed
        toast({
          title: "Error",
          description: "Failed to load collections",
          variant: "destructive",
        });
      }
    }
  );
  
  const collections = (collectionsData?.collections || []) as unknown as Collection[];
  


  const createCollection = async () => {
    if (!newCollection.name.trim()) {
      toast({
        title: "Validation Error",
        description: "Collection name is required",
        variant: "destructive",
      });
      return;
    }

    try {
      await apiClient.createCollection({
        name: newCollection.name,
        description: newCollection.description,
        metadata: {
          technology: newCollection.technology.split(',').map(t => t.trim()).filter(Boolean)
        }
      });

      toast({
        title: "Success",
        description: `Collection "${newCollection.name}" created successfully`,
      });

      setCreateDialogOpen(false);
      setNewCollection({ name: '', description: '', technology: '' });
      refetchCollections();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create collection",
        variant: "destructive",
      });
    }
  };

  const deleteCollection = async (collectionId: string, collectionName: string) => {
    if (!confirm(`Are you sure you want to delete the collection "${collectionName}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await apiClient.deleteCollection(collectionId);
      toast({
        title: "Success",
        description: `Collection "${collectionName}" deleted successfully`,
      });
      refetchCollections();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to delete collection",
        variant: "destructive",
      });
    }
  };

  const reindexCollection = async (collectionId: string, collectionName: string) => {
    try {
      await apiClient.reindexCollection(collectionId);
      toast({
        title: "Success",
        description: `Reindexing started for collection "${collectionName}"`,
      });
      refetchCollections();
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to start reindexing",
        variant: "destructive",
      });
    }
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['B', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 B';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const getStatusBadge = (status: Collection['status'], progress?: number) => {
    switch (status) {
      case 'active':
        return <Badge className="bg-green-100 text-green-800">Active</Badge>;
      case 'indexing':
        return <Badge className="bg-blue-100 text-blue-800">Indexing {progress ? `${progress}%` : ''}</Badge>;
      case 'error':
        return <Badge className="bg-red-100 text-red-800">Error</Badge>;
      default:
        return <Badge variant="secondary">Unknown</Badge>;
    }
  };

  const getStatusIcon = (status: Collection['status']) => {
    switch (status) {
      case 'active':
        return <Icons.checkCircle className="w-4 h-4 text-green-600" />;
      case 'indexing':
        return <Icons.spinner className="w-4 h-4 text-blue-600 animate-spin" />;
      case 'error':
        return <Icons.alertCircle className="w-4 h-4 text-red-600" />;
      default:
        return <Icons.circle className="w-4 h-4 text-gray-600" />;
    }
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Collections Management</h1>
          <p className="text-muted-foreground">
            Organize and manage your document collections
          </p>
        </div>
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Icons.add className="w-4 h-4 mr-2" />
              Create Collection
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Collection</DialogTitle>
              <DialogDescription>
                Create a new collection to organize your documents
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Collection Name</Label>
                <Input
                  id="name"
                  value={newCollection.name}
                  onChange={(e) => setNewCollection(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="Enter collection name"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={newCollection.description}
                  onChange={(e) => setNewCollection(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Enter collection description"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="technology">Technologies (comma-separated)</Label>
                <Input
                  id="technology"
                  value={newCollection.technology}
                  onChange={(e) => setNewCollection(prev => ({ ...prev, technology: e.target.value }))}
                  placeholder="e.g., React, TypeScript, Next.js"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={createCollection}>
                Create Collection
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Circuit Breaker Status */}
      <CircuitBreakerIndicator 
        identifier="collections-api" 
        onReset={refetchCollections}
      />
      
      {/* Show circuit state info */}
      {!canMakeRequest && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <Icons.alertCircle className="w-5 h-5 text-red-600" />
            <div>
              <div className="font-medium text-red-800">API Connection Blocked</div>
              <div className="text-sm text-red-600">
                Circuit breaker is {circuitState} - Collections API calls are temporarily disabled
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Collections Grid */}
      {collectionsLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Icons.spinner className="w-8 h-8 animate-spin mx-auto mb-4" />
            <div className="text-muted-foreground">Loading collections...</div>
          </div>
        </div>
      ) : collections.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {collections.map((collection) => (
            <Card key={collection.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {getStatusIcon(collection.status)}
                    <CardTitle className="text-lg">{collection.name}</CardTitle>
                  </div>
                  {getStatusBadge(collection.status, collection.indexingProgress)}
                </div>
                <CardDescription className="min-h-[40px]">
                  {collection.description || 'No description provided'}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Indexing Progress */}
                {collection.status === 'indexing' && collection.indexingProgress !== undefined && (
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span>Indexing Progress</span>
                      <span>{collection.indexingProgress}%</span>
                    </div>
                    <Progress value={collection.indexingProgress} className="h-2" />
                  </div>
                )}

                {/* Statistics */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="font-medium text-2xl">{collection.documentCount.toLocaleString()}</div>
                    <div className="text-muted-foreground">Documents</div>
                  </div>
                  <div>
                    <div className="font-medium text-2xl">{formatFileSize(collection.totalSize)}</div>
                    <div className="text-muted-foreground">Total Size</div>
                  </div>
                </div>

                {/* Technologies */}
                {collection.technology.length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-2">Technologies</div>
                    <div className="flex flex-wrap gap-1">
                      {collection.technology.slice(0, 3).map((tech) => (
                        <Badge key={tech} variant="outline" className="text-xs">
                          {tech}
                        </Badge>
                      ))}
                      {collection.technology.length > 3 && (
                        <Badge variant="outline" className="text-xs">
                          +{collection.technology.length - 3} more
                        </Badge>
                      )}
                    </div>
                  </div>
                )}

                {/* Last Modified */}
                <div className="text-xs text-muted-foreground">
                  Last modified: {new Date(collection.lastModified).toLocaleDateString()}
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" size="sm" className="flex-1">
                    <Icons.eye className="w-3 h-3 mr-1" />
                    View
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => reindexCollection(collection.id, collection.name)}
                    disabled={collection.status === 'indexing'}
                  >
                    <Icons.arrowRight className="w-3 h-3 mr-1" />
                    Reindex
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => deleteCollection(collection.id, collection.name)}
                  >
                    <Icons.trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="text-center py-12">
            <Icons.folder className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
            <div className="text-lg font-medium mb-2">No Collections Found</div>
            <div className="text-muted-foreground mb-4">
              Create your first collection to start organizing your documents
            </div>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Icons.add className="w-4 h-4 mr-2" />
              Create Collection
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}