/**
 * Global State Management Types
 * Comprehensive type definitions for all application state
 */

// ============= PROVIDER STATE =============
export interface ProviderConfiguration {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  configured: boolean;
  config: {
    base_url?: string;
    api_key?: string;
    [key: string]: any;
  };
  // New: Test tracking
  testStatus: 'untested' | 'testing' | 'tested' | 'failed';
  testResults?: {
    lastTested: Date;
    success: boolean;
    models: string[];
    error?: string;
  };
}

export interface ModelSelection {
  textGeneration: {
    provider: string;
    model: string;
  };
  embeddings: {
    provider: string;
    model: string;
  };
  sharedProvider: boolean;
}

// ============= SYSTEM STATE =============
export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    api: ServiceStatus;
    database: ServiceStatus;
    redis: ServiceStatus;
    anythingllm: ServiceStatus;
    monitoring: ServiceStatus;
  };
  lastCheck: Date;
}

export interface ServiceStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency?: number;
  error?: string;
}

// ============= USER STATE =============
export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notifications: {
    enabled: boolean;
    types: string[];
  };
  dashboard: {
    layout: 'compact' | 'standard' | 'detailed';
    refreshInterval: number;
  };
}

// ============= UI STATE =============
export interface UIState {
  // Global UI state
  sidebar: {
    collapsed: boolean;
    activeItem: string;
  };
  modals: {
    [key: string]: boolean;
  };
  loading: {
    [key: string]: boolean;
  };
  errors: {
    [key: string]: string | null;
  };
  notifications: Notification[];
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  actions?: NotificationAction[];
}

export interface NotificationAction {
  label: string;
  action: () => void;
}

// ============= REAL-TIME STATE =============
export interface RealtimeMetrics {
  systemLoad: {
    cpu: number;
    memory: number;
    disk: number;
  };
  apiMetrics: {
    requestsPerSecond: number;
    averageResponseTime: number;
    errorRate: number;
  };
  activeConnections: number;
  lastUpdate: Date;
}

export interface LogEntry {
  timestamp: Date;
  level: 'debug' | 'info' | 'warn' | 'error';
  service: string;
  message: string;
  metadata?: Record<string, any>;
}

// ============= CUSTOMER STATE (Future) =============
export interface Customer {
  id: string;
  name: string;
  plan: 'free' | 'pro' | 'enterprise';
  usage: {
    documentsProcessed: number;
    apiCalls: number;
    storageUsed: number;
  };
  limits: {
    maxDocuments: number;
    maxApiCalls: number;
    maxStorage: number;
  };
}

// ============= APPLICATION STATE =============
export interface AppState {
  // Core application state
  providers: {
    configurations: Record<string, ProviderConfiguration>;
    modelSelection: ModelSelection;
    loading: boolean;
    error: string | null;
  };
  
  system: {
    health: SystemHealth;
    metrics: RealtimeMetrics;
    logs: LogEntry[];
    loading: boolean;
    error: string | null;
  };
  
  user: {
    preferences: UserPreferences;
    loading: boolean;
    error: string | null;
  };
  
  ui: UIState;
  
  // Future: Customer management
  customers?: {
    list: Customer[];
    selected: Customer | null;
    loading: boolean;
    error: string | null;
  };
  
  // WebSocket connection state
  realtime: {
    connected: boolean;
    reconnecting: boolean;
    lastHeartbeat: Date | null;
  };
}