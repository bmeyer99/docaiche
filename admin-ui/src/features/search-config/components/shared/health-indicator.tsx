/**
 * Health status indicator component
 */

import React from 'react';
import { cn } from '@/lib/utils';
import { HealthIndicatorProps } from '../../types';

export function HealthIndicator({
  status,
  label,
  showLabel = true,
  size = 'md',
  pulse = false
}: HealthIndicatorProps) {
  const sizeClasses = {
    sm: 'h-2 w-2',
    md: 'h-3 w-3',
    lg: 'h-4 w-4'
  };

  const statusClasses = {
    healthy: 'bg-green-500',
    degraded: 'bg-yellow-500',
    unhealthy: 'bg-red-500',
    unknown: 'bg-gray-400'
  };

  const statusLabels = {
    healthy: label || 'Healthy',
    degraded: label || 'Degraded',
    unhealthy: label || 'Unhealthy',
    unknown: label || 'Unknown'
  };

  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        <div
          className={cn(
            'rounded-full',
            sizeClasses[size],
            statusClasses[status],
            pulse && status !== 'unknown' && 'animate-pulse'
          )}
        />
        {/* Glow effect for critical status */}
        {status === 'unhealthy' && (
          <div
            className={cn(
              'absolute inset-0 rounded-full bg-red-500 blur animate-ping',
              sizeClasses[size]
            )}
          />
        )}
      </div>
      {showLabel && (
        <span className={cn(
          'text-sm',
          status === 'healthy' && 'text-green-600',
          status === 'degraded' && 'text-yellow-600',
          status === 'unhealthy' && 'text-red-600',
          status === 'unknown' && 'text-gray-500'
        )}>
          {statusLabels[status]}
        </span>
      )}
    </div>
  );
}