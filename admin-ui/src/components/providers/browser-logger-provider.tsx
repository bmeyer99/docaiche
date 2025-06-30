'use client';

import { useEffect } from 'react';
import { browserLogger } from '@/lib/utils/browser-logger';

export function BrowserLoggerProvider({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize browser logging
    browserLogger.info('DocAIche Admin UI initialized', {
      timestamp: new Date().toISOString(),
      page: window.location.pathname
    });

    // Log navigation changes
    const handleNavigation = () => {
      browserLogger.info('Navigation', {
        url: window.location.href,
        pathname: window.location.pathname
      });
    };

    window.addEventListener('popstate', handleNavigation);
    
    return () => {
      window.removeEventListener('popstate', handleNavigation);
    };
  }, []);

  return <>{children}</>;
}