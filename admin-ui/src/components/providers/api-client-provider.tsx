'use client';

import { useMemo } from 'react';
import { DocaicheApiClient } from '@/lib/utils/api-client';
import { ApiClientContext } from '@/lib/hooks/use-api-client';

interface ApiClientProviderProps {
  children: React.ReactNode;
}

export function ApiClientProvider({ children }: ApiClientProviderProps) {
  const client = useMemo(() => new DocaicheApiClient(), []);
  
  return (
    <ApiClientContext.Provider value={client}>
      {children}
    </ApiClientContext.Provider>
  );
}