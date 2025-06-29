'use client';
import React from 'react';
import { ActiveThemeProvider } from '../active-theme';
import { ApiClientProvider } from '@/components/providers/api-client-provider';

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
          {children}
        </ApiClientProvider>
      </ActiveThemeProvider>
    </>
  );
}
