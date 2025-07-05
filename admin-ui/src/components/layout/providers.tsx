'use client';
import React from 'react';
import { ActiveThemeProvider } from '../active-theme';
import { ApiClientProvider } from '@/components/providers/api-client-provider';
import { BrowserLoggerProvider } from '@/components/providers/browser-logger-provider';
import { ProviderSettingsProvider } from '@/lib/hooks/use-provider-settings';
import { AnalyticsProvider } from '@/providers/analytics-provider';

export default function Providers({
  activeThemeValue,
  children
}: {
  activeThemeValue: string;
  children: React.ReactNode;
}) {
  return (
    <>
      <ActiveThemeProvider initialTheme={activeThemeValue}>
        <ApiClientProvider>
          <BrowserLoggerProvider>
            <ProviderSettingsProvider>
              <AnalyticsProvider>
                {children}
              </AnalyticsProvider>
            </ProviderSettingsProvider>
          </BrowserLoggerProvider>
        </ApiClientProvider>
      </ActiveThemeProvider>
    </>
  );
}
