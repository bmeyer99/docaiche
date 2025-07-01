/**
 * Reusable metric card component for displaying real-time metrics
 */

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { cn } from '@/lib/utils';
import { MetricCardProps } from '../../types';

export function MetricCard({
  title,
  value,
  change,
  trend,
  loading = false,
  error,
  icon
}: MetricCardProps) {
  const getTrendIcon = () => {
    if (!trend || change === undefined) return null;
    
    switch (trend) {
      case 'up':
        return <TrendingUp className="h-4 w-4" />;
      case 'down':
        return <TrendingDown className="h-4 w-4" />;
      default:
        return <Minus className="h-4 w-4" />;
    }
  };

  const getTrendColor = () => {
    if (!trend || change === undefined) return 'text-muted-foreground';
    
    // Positive change is good for most metrics
    if (change > 0) {
      return trend === 'up' ? 'text-green-600' : 'text-red-600';
    } else if (change < 0) {
      return trend === 'down' ? 'text-green-600' : 'text-red-600';
    }
    return 'text-muted-foreground';
  };

  const formatChange = () => {
    if (change === undefined) return null;
    const sign = change > 0 ? '+' : '';
    return `${sign}${change.toFixed(1)}%`;
  };

  return (
    <Card>
      <CardContent className="p-6">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>
        ) : error ? (
          <div className="text-red-500">
            <p className="text-sm font-medium">{title}</p>
            <p className="text-xs mt-1">Error loading data</p>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm font-medium text-muted-foreground">{title}</p>
              {icon && <div className="text-muted-foreground">{icon}</div>}
            </div>
            <div className="flex items-baseline gap-2">
              <p className="text-2xl font-bold">{value}</p>
              {change !== undefined && (
                <div className={cn("flex items-center gap-1 text-sm", getTrendColor())}>
                  {getTrendIcon()}
                  <span>{formatChange()}</span>
                </div>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}