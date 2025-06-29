/**
 * UI State Slice
 * Manages global UI state including modals, loading states, and notifications
 */

import { StateCreator } from 'zustand';
import { UIState, Notification, NotificationAction } from '../types';

export interface UISliceState {
  ui: UIState;
}

export interface UIActions {
  // Sidebar actions
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setSidebarActiveItem: (item: string) => void;
  
  // Modal actions
  openModal: (modalId: string) => void;
  closeModal: (modalId: string) => void;
  closeAllModals: () => void;
  isModalOpen: (modalId: string) => boolean;
  
  // Loading actions
  setLoading: (key: string, loading: boolean) => void;
  clearAllLoading: () => void;
  isLoading: (key: string) => boolean;
  
  // Error actions
  setError: (key: string, error: string | null) => void;
  clearError: (key: string) => void;
  clearAllErrors: () => void;
  getError: (key: string) => string | null;
  
  // Notification actions
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp' | 'read'>) => string;
  removeNotification: (id: string) => void;
  markNotificationRead: (id: string) => void;
  markAllNotificationsRead: () => void;
  clearNotifications: () => void;
  clearReadNotifications: () => void;
  
  // Computed selectors
  getUnreadNotifications: () => Notification[];
  getNotificationCount: () => number;
  getUnreadNotificationCount: () => number;
  hasErrors: () => boolean;
  isAnyLoading: () => boolean;
}

export type UISlice = UISliceState & UIActions;

// Default state
const defaultUIState: UIState = {
  sidebar: {
    collapsed: false,
    activeItem: 'dashboard',
  },
  modals: {},
  loading: {},
  errors: {},
  notifications: [],
};

// Utility function to generate notification IDs
const generateNotificationId = () => {
  return `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const createUISlice: StateCreator<
  UISlice,
  [["zustand/immer", never]],
  [],
  UISlice
> = (set, get) => ({
  ui: defaultUIState,

  // Sidebar actions
  toggleSidebar: () =>
    set((state) => {
      state.ui.sidebar.collapsed = !state.ui.sidebar.collapsed;
    }),

  setSidebarCollapsed: (collapsed) =>
    set((state) => {
      state.ui.sidebar.collapsed = collapsed;
    }),

  setSidebarActiveItem: (item) =>
    set((state) => {
      state.ui.sidebar.activeItem = item;
    }),

  // Modal actions
  openModal: (modalId) =>
    set((state) => {
      state.ui.modals[modalId] = true;
    }),

  closeModal: (modalId) =>
    set((state) => {
      state.ui.modals[modalId] = false;
    }),

  closeAllModals: () =>
    set((state) => {
      Object.keys(state.ui.modals).forEach(modalId => {
        state.ui.modals[modalId] = false;
      });
    }),

  isModalOpen: (modalId) => {
    const state = get();
    return state.ui.modals[modalId] || false;
  },

  // Loading actions
  setLoading: (key, loading) =>
    set((state) => {
      if (loading) {
        state.ui.loading[key] = true;
      } else {
        delete state.ui.loading[key];
      }
    }),

  clearAllLoading: () =>
    set((state) => {
      state.ui.loading = {};
    }),

  isLoading: (key) => {
    const state = get();
    return state.ui.loading[key] || false;
  },

  // Error actions
  setError: (key, error) =>
    set((state) => {
      if (error) {
        state.ui.errors[key] = error;
      } else {
        delete state.ui.errors[key];
      }
    }),

  clearError: (key) =>
    set((state) => {
      delete state.ui.errors[key];
    }),

  clearAllErrors: () =>
    set((state) => {
      state.ui.errors = {};
    }),

  getError: (key) => {
    const state = get();
    return state.ui.errors[key] || null;
  },

  // Notification actions
  addNotification: (notification) => {
    const id = generateNotificationId();
    
    set((state) => {
      const newNotification: Notification = {
        ...notification,
        id,
        timestamp: new Date(),
        read: false,
      };
      
      // Add to beginning of array (newest first)
      state.ui.notifications.unshift(newNotification);
      
      // Limit to 100 notifications
      if (state.ui.notifications.length > 100) {
        state.ui.notifications = state.ui.notifications.slice(0, 100);
      }
    });
    
    return id;
  },

  removeNotification: (id) =>
    set((state) => {
      state.ui.notifications = state.ui.notifications.filter((n: Notification) => n.id !== id);
    }),

  markNotificationRead: (id) =>
    set((state) => {
      const notification = state.ui.notifications.find((n: Notification) => n.id === id);
      if (notification) {
        notification.read = true;
      }
    }),

  markAllNotificationsRead: () =>
    set((state) => {
      state.ui.notifications.forEach((notification: Notification) => {
        notification.read = true;
      });
    }),

  clearNotifications: () =>
    set((state) => {
      state.ui.notifications = [];
    }),

  clearReadNotifications: () =>
    set((state) => {
      state.ui.notifications = state.ui.notifications.filter((n: Notification) => !n.read);
    }),

  // Computed selectors
  getUnreadNotifications: () => {
    const state = get();
    return state.ui.notifications.filter((n: Notification) => !n.read);
  },

  getNotificationCount: () => {
    const state = get();
    return state.ui.notifications.length;
  },

  getUnreadNotificationCount: () => {
    const state = get();
    return state.ui.notifications.filter((n: Notification) => !n.read).length;
  },

  hasErrors: () => {
    const state = get();
    return Object.keys(state.ui.errors).length > 0;
  },

  isAnyLoading: () => {
    const state = get();
    return Object.keys(state.ui.loading).length > 0;
  },
});