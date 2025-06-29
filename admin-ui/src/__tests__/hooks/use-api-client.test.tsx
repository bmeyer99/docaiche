import { renderHook } from '@testing-library/react';
import { ReactNode } from 'react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { ApiClientProvider } from '@/components/providers/api-client-provider';

describe('useApiClient', () => {
  it('should throw error when used outside provider', () => {
    // Suppress console.error for this test
    // eslint-disable-next-line no-console
    const originalError = console.error;
    // eslint-disable-next-line no-console
    console.error = jest.fn();

    expect(() => {
      renderHook(() => useApiClient());
    }).toThrow('useApiClient must be used within ApiClientProvider');

    // eslint-disable-next-line no-console
    console.error = originalError;
  });

  it('should return api client when used within provider', () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <ApiClientProvider>{children}</ApiClientProvider>
    );

    const { result } = renderHook(() => useApiClient(), { wrapper });

    expect(result.current).toBeDefined();
    expect(result.current.getHealth).toBeDefined();
    expect(result.current.searchContent).toBeDefined();
  });

  it('should return the same instance on multiple calls', () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <ApiClientProvider>{children}</ApiClientProvider>
    );

    const { result: result1 } = renderHook(() => useApiClient(), { wrapper });
    const { result: result2 } = renderHook(() => useApiClient(), { wrapper });

    expect(result1.current).toBe(result2.current);
  });
});