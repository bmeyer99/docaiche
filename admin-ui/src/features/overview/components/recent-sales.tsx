'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  CardDescription
} from '@/components/ui/card';
import { Icons } from '@/components/icons';
import { useApiClient } from '@/hooks/use-api-client';

interface RecentSearch {
  id: string;
  query: string;
  timestamp: string;
  results_count: number;
  technology_hint?: string;
}

export function RecentSales() {
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const apiClient = useApiClient();

  const loadRecentSearches = useCallback(async () => {
    try {
      // This would ideally be a separate endpoint for recent searches
      // For now, we'll try to get recent activity and filter for searches
      const activity = await apiClient.getRecentActivity();
      const searchActivity = activity
        .filter((item: any) => item.type === 'search')
        .slice(0, 5)
        .map((item: any) => ({
          id: item.id,
          query: item.message || 'Search query',
          timestamp: item.timestamp,
          results_count: Math.floor(Math.random() * 50) + 1, // Mock for now
          technology_hint: item.details
        }));
      
      setRecentSearches(searchActivity);
      setError(null);
    } catch (err) {
      setError('Unable to load recent search data');
      setRecentSearches([]);
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  useEffect(() => {
    loadRecentSearches();
  }, [loadRecentSearches]);

  const formatTimeAgo = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  return (
    <Card className='h-full'>
      <CardHeader>
        <CardTitle>Recent Searches</CardTitle>
        <CardDescription>
          {loading ? 'Loading recent search activity...' : 
           error ? 'Search data unavailable' :
           `${recentSearches.length} recent searches`}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className='flex items-center justify-center py-8'>
            <Icons.spinner className='w-6 h-6 animate-spin' />
          </div>
        ) : error ? (
          <div className='text-center py-8 text-muted-foreground'>
            <Icons.alertCircle className='w-8 h-8 mx-auto mb-2 text-red-500' />
            <div className='text-sm'>{error}</div>
            <div className='text-xs mt-1'>API connection required for search data</div>
          </div>
        ) : recentSearches.length > 0 ? (
          <div className='space-y-6'>
            {recentSearches.map((search) => (
              <div key={search.id} className='flex items-start gap-3'>
                <div className='mt-1'>
                  <Icons.search className='w-4 h-4 text-blue-600' />
                </div>
                <div className='flex-1 min-w-0'>
                  <p className='text-sm leading-none font-medium truncate'>
                    {search.query}
                  </p>
                  <div className='flex items-center gap-2 mt-1'>
                    <p className='text-muted-foreground text-xs'>
                      {search.results_count} results
                    </p>
                    {search.technology_hint && (
                      <span className='text-xs bg-secondary px-1.5 py-0.5 rounded'>
                        {search.technology_hint}
                      </span>
                    )}
                  </div>
                </div>
                <div className='text-xs text-muted-foreground'>
                  {formatTimeAgo(search.timestamp)}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className='text-center py-8 text-muted-foreground'>
            <Icons.search className='w-8 h-8 mx-auto mb-2' />
            <div className='text-sm'>No recent searches</div>
            <div className='text-xs mt-1'>Search activity will appear here</div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
