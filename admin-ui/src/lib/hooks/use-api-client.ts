import { useContext, createContext } from 'react';
import { DocaicheApiClient } from '@/lib/utils/api-client';

const ApiClientContext = createContext<DocaicheApiClient | null>(null);

export function useApiClient() {
  const client = useContext(ApiClientContext);
  if (!client) {
    throw new Error('useApiClient must be used within ApiClientProvider');
  }
  return client;
}

export { ApiClientContext };