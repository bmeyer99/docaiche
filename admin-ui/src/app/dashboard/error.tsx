'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Icons } from '@/components/icons';

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error specific to dashboard
    if (process.env.NODE_ENV === 'production') {
      // Could send to error tracking service
    }
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-4">
      <Card className="max-w-md w-full">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <Icons.alertCircle className="h-10 w-10 text-destructive" />
          </div>
          <CardTitle>Dashboard Error</CardTitle>
          <CardDescription>
            We encountered an error while loading the dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {process.env.NODE_ENV === 'development' && (
            <div className="bg-muted p-3 rounded text-sm font-mono break-all max-h-32 overflow-auto">
              {error.message}
            </div>
          )}
          <div className="flex justify-center gap-3">
            <Button onClick={reset} size="sm">
              <Icons.arrowRight className="mr-2 h-4 w-4 rotate-180" />
              Retry
            </Button>
            <Button
              onClick={() => window.location.reload()}
              variant="outline"
              size="sm"
            >
              <Icons.arrowRight className="mr-2 h-4 w-4 rotate-180" />
              Refresh Page
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}