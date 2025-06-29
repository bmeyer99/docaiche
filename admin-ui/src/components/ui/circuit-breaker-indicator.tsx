/**
 * Circuit Breaker Status Indicator Component
 * 
 * Shows visual feedback about circuit breaker state in the UI
 */

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Icons } from '@/components/icons';
import { useCircuitBreaker } from '@/lib/hooks/use-circuit-breaker';

interface CircuitBreakerIndicatorProps {
  identifier: string;
  onReset?: () => void;
  showDetails?: boolean;
}

export function CircuitBreakerIndicator({ 
  identifier, 
  onReset,
  showDetails = false 
}: CircuitBreakerIndicatorProps) {
  const circuitBreaker = useCircuitBreaker(identifier);
  const [timeToReset, setTimeToReset] = useState<number>(0);

  useEffect(() => {
    if (!circuitBreaker.isCircuitOpen) return;

    const interval = setInterval(() => {
      const timeSinceFailure = circuitBreaker.getTimeSinceLastFailure();
      const remaining = Math.max(0, 30000 - timeSinceFailure); // 30 seconds reset time
      setTimeToReset(Math.ceil(remaining / 1000));
      
      if (remaining === 0) {
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [circuitBreaker.isCircuitOpen, circuitBreaker]);

  const state = circuitBreaker.getCircuitState();
  
  if (state === 'CLOSED' && !showDetails) {
    return null; // Don't show indicator when everything is working
  }

  const getStateColor = (state: string) => {
    switch (state) {
      case 'CLOSED': return 'bg-green-100 text-green-800 border-green-200';
      case 'HALF_OPEN': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'OPEN': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStateIcon = (state: string) => {
    switch (state) {
      case 'CLOSED': return <Icons.checkCircle className="w-4 h-4" />;
      case 'HALF_OPEN': return <Icons.clock className="w-4 h-4" />;
      case 'OPEN': return <Icons.alertCircle className="w-4 h-4" />;
      default: return <Icons.circle className="w-4 h-4" />;
    }
  };

  return (
    <Card className="border-l-4 border-l-red-500">
      <CardContent className="pt-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Badge className={getStateColor(state)}>
              <div className="flex items-center gap-1">
                {getStateIcon(state)}
                <span className="font-medium">{state}</span>
              </div>
            </Badge>
            <div>
              <div className="font-medium text-sm">
                {identifier.replace('-api', '').toUpperCase()} API Status
              </div>
              <div className="text-xs text-muted-foreground">
                {state === 'OPEN' && `Retry in ${timeToReset}s`}
                {state === 'HALF_OPEN' && 'Testing connection...'}
                {state === 'CLOSED' && 'Connection healthy'}
              </div>
            </div>
          </div>
          
          {state === 'OPEN' && onReset && (
            <Button 
              size="sm" 
              variant="outline"
              onClick={() => {
                circuitBreaker.resetCircuit();
                onReset();
              }}
            >
              <Icons.arrowRight className="w-3 h-3 mr-1" />
              Reset
            </Button>
          )}
        </div>
        
        {showDetails && (
          <div className="mt-3 text-xs text-muted-foreground">
            <div>Identifier: {identifier}</div>
            <div>Time since last failure: {Math.floor(circuitBreaker.getTimeSinceLastFailure() / 1000)}s</div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}