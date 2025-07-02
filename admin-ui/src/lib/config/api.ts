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
    CONNECTION_TEST: 30000 // 30 seconds for provider connection tests
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
  SIGNALS: '/signals',
  
  // MCP (Model Context Protocol) Management
  MCP: {
    PROVIDERS: '/mcp/providers',
    PROVIDER: (id: string) => `/mcp/providers/${id}`,
    CONFIG: '/mcp/config',
    SEARCH: '/mcp/search',
    STATS: '/mcp/stats'
  }
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
  value: string | number | boolean | Record<string, unknown> | unknown[];
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
  value: string | number | boolean | Record<string, unknown> | unknown[];
  description?: string;
}

// Health Response Types
export interface HealthStatus {
  service: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  response_time_ms?: number;
  last_check: string;
  details?: Record<string, unknown>;
}

export interface HealthResponse {
  overall_status: 'healthy' | 'degraded' | 'unhealthy';
  services: HealthStatus[];
  timestamp: string;
}

// Stats Response Types
export interface StatsResponse {
  search_stats: Record<string, number | string>;
  cache_stats: Record<string, number | string>;
  content_stats: Record<string, number | string>;
  system_stats: Record<string, number | string>;
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

// Activity Types
export interface ActivityItem {
  id: string;
  type: 'search' | 'index' | 'config' | 'error';
  message: string;
  timestamp: string;
  details?: string;
  user_id?: string;
  metadata?: Record<string, unknown>;
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

// MCP (Model Context Protocol) Types
export interface MCPProviderConfig {
  provider_id: string;
  provider_type: string;
  enabled: boolean;
  api_key?: string;
  api_endpoint?: string;
  priority: number;
  max_results: number;
  timeout_seconds: number;
  rate_limit_per_minute: number;
  custom_headers: Record<string, string>;
  custom_params: Record<string, any>;
}

export interface MCPProviderCapability {
  feature: string;
  supported: boolean;
  description: string;
}

export interface MCPProviderHealth {
  provider_id: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  last_check: string;
  response_time_ms?: number;
  error_message?: string;
  success_rate?: number;
}

export interface MCPProviderStats {
  provider_id: string;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  avg_response_time_ms: number;
  last_24h_requests: number;
  circuit_breaker_open: boolean;
}

export interface MCPProvider {
  provider_id: string;
  config: MCPProviderConfig;
  capabilities: MCPProviderCapability[];
  health: MCPProviderHealth;
  stats: MCPProviderStats;
}

export interface MCPProvidersResponse {
  providers: MCPProvider[];
  total_count: number;
  healthy_count: number;
}

export interface MCPSearchConfig {
  enable_external_search: boolean;
  enable_hedged_requests: boolean;
  hedged_delay_seconds: number;
  max_concurrent_providers: number;
  external_search_threshold: number;
  cache_ttl_seconds: number;
  enable_performance_monitoring: boolean;
}

export interface MCPCacheConfig {
  l1_cache_size: number;
  l2_cache_ttl: number;
  compression_threshold: number;
  enable_compression: boolean;
  enable_stats: boolean;
}

export interface MCPConfigResponse {
  config: MCPSearchConfig;
  cache_config: MCPCacheConfig;
  last_updated: string;
}

export interface MCPPerformanceStats {
  total_searches: number;
  cache_hits: number;
  cache_misses: number;
  avg_response_time_ms: number;
  hedged_requests: number;
  circuit_breaks: number;
  provider_stats: MCPProviderStats[];
}

export interface MCPStatsResponse {
  stats: MCPPerformanceStats;
  collection_period_hours: number;
  last_reset: string;
}

export interface MCPExternalSearchRequest {
  query: string;
  technology_hint?: string;
  max_results: number;
  provider_ids?: string[];
  force_external: boolean;
}

export interface MCPExternalSearchResult {
  title: string;
  url: string;
  snippet: string;
  provider: string;
  content_type: string;
  published_date?: string;
  relevance_score?: number;
}

export interface MCPExternalSearchResponse {
  results: MCPExternalSearchResult[];
  total_results: number;
  providers_used: string[];
  execution_time_ms: number;
  cache_hit: boolean;
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