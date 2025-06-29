/**
 * App Store Hook
 * Convenience hook for accessing the global application store
 */

import { useAppStore } from '../store';

/**
 * Simple hook that provides direct access to the store
 * Use this to access any store state or actions directly
 */
export function useAppStoreState() {
  return useAppStore();
}

/**
 * Hook for accessing common store patterns
 * This provides the most commonly used store functionality
 */
export function useAppStoreCommon() {
  const store = useAppStore();
  
  return {
    // State
    providers: store.providers,
    system: store.system,
    user: store.user,
    ui: store.ui,
    realtime: store.realtime,
    
    // Most common actions that are definitely available
    setSidebarCollapsed: store.setSidebarCollapsed,
    
    // Store itself for any custom access
    store,
  };
}