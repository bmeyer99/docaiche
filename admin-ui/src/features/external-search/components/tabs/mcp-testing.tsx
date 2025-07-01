/**
 * MCP Testing Tab Component
 * 
 * Interface for testing external search providers and comparing results.
 */

'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Search, ExternalLink, Clock } from 'lucide-react';
import { apiClient } from '@/lib/utils/api-client';
import { useMCPProviders } from '../../hooks/use-mcp-providers';
import type { MCPExternalSearchResponse } from '@/lib/config/api';

export function MCPTestingTab() {
  const { data: providers } = useMCPProviders();
  const [testQuery, setTestQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<MCPExternalSearchResponse | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleTestSearch = async () => {
    if (!testQuery.trim()) return;
    
    setIsSearching(true);
    setSearchError(null);
    
    try {
      const response = await apiClient.performExternalSearch({
        query: testQuery,
        max_results: 10,
        force_external: true
      });
      
      setSearchResults(response);
    } catch (error) {
      console.error('External search test failed:', error);
      setSearchError('Search test failed. Please check your provider configuration.');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Test Interface */}
      <Card>
        <CardHeader>
          <CardTitle>Test External Search</CardTitle>
          <CardDescription>
            Test your external search providers to see how they respond to queries.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex space-x-2">
            <Input
              placeholder="Enter a test query..."
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleTestSearch()}
              disabled={isSearching}
            />
            <Button 
              onClick={handleTestSearch} 
              disabled={isSearching || !testQuery.trim()}
            >
              <Search className="mr-2 h-4 w-4" />
              {isSearching ? 'Searching...' : 'Test Search'}
            </Button>
          </div>

          {/* Provider Status */}
          <div className="text-sm text-muted-foreground">
            Available providers: {providers?.providers
              .filter(p => p.config.enabled)
              .map(p => p.provider_id)
              .join(', ') || 'None'}
          </div>
        </CardContent>
      </Card>

      {/* Search Results */}
      {isSearching && (
        <Card>
          <CardContent className="p-6">
            <div className="space-y-4">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          </CardContent>
        </Card>
      )}

      {searchError && (
        <Card>
          <CardContent className="p-6">
            <div className="text-red-600">
              {searchError}
            </div>
          </CardContent>
        </Card>
      )}

      {searchResults && !isSearching && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Search Results</CardTitle>
              <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                <div className="flex items-center">
                  <Clock className="mr-1 h-4 w-4" />
                  {searchResults.execution_time_ms}ms
                </div>
                <Badge variant={searchResults.cache_hit ? 'default' : 'outline'}>
                  {searchResults.cache_hit ? 'Cached' : 'Live'}
                </Badge>
              </div>
            </div>
            <CardDescription>
              Found {searchResults.total_results} results from {searchResults.providers_used.length} providers
            </CardDescription>
          </CardHeader>
          <CardContent>
            {searchResults.results.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                No results found
              </div>
            ) : (
              <div className="space-y-4">
                {searchResults.results.map((result, index) => (
                  <div key={index} className="border rounded-lg p-4">
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-medium text-lg leading-tight">
                        {result.title}
                      </h4>
                      <Badge variant="outline" className="ml-2 flex-shrink-0">
                        {result.provider}
                      </Badge>
                    </div>
                    
                    <p className="text-muted-foreground text-sm mb-3 line-clamp-2">
                      {result.snippet}
                    </p>
                    
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                        <Badge variant="secondary" className="text-xs">
                          {result.content_type}
                        </Badge>
                        {result.published_date && (
                          <span>
                            {new Date(result.published_date).toLocaleDateString()}
                          </span>
                        )}
                        {result.relevance_score && (
                          <span>
                            Relevance: {(result.relevance_score * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                      
                      <Button variant="ghost" size="sm" asChild>
                        <a 
                          href={result.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="flex items-center"
                        >
                          <ExternalLink className="mr-1 h-3 w-3" />
                          Visit
                        </a>
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Provider Information */}
      <Card>
        <CardHeader>
          <CardTitle>Provider Information</CardTitle>
          <CardDescription>
            Current status of your configured external search providers.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!providers || providers.providers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No providers configured. Add providers in the Providers tab to enable external search.
            </div>
          ) : (
            <div className="space-y-4">
              {providers.providers.map((provider) => (
                <div key={provider.provider_id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center space-x-4">
                    <div 
                      className={`w-3 h-3 rounded-full ${
                        provider.health.status === 'healthy' 
                          ? 'bg-green-500' 
                          : provider.health.status === 'degraded'
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                    />
                    <div>
                      <div className="font-medium">{provider.provider_id}</div>
                      <div className="text-sm text-muted-foreground">
                        {provider.config.provider_type} • Priority {provider.config.priority}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <Badge variant={provider.config.enabled ? 'default' : 'secondary'}>
                      {provider.config.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                    <div className="text-sm text-muted-foreground">
                      {provider.health.response_time_ms}ms
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}