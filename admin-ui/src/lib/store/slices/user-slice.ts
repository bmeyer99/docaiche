/**
 * User State Slice
 * Manages user preferences and settings
 */

import { StateCreator } from 'zustand';
import { UserPreferences } from '../types';

export interface UserState {
  user: {
    preferences: UserPreferences;
    loading: boolean;
    error: string | null;
  };
}

export interface UserActions {
  // Preference actions
  updateUserPreferences: (preferences: Partial<UserPreferences>) => void;
  setTheme: (theme: UserPreferences['theme']) => void;
  setLanguage: (language: string) => void;
  updateNotificationSettings: (settings: Partial<UserPreferences['notifications']>) => void;
  updateDashboardSettings: (settings: Partial<UserPreferences['dashboard']>) => void;
  toggleNotifications: (enabled: boolean) => void;
  setNotificationTypes: (types: string[]) => void;
  setDashboardLayout: (layout: UserPreferences['dashboard']['layout']) => void;
  setRefreshInterval: (interval: number) => void;
  
  // Loading and error states
  setUserLoading: (loading: boolean) => void;
  setUserError: (error: string | null) => void;
  
  // Computed selectors
  getTheme: () => UserPreferences['theme'];
  areNotificationsEnabled: () => boolean;
  getDashboardLayout: () => UserPreferences['dashboard']['layout'];
  getRefreshInterval: () => number;
  
  // Preference helpers
  resetPreferences: () => void;
  exportPreferences: () => UserPreferences;
  importPreferences: (preferences: UserPreferences) => void;
}

export type UserSlice = UserState & UserActions;

// Default state
const defaultUserPreferences: UserPreferences = {
  theme: 'system',
  language: 'en',
  notifications: {
    enabled: true,
    types: ['system', 'provider', 'document', 'error'],
  },
  dashboard: {
    layout: 'standard',
    refreshInterval: 30000, // 30 seconds
  },
};

const defaultUserState: UserState['user'] = {
  preferences: defaultUserPreferences,
  loading: false,
  error: null,
};

export const createUserSlice: StateCreator<
  UserSlice,
  [["zustand/immer", never]],
  [],
  UserSlice
> = (set, get) => ({
  user: defaultUserState,

  // Preference actions
  updateUserPreferences: (preferences) =>
    set((state) => {
      Object.assign(state.user.preferences, preferences);
    }),

  setTheme: (theme) =>
    set((state) => {
      state.user.preferences.theme = theme;
    }),

  setLanguage: (language) =>
    set((state) => {
      state.user.preferences.language = language;
    }),

  updateNotificationSettings: (settings) =>
    set((state) => {
      Object.assign(state.user.preferences.notifications, settings);
    }),

  updateDashboardSettings: (settings) =>
    set((state) => {
      Object.assign(state.user.preferences.dashboard, settings);
    }),

  toggleNotifications: (enabled) =>
    set((state) => {
      state.user.preferences.notifications.enabled = enabled;
    }),

  setNotificationTypes: (types) =>
    set((state) => {
      state.user.preferences.notifications.types = types;
    }),

  setDashboardLayout: (layout) =>
    set((state) => {
      state.user.preferences.dashboard.layout = layout;
    }),

  setRefreshInterval: (interval) =>
    set((state) => {
      state.user.preferences.dashboard.refreshInterval = interval;
    }),

  // Loading and error states
  setUserLoading: (loading) =>
    set((state) => {
      state.user.loading = loading;
    }),

  setUserError: (error) =>
    set((state) => {
      state.user.error = error;
    }),

  // Computed selectors
  getTheme: () => {
    const state = get();
    return state.user.preferences.theme;
  },

  areNotificationsEnabled: () => {
    const state = get();
    return state.user.preferences.notifications.enabled;
  },

  getDashboardLayout: () => {
    const state = get();
    return state.user.preferences.dashboard.layout;
  },

  getRefreshInterval: () => {
    const state = get();
    return state.user.preferences.dashboard.refreshInterval;
  },

  // Preference helpers
  resetPreferences: () =>
    set((state) => {
      state.user.preferences = { ...defaultUserPreferences };
    }),

  exportPreferences: () => {
    const state = get();
    return { ...state.user.preferences };
  },

  importPreferences: (preferences) =>
    set((state) => {
      // Validate and merge with defaults to ensure all required fields exist
      state.user.preferences = {
        ...defaultUserPreferences,
        ...preferences,
        notifications: {
          ...defaultUserPreferences.notifications,
          ...preferences.notifications,
        },
        dashboard: {
          ...defaultUserPreferences.dashboard,
          ...preferences.dashboard,
        },
      };
    }),
});