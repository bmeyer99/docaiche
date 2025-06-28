/**
 * Centralized API Configuration for Docaiche Admin Interface
 * 
 * This file contains all API-related configuration including
 * base URLs, timeouts, retry logic, and endpoint definitions.
 */

// API Configuration Constants
export const API_CONFIG = {
  // Base URL from environment variable with fallback
  BASE_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:4080/api/v1',
  
  // Request timeouts (in milliseconds)
  TIMEOUTS: {
    DEFAULT: 10000,      // 10 seconds
    UPLOAD: 60000,       // 1 minute for file uploads
    HEALTH_CHECK: 5000,  // 5 seconds for health checks
    CONNECTION_TEST: 8000 // 8 seconds for provider connection tests
  },
  
  // Retry configuration
  RETRY: {
    MAX_ATTEMPTS: 3,
    DELAY_MS: 1000,
    BACKOFF_MULTIPLIER: 2
  },
  
  // Request headers
  HEADERS: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Client': 'docaiche-admin-ui'
  }
} as const;

// API Endpoints
export const API_ENDPOINTS = {
  // Configuration Management
  CONFIG: {
    GET: '/config',
    UPDATE: '/config'
  },
  
  // System Monitoring
  HEALTH: '/health',
  STATS: '/stats',
  COLLECTIONS: '/collections',
  
  // Content Management
  CONTENT: {
    SEARCH: '/admin/search-content',
    UPLOAD: '/upload',
    DELETE: (contentId: string) => `/content/${contentId}`
  },
  
  // Feedback & Signals
  FEEDBACK: '/feedback',
  SIGNALS: '/signals'
} as const;

// API Response Types based on api-simplified.yaml
export interface ApiResponse<T = any> {
  data?: T;
  error?: {
    type: string;
    title: string;
    status: number;
    detail: string;
    instance?: string;
    error_code?: string;
    trace_id?: string;
  };
}

// Configuration Response Types
export interface ConfigurationItem {
  key: string;
  value: any;
  schema_version?: string;
  description?: string;
  is_sensitive?: boolean;
}

export interface ConfigurationResponse {
  items: ConfigurationItem[];
  timestamp: string;
}

export interface ConfigurationUpdateRequest {
  key: string;
  value: any;
  description?: string;
}

// Health Response Types
export interface HealthStatus {
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  response_time_ms?: number;
  last_check: string;
  details?: Record<string, any>;
}

export interface HealthResponse {
  overall_status: 'healthy' | 'degraded' | 'unhealthy';
  services: HealthStatus[];
  timestamp: string;
}

// Stats Response Types
export interface StatsResponse {
  search_stats: Record<string, any>;
  cache_stats: Record<string, any>;
  content_stats: Record<string, any>;
  system_stats: Record<string, any>;
  timestamp: string;
}

// Collection Types
export interface Collection {
  slug: string;
  name: string;
  technology: string;
  document_count: number;
  last_updated: string;
  is_active: boolean;
}

export interface CollectionsResponse {
  collections: Collection[];
  total_count: number;
}

// Admin Content Types
export interface AdminContentItem {
  content_id: string;
  title: string;
  content_type: string;
  technology?: string;
  source_url?: string;
  collection_name: string;
  created_at: string;
  last_updated: string;
  size_bytes?: number;
  status: 'active' | 'flagged' | 'removed';
}

export interface AdminSearchParams {
  search_term?: string;
  content_type?: string;
  technology?: string;
  status?: 'active' | 'flagged' | 'removed';
  limit?: number;
  offset?: number;
}

export interface AdminSearchResponse {
  items: AdminContentItem[];
  total_count: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

// Upload Response Types
export interface UploadResponse {
  upload_id: string;
  status: 'accepted' | 'processing' | 'completed' | 'failed';
  message?: string;
}

// Error Types based on RFC 7807 Problem Details
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  error_code?: string;
  trace_id?: string;
}

// Provider-specific types for AI configuration
export interface ProviderConfig {
  provider: string;
  base_url: string;
  api_key?: string;
  model?: string;
  parameters?: Record<string, any>;
}

// Status check helper
export const isHealthy = (status: HealthStatus['status']): boolean => {
  return status === 'healthy';
};

export const isDegraded = (status: HealthStatus['status']): boolean => {
  return status === 'degraded';
};

export const isUnhealthy = (status: HealthStatus['status']): boolean => {
  return status === 'unhealthy';
};

// HTTP Status Codes
export const HTTP_STATUS = {
  OK: 200,
  CREATED: 201,
  ACCEPTED: 202,
  NO_CONTENT: 204,
  BAD_REQUEST: 400,
  UNAUTHORIZED: 401,
  FORBIDDEN: 403,
  NOT_FOUND: 404,
  CONFLICT: 409,
  PAYLOAD_TOO_LARGE: 413,
  UNPROCESSABLE_ENTITY: 422,
  TOO_MANY_REQUESTS: 429,
  INTERNAL_SERVER_ERROR: 500,
  BAD_GATEWAY: 502,
  SERVICE_UNAVAILABLE: 503
} as const;