'use client';

import { memo } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Icons } from '@/components/icons';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

interface ContentMetrics {
  totalDocuments: number;
  totalCollections: number;
  indexedToday: number;
  mostAccessedDocs: Array<{ title: string; accessCount: number; technology: string }>;
  documentsByType: Array<{ type: string; count: number; sizeGB: number }>;
  documentsByTechnology: Array<{ technology: string; count: number; color: string }>;
}

interface AnalyticsContentMetricsProps {
  contentMetrics: ContentMetrics | null;
}

const PIE_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', 
  '#8b5cf6', '#06b6d4', '#84cc16', '#f97316'
];

export const AnalyticsContentMetrics = memo(function AnalyticsContentMetrics({ contentMetrics }: AnalyticsContentMetricsProps) {
  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatBytes = (bytes: number) => {
    const gb = bytes * 1024 * 1024 * 1024; // Convert from GB to bytes
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    if (gb === 0) return '0 B';
    const i = Math.floor(Math.log(gb) / Math.log(1024));
    return `${(gb / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  if (!contentMetrics) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No content metrics available
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <Icons.fileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {contentMetrics.totalDocuments ? formatNumber(contentMetrics.totalDocuments) : '0'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Collections</CardTitle>
            <Icons.folder className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {contentMetrics.totalCollections || '0'}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Indexed Today</CardTitle>
            <Icons.add className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {contentMetrics.indexedToday || '0'}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Documents by Technology</CardTitle>
            <CardDescription>Distribution across different technologies</CardDescription>
          </CardHeader>
          <CardContent>
            {contentMetrics.documentsByTechnology && contentMetrics.documentsByTechnology.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={contentMetrics.documentsByTechnology}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ technology, count }) => `${technology}: ${count}`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {contentMetrics.documentsByTechnology.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color || PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No technology distribution data
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Most Accessed Documents</CardTitle>
            <CardDescription>Popular content based on search results</CardDescription>
          </CardHeader>
          <CardContent>
            {contentMetrics.mostAccessedDocs && contentMetrics.mostAccessedDocs.length > 0 ? (
              <div className="space-y-3">
                {contentMetrics.mostAccessedDocs.slice(0, 5).map((doc, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <Badge variant="outline">{index + 1}</Badge>
                      <div className="flex-1 min-w-0">
                        <span className="font-medium truncate block">{doc.title}</span>
                        <span className="text-xs text-muted-foreground">{doc.technology}</span>
                      </div>
                    </div>
                    <span className="text-sm text-muted-foreground">
                      {formatNumber(doc.accessCount)} views
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                No access data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Documents by Type</CardTitle>
          <CardDescription>File format distribution and storage</CardDescription>
        </CardHeader>
        <CardContent>
          {contentMetrics.documentsByType && contentMetrics.documentsByType.length > 0 ? (
            <div className="space-y-3">
              {contentMetrics.documentsByType.map((type, index) => (
                <div key={index} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{type.type.toUpperCase()}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground">
                        {formatNumber(type.count)} files
                      </span>
                      <Badge variant="secondary">
                        {formatBytes(type.sizeGB)}
                      </Badge>
                    </div>
                  </div>
                  <Progress 
                    value={(type.count / contentMetrics.totalDocuments) * 100} 
                    className="h-2" 
                  />
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No document type data available
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
});