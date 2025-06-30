/**
 * Performance-related React components
 * These components use JSX and should be in a .tsx file
 */

import React, { ReactNode, useCallback } from 'react';

// ========================== PROFILER COMPONENTS ==========================

/**
 * Profiler wrapper component for measuring component performance
 */
export function ProfilerWrapper({ 
  id, 
  children,
  onRender
}: {
  id: string;
  children: ReactNode;
  onRender?: (id: string, phase: 'mount' | 'update', actualDuration: number) => void;
}) {
  // Development logging for profiler data
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const _logPerformanceData = useCallback(
    (id: string, phase: 'mount' | 'update', actualDuration: number) => {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Profiler] ${id} ${phase} took ${actualDuration.toFixed(2)}ms`);
      }
      onRender?.(id, phase, actualDuration);
    },
    [onRender]
  );

  // Only render Profiler in development
  if (process.env.NODE_ENV === 'development') {
    return (
      <div data-profiler-id={id}>
        {children}
      </div>
    );
  }

  return <>{children}</>;
}

/**
 * Performance monitoring wrapper for expensive components
 */
export function PerformanceWrapper({
  componentName,
  children,
  enableProfiling = process.env.NODE_ENV === 'development'
}: {
  componentName: string;
  children: ReactNode;
  enableProfiling?: boolean;
}) {
  if (!enableProfiling) {
    return <>{children}</>;
  }

  return (
    <ProfilerWrapper 
      id={componentName}
      onRender={(id, phase, actualDuration) => {
        if (actualDuration > 16) { // More than one frame at 60fps
          console.warn(`[Performance] ${id} took ${actualDuration.toFixed(2)}ms in ${phase} phase`);
        }
      }}
    >
      {children}
    </ProfilerWrapper>
  );
}