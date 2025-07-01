/**
 * Reusable provider card component
 */

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { 
  Settings, 
  PlayCircle, 
  GripVertical,
  Clock,
  AlertCircle,
  Zap
} from 'lucide-react';
import { HealthIndicator } from './health-indicator';
import { cn } from '@/lib/utils';
import { ProviderCardProps } from '../../types';

export function ProviderCard({
  provider,
  config,
  onConfigure,
  onTest,
  onToggle,
  draggable = false
}: ProviderCardProps) {
  const isConfigured = config && config.config && Object.keys(config.config).length > 0;
  
  const getCircuitBreakerBadge = () => {
    switch (provider.circuit_breaker_state) {
      case 'open':
        return <Badge variant="destructive">Circuit Open</Badge>;
      case 'half_open':
        return <Badge variant="secondary">Circuit Half-Open</Badge>;
      default:
        return null;
    }
  };

  return (
    <Card className={cn(
      "relative",
      draggable && "cursor-move hover:shadow-lg transition-shadow"
    )}>
      {draggable && (
        <div className="absolute left-2 top-1/2 -translate-y-1/2 text-muted-foreground">
          <GripVertical className="h-5 w-5" />
        </div>
      )}
      
      <CardHeader className={cn("pb-3", draggable && "pl-10")}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CardTitle className="text-lg">{provider.name}</CardTitle>
            <HealthIndicator 
              status={provider.health} 
              showLabel={false}
              size="sm"
              pulse
            />
            {getCircuitBreakerBadge()}
          </div>
          
          <Switch
            checked={provider.enabled}
            onCheckedChange={onToggle}
            disabled={!isConfigured}
          />
        </div>
      </CardHeader>
      
      <CardContent className={cn(draggable && "pl-10")}>
        <div className="space-y-3">
          {/* Metrics */}
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">Latency:</span>
                <span className="font-medium">
                  {provider.latency_ms ? `${provider.latency_ms}ms` : 'N/A'}
                </span>
              </div>
              
              <div className="flex items-center gap-1">
                <AlertCircle className="h-3 w-3 text-muted-foreground" />
                <span className="text-muted-foreground">Errors:</span>
                <span className="font-medium">
                  {(provider.error_rate * 100).toFixed(1)}%
                </span>
              </div>
              
              {provider.rate_limit_remaining !== undefined && (
                <div className="flex items-center gap-1">
                  <Zap className="h-3 w-3 text-muted-foreground" />
                  <span className="text-muted-foreground">Rate Limit:</span>
                  <span className="font-medium">
                    {provider.rate_limit_remaining}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Configuration status */}
          {!isConfigured && (
            <div className="text-sm text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20 p-2 rounded">
              Provider not configured. Click configure to set up.
            </div>
          )}

          {/* Priority badge */}
          {config && (
            <div className="flex items-center gap-2">
              <Badge variant="outline">Priority: {config.priority}</Badge>
              <Badge variant="outline">Type: {provider.type}</Badge>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Button 
              size="sm" 
              variant="outline"
              onClick={onConfigure}
              className="flex-1"
            >
              <Settings className="h-4 w-4 mr-2" />
              Configure
            </Button>
            
            {isConfigured && (
              <Button 
                size="sm" 
                variant="outline"
                onClick={onTest}
                disabled={!provider.enabled}
                className="flex-1"
              >
                <PlayCircle className="h-4 w-4 mr-2" />
                Test
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}