/**
 * TypeScript interfaces for Search Configuration
 * 
 * These interfaces match the API schemas from the backend
 * and provide type safety for the admin UI components.
 */

// ===============================
// Configuration Types
// ===============================

export interface QueueManagementConfig {
  max_queue_depth: number;
  overflow_strategy: 'reject' | 'evict_oldest';
  priority_levels: number;
  stale_timeout_seconds: number;
}

export interface RateLimitingConfig {
  per_user_rate_limit: number;
  global_rate_limit: number;
  burst_size: number;
  rate_limit_window_seconds: number;
}

export interface TimeoutConfig {
  search_timeout_seconds: number;
  ai_timeout_seconds: number;
  provider_timeout_seconds: number;
  cache_ttl_seconds: number;
}

export interface PerformanceThresholds {
  max_search_latency_ms: number;
  max_ai_latency_ms: number;
  min_cache_hit_rate: number;
  max_error_rate: number;
}

export interface ResourceLimits {
  max_concurrent_searches: number;
  max_ai_calls_per_minute: number;
  max_provider_calls_per_minute: number;
  max_cache_size_mb: number;
}

export interface FeatureToggles {
  enable_external_search: boolean;
  enable_ai_evaluation: boolean;
  enable_query_refinement: boolean;
  enable_knowledge_ingestion: boolean;
  enable_result_caching: boolean;
}

export interface AdvancedSettings {
  workspace_selection_strategy: string;
  result_ranking_algorithm: string;
  external_provider_priority: string[];
}

export interface SearchConfiguration {
  queue_management: QueueManagementConfig;
  rate_limiting: RateLimitingConfig;
  timeouts: TimeoutConfig;
  performance_thresholds: PerformanceThresholds;
  resource_limits: ResourceLimits;
  feature_toggles: FeatureToggles;
  advanced_settings: AdvancedSettings;
  last_updated: string;
  version: string;
}

// ===============================
// Vector Search Types
// ===============================

export interface VectorConnectionConfig {
  base_url: string;
  api_key?: string;
  timeout_seconds: number;
  max_retries: number;
  verify_ssl: boolean;
}

export interface VectorConnectionStatus {
  connected: boolean;
  endpoint: string;
  version?: string;
  workspaces_count: number;
  last_check: string;
  error?: string;
}

export interface WorkspaceConfig {
  id: string;
  name: string;
  slug: string;
  description: string;
  technologies: string[];
  tags: string[];
  priority: number;
  active: boolean;
  search_settings: Record<string, any>;
}

// ===============================
// Text AI Types
// ===============================

export interface TextAIModelConfig {
  provider: string;
  model: string;
  api_key: string;
  base_url?: string;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  custom_parameters: Record<string, any>;
}

export interface TextAIStatus {
  connected: boolean;
  provider: string;
  model: string;
  available: boolean;
  last_check: string;
  error?: string;
  usage_today?: {
    requests: number;
    tokens: number;
    cost_usd: number;
  };
}

export interface PromptTemplate {
  id: string;
  name: string;
  type: string;
  version: string;
  template: string;
  variables: string[];
  active: boolean;
  performance_metrics?: {
    avg_latency_ms: number;
    success_rate: number;
  };
  last_updated: string;
}

export interface ABTest {
  id: string;
  prompt_type: string;
  status: 'running' | 'completed' | 'paused';
  variants: Array<{
    id: string;
    version: string;
    traffic: number;
  }>;
  metrics: Record<string, {
    success_rate: number;
    avg_latency: number;
  }>;
  significance: number;
  started_at: string;
}

// ===============================
// Provider Types
// ===============================

export interface ProviderConfig {
  id: string;
  type: string;
  name: string;
  enabled: boolean;
  priority: number;
  config: Record<string, any>;
  rate_limits?: {
    requests_per_minute: number;
    requests_per_day: number;
  };
  cost_limits?: {
    monthly_budget_usd: number;
    cost_per_request: number;
  };
}

export interface ProviderStatus {
  id: string;
  name: string;
  type: string;
  enabled: boolean;
  health: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  latency_ms?: number;
  error_rate: number;
  last_check: string;
  circuit_breaker_state: 'open' | 'closed' | 'half_open';
  rate_limit_remaining?: number;
}

// ===============================
// Monitoring Types
// ===============================

export interface SearchMetrics {
  time_range: string;
  total_searches: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  cache_hit_rate: number;
  error_rate: number;
  searches_by_hour: Array<{
    hour: string;
    count: number;
    avg_latency: number;
  }>;
  top_queries: Array<{
    query: string;
    count: number;
    avg_latency: number;
  }>;
}

export interface QueueMetrics {
  current_depth: number;
  max_depth: number;
  avg_wait_time_ms: number;
  overflow_count: number;
  processing_rate: number;
  depth_history: Array<{
    timestamp: string;
    depth: number;
    processing_rate: number;
  }>;
}

export interface AlertConfig {
  id: string;
  name: string;
  type: string;
  condition: Record<string, any>;
  severity: 'low' | 'medium' | 'high' | 'critical';
  enabled: boolean;
  notification_channels: string[];
  cooldown_minutes: number;
}

export interface ActiveAlert {
  id: string;
  alert_config_id: string;
  name: string;
  severity: string;
  triggered_at: string;
  details: Record<string, any>;
  acknowledged: boolean;
  acknowledged_by?: string;
}

// ===============================
// Form and UI Types
// ===============================

export interface ConfigFormState {
  isDirty: boolean;
  isSubmitting: boolean;
  errors: Record<string, string>;
  touched: Record<string, boolean>;
}

export interface TabConfig {
  id: string;
  label: string;
  icon: string;
  shortcut?: string;
  badge?: number | string;
}

// ===============================
// WebSocket Types
// ===============================

export interface WebSocketMessage {
  type: 'config_update' | 'health_update' | 'metrics_update' | 'alert';
  payload: any;
  timestamp: string;
}

export interface HealthUpdate {
  component: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  message?: string;
  details?: Record<string, any>;
}

export interface MetricsUpdate {
  metric: string;
  value: number;
  timestamp: string;
  tags?: Record<string, string>;
}

// ===============================
// API Response Types
// ===============================

export interface APIResponse {
  success: boolean;
  message?: string;
  data?: any;
  errors?: string[];
}

export interface ConfigChangeLog {
  id: string;
  timestamp: string;
  user: string;
  section: string;
  changes: Record<string, any>;
  previous_values: Record<string, any>;
  comment?: string;
}

// ===============================
// Component Prop Types
// ===============================

export interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  trend?: 'up' | 'down' | 'stable';
  loading?: boolean;
  error?: string;
  icon?: React.ReactNode;
}

export interface HealthIndicatorProps {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown';
  label?: string;
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  pulse?: boolean;
}

export interface ConfigurationFormProps {
  initialValues: any;
  onSubmit: (values: any) => Promise<void>;
  onChange?: (values: any) => void;
  validationSchema?: any;
  disabled?: boolean;
}

export interface ProviderCardProps {
  provider: ProviderStatus;
  config?: ProviderConfig;
  onConfigure?: () => void;
  onTest?: () => void;
  onToggle?: (enabled: boolean) => void;
  draggable?: boolean;
}