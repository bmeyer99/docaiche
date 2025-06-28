'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Icons } from '@/components/icons';
import { DocaicheApiClient } from '@/lib/utils/api-client';
import { useToast } from '@/hooks/use-toast';

interface SearchResult {
  id: string;
  title: string;
  content: string;
  collection: string;
  technology: string;
  score: number;
  url?: string;
  lastModified: string;
  fileType: string;
  highlights?: string[];
}

interface SearchFilters {
  collection?: string;
  technology?: string;
  fileType?: string;
  dateRange?: string;
}

export default function ContentSearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [filters, setFilters] = useState<SearchFilters>({});
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [searchTime, setSearchTime] = useState(0);
  const { toast } = useToast();

  const performSearch = useCallback(async (searchQuery: string, searchFilters: SearchFilters = {}) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setTotalResults(0);
      return;
    }

    setLoading(true);
    const startTime = Date.now();
    const apiClient = new DocaicheApiClient();

    try {
      const response = await apiClient.searchContent({
        query: searchQuery,
        ...searchFilters,
        limit: 20
      } as any);

      setResults((response as any).results || []);
      setTotalResults((response as any).total || 0);
      setSearchTime(Date.now() - startTime);
    } catch (error) {
      toast({
        title: "Search Error",
        description: "Failed to perform search. Please try again.",
        variant: "destructive",
      });
      setResults([]);
      setTotalResults(0);
    } finally {
      setLoading(false);
    }
  }, [toast]);

  const handleSearch = () => {
    performSearch(query, filters);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  const clearSearch = () => {
    setQuery('');
    setResults([]);
    setTotalResults(0);
    setFilters({});
  };

  const getFileTypeIcon = (fileType: string) => {
    switch (fileType.toLowerCase()) {
      case 'pdf': return <Icons.fileText className="w-4 h-4 text-red-600" />;
      case 'md': case 'markdown': return <Icons.fileText className="w-4 h-4 text-blue-600" />;
      case 'txt': return <Icons.fileText className="w-4 h-4 text-gray-600" />;
      case 'docx': case 'doc': return <Icons.fileText className="w-4 h-4 text-blue-700" />;
      case 'html': case 'htm': return <Icons.globe className="w-4 h-4 text-orange-600" />;
      default: return <Icons.page className="w-4 h-4" />;
    }
  };

  const formatScore = (score: number) => {
    return (score * 100).toFixed(1);
  };

  const truncateContent = (content: string, maxLength: number = 200) => {
    return content.length > maxLength ? content.substring(0, maxLength) + '...' : content;
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">Content Search</h1>
        <p className="text-muted-foreground">
          Search through indexed documents and content across all collections
        </p>
      </div>

      {/* Search Interface */}
      <Card>
        <CardHeader>
          <CardTitle>Search Documents</CardTitle>
          <CardDescription>
            Enter your search query and apply filters to find relevant content
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <div className="flex-1">
              <Textarea
                placeholder="Enter your search query..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyPress}
                className="min-h-[60px] resize-none"
              />
            </div>
            <div className="flex flex-col gap-2">
              <Button onClick={handleSearch} disabled={loading || !query.trim()}>
                {loading ? (
                  <>
                    <Icons.spinner className="w-4 h-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Icons.search className="w-4 h-4 mr-2" />
                    Search
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={clearSearch} size="sm">
                <Icons.close className="w-4 h-4 mr-2" />
                Clear
              </Button>
            </div>
          </div>

          {/* Filters */}
          <div className="grid gap-4 md:grid-cols-4">
            <Select
              value={filters.collection || ''}
              onValueChange={(value) => setFilters(prev => ({ ...prev, collection: value || undefined }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Collection" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Collections</SelectItem>
                <SelectItem value="documentation">Documentation</SelectItem>
                <SelectItem value="api-docs">API Docs</SelectItem>
                <SelectItem value="tutorials">Tutorials</SelectItem>
                <SelectItem value="guides">Guides</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.technology || ''}
              onValueChange={(value) => setFilters(prev => ({ ...prev, technology: value || undefined }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Technology" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Technologies</SelectItem>
                <SelectItem value="react">React</SelectItem>
                <SelectItem value="nextjs">Next.js</SelectItem>
                <SelectItem value="nodejs">Node.js</SelectItem>
                <SelectItem value="python">Python</SelectItem>
                <SelectItem value="typescript">TypeScript</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.fileType || ''}
              onValueChange={(value) => setFilters(prev => ({ ...prev, fileType: value || undefined }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="File Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Types</SelectItem>
                <SelectItem value="pdf">PDF</SelectItem>
                <SelectItem value="md">Markdown</SelectItem>
                <SelectItem value="txt">Text</SelectItem>
                <SelectItem value="html">HTML</SelectItem>
                <SelectItem value="docx">Word</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={filters.dateRange || ''}
              onValueChange={(value) => setFilters(prev => ({ ...prev, dateRange: value || undefined }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Date Range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Any Time</SelectItem>
                <SelectItem value="today">Today</SelectItem>
                <SelectItem value="week">This Week</SelectItem>
                <SelectItem value="month">This Month</SelectItem>
                <SelectItem value="year">This Year</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Search Results */}
      {(results.length > 0 || (query && !loading)) && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Search Results</CardTitle>
                <CardDescription>
                  {totalResults > 0 ? (
                    <>Found {totalResults.toLocaleString()} results in {searchTime}ms</>
                  ) : (
                    <>No results found for &ldquo;{query}&rdquo;</>
                  )}
                </CardDescription>
              </div>
              {results.length > 0 && (
                <Badge variant="secondary">
                  Showing {results.length} of {totalResults}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <div className="text-center">
                  <Icons.spinner className="w-8 h-8 animate-spin mx-auto mb-4" />
                  <div className="text-muted-foreground">Searching content...</div>
                </div>
              </div>
            ) : results.length > 0 ? (
              <div className="space-y-4">
                {results.map((result, index) => (
                  <div key={result.id} className="border rounded-lg p-4 hover:bg-accent/50 transition-colors">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {getFileTypeIcon(result.fileType)}
                        <h3 className="font-semibold text-lg">{result.title}</h3>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">
                          Score: {formatScore(result.score)}%
                        </Badge>
                        <Badge variant="secondary">
                          {result.fileType.toUpperCase()}
                        </Badge>
                      </div>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3">
                      <span className="flex items-center gap-1">
                        <Icons.folder className="w-3 h-3" />
                        {result.collection}
                      </span>
                      <span className="flex items-center gap-1">
                        <Icons.tag className="w-3 h-3" />
                        {result.technology}
                      </span>
                      <span className="flex items-center gap-1">
                        <Icons.calendar className="w-3 h-3" />
                        {new Date(result.lastModified).toLocaleDateString()}
                      </span>
                    </div>

                    <p className="text-muted-foreground mb-3">
                      {truncateContent(result.content)}
                    </p>

                    {result.highlights && result.highlights.length > 0 && (
                      <div className="mb-3">
                        <div className="text-sm font-medium mb-1">Highlights:</div>
                        <div className="space-y-1">
                          {result.highlights.slice(0, 2).map((highlight, idx) => (
                            <div key={idx} className="text-sm bg-yellow-100 dark:bg-yellow-900 p-2 rounded">
                              ...{highlight}...
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between">
                      <div className="text-xs text-muted-foreground">
                        Result #{index + 1}
                      </div>
                      <div className="flex gap-2">
                        {result.url && (
                          <Button variant="outline" size="sm" asChild>
                            <a href={result.url} target="_blank" rel="noopener noreferrer">
                              <Icons.externalLink className="w-3 h-3 mr-1" />
                              View
                            </a>
                          </Button>
                        )}
                        <Button variant="outline" size="sm">
                          <Icons.moreHorizontal className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <Icons.search className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <div className="text-lg font-medium mb-2">No results found</div>
                <div>Try adjusting your search query or filters</div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}