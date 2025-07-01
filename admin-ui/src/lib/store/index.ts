/**
 * Global State Store
 * Enterprise-grade state management for DocAIche Admin UI
 */

import { create } from 'zustand';
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { ProviderConfiguration, ModelSelection, UserPreferences, Notification } from './types';

// Store slices
import { createProviderSlice, ProviderSlice } from './slices/provider-slice';
import { createSystemSlice, SystemSlice } from './slices/system-slice';
import { createUserSlice, UserSlice } from './slices/user-slice';
import { createUISlice, UISlice } from './slices/ui-slice';
import { createRealtimeSlice, RealtimeSlice } from './slices/realtime-slice';

// Import AppStore type from shared types
import type { AppStore } from './store-types';

// Create the main store with proper typing
export const useAppStore = create<AppStore>()(
  devtools(
    persist(
      subscribeWithSelector(
        immer<AppStore>((set, get, api) => ({
          // Combine all slices
          ...createProviderSlice(set, get, api),
          ...createSystemSlice(set, get, api),
          ...createUserSlice(set, get, api),
          ...createUISlice(set, get, api),
          ...createRealtimeSlice(set, get, api),
        }))
      ),
      {
        name: 'docaiche-store',
        // Only persist specific parts of the state
        partialize: (state) => ({
          user: state.user,
          ui: {
            sidebar: state.ui?.sidebar,
          },
          providers: {
            modelSelection: state.providers?.modelSelection,
          },
        }),
        // Custom storage for different data types
        storage: {
          getItem: (name) => {
            const item = localStorage.getItem(name);
            return item ? JSON.parse(item) : null;
          },
          setItem: (name, value) => {
            localStorage.setItem(name, JSON.stringify(value));
          },
          removeItem: (name) => {
            localStorage.removeItem(name);
          },
        },
      }
    ),
    {
      name: 'DocAIche Admin Store',
      // Enable Redux DevTools
      enabled: process.env.NODE_ENV === 'development',
    }
  )
);

// Convenience selectors
export const useProviders = () => useAppStore((state) => state.providers);
export const useSystem = () => useAppStore((state) => state.system);
export const useUser = () => useAppStore((state) => state.user);
export const useUI = () => useAppStore((state) => state.ui);
export const useRealtime = () => useAppStore((state) => state.realtime);

// Specific selectors for common use cases
export const useProviderConfiguration = (providerId: string) => 
  useAppStore((state) => state.providers.configurations[providerId]);

export const useProviderTestStatus = (providerId: string) => 
  useAppStore((state) => state.providers.configurations[providerId]?.testStatus);

export const useModelSelection = () => 
  useAppStore((state) => state.providers.modelSelection);

export const useSystemHealth = () => 
  useAppStore((state) => state.system.health);

export const useNotifications = () => 
  useAppStore((state) => state.ui.notifications);

export const useTheme = () => 
  useAppStore((state) => state.user.preferences.theme);

// Actions (exported for external use)
export const {
  // Provider actions
  setProviderConfiguration,
  updateProviderTestStatus,
  setProviderTestResults,
  updateModelSelection,
  
  // System actions
  updateSystemHealth,
  updateMetrics,
  addLogEntry,
  
  // User actions
  updateUserPreferences,
  
  // UI actions
  toggleSidebar,
  setSidebarCollapsed,
  openModal,
  closeModal,
  setLoading,
  clearError,
  addNotification,
  removeNotification,
  markNotificationRead,
  
  // Realtime actions
  setRealtimeConnected,
  updateRealtimeMetrics,
} = useAppStore.getState();

// Store utilities
export const getStoreSnapshot = () => useAppStore.getState();
export const resetStore = () => useAppStore.setState({} as AppStore, true);

// Type exports
export type { ProviderConfiguration, ModelSelection, UserPreferences, Notification };
export * from './types';