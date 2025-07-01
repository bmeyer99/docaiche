# MCP Search System - Configuration Reference

## Overview

This document provides a comprehensive reference for all configuration options available in the MCP Search System. All settings can be configured through environment variables, configuration files, or the Admin UI.

## Configuration Hierarchy

Configuration is applied in the following order (highest priority first):

1. **Environment Variables** (highest priority)
2. **Configuration Files** (`config/production.yaml`)
3. **Database Settings** (Admin UI configured)
4. **Default Values** (lowest priority)

## Core System Configuration

### Database Configuration

```yaml
database:
  # Primary database connection
  url: "postgresql://user:password@localhost:5432/docaiche"
  pool_size: 10
  max_overflow: 20
  pool_timeout: 30
  pool_recycle: 3600
  
  # Connection retry settings
  retry_attempts: 3
  retry_delay: 5
  
  # Health check settings
  health_check_interval: 60
  health_check_timeout: 10
```

**Environment Variables:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/docaiche
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
DATABASE_RETRY_ATTEMPTS=3
DATABASE_RETRY_DELAY=5
DATABASE_HEALTH_CHECK_INTERVAL=60
DATABASE_HEALTH_CHECK_TIMEOUT=10
```

### Cache Configuration

```yaml
cache:
  # Redis L2 cache configuration
  redis:
    url: "redis://localhost:6379/0"
    connection_pool_size: 10
    socket_timeout: 30
    socket_connect_timeout: 30
    retry_on_timeout: true
    health_check_interval: 60
  
  # L1 in-memory cache configuration
  l1_cache:
    size: 1000
    ttl: 3600
    max_size_bytes: 104857600  # 100MB
    eviction_policy: "lru"
  
  # L2 Redis cache configuration
  l2_cache:
    ttl: 7200
    compression_threshold: 1024
    compression_algorithm: "gzip"
    key_prefix: "docaiche:mcp:"
  
  # Cache statistics
  enable_stats: true
  stats_interval: 300
```

**Environment Variables:**
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_CONNECTION_POOL_SIZE=10
REDIS_SOCKET_TIMEOUT=30
REDIS_SOCKET_CONNECT_TIMEOUT=30
REDIS_RETRY_ON_TIMEOUT=true
REDIS_HEALTH_CHECK_INTERVAL=60

MCP_L1_CACHE_SIZE=1000
MCP_L1_CACHE_TTL=3600
MCP_L1_CACHE_MAX_SIZE_BYTES=104857600
MCP_L1_CACHE_EVICTION_POLICY=lru

MCP_L2_CACHE_TTL=7200
MCP_L2_CACHE_COMPRESSION_THRESHOLD=1024
MCP_L2_CACHE_COMPRESSION_ALGORITHM=gzip
MCP_L2_CACHE_KEY_PREFIX=docaiche:mcp:

MCP_CACHE_ENABLE_STATS=true
MCP_CACHE_STATS_INTERVAL=300
```

## MCP External Search Configuration

### General External Search Settings

```yaml
mcp:
  external_search:
    # Enable/disable external search functionality
    enabled: true
    
    # Global external search settings
    max_concurrent_providers: 3
    default_timeout_seconds: 3.0
    max_results_per_provider: 10
    
    # Hedged request configuration
    enable_hedged_requests: true
    hedged_delay_seconds: 0.15
    hedged_max_concurrent: 2
    
    # Circuit breaker configuration
    circuit_breaker:
      failure_threshold: 5
      recovery_timeout: 300
      half_open_max_calls: 3
    
    # Rate limiting
    global_rate_limit_per_minute: 1000
    per_provider_rate_limit_per_minute: 200
    
    # Adaptive timeout configuration
    adaptive_timeouts:
      enabled: true
      min_timeout: 1.0
      max_timeout: 10.0
      percentile: 95
      adjustment_factor: 1.2
      learning_window: 100
```

**Environment Variables:**
```bash
MCP_EXTERNAL_SEARCH_ENABLED=true
MCP_MAX_CONCURRENT_PROVIDERS=3
MCP_DEFAULT_TIMEOUT_SECONDS=3.0
MCP_MAX_RESULTS_PER_PROVIDER=10

MCP_ENABLE_HEDGED_REQUESTS=true
MCP_HEDGED_DELAY_SECONDS=0.15
MCP_HEDGED_MAX_CONCURRENT=2

MCP_CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
MCP_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=300
MCP_CIRCUIT_BREAKER_HALF_OPEN_MAX_CALLS=3

MCP_GLOBAL_RATE_LIMIT_PER_MINUTE=1000
MCP_PER_PROVIDER_RATE_LIMIT_PER_MINUTE=200

MCP_ADAPTIVE_TIMEOUTS_ENABLED=true
MCP_ADAPTIVE_TIMEOUTS_MIN_TIMEOUT=1.0
MCP_ADAPTIVE_TIMEOUTS_MAX_TIMEOUT=10.0
MCP_ADAPTIVE_TIMEOUTS_PERCENTILE=95
MCP_ADAPTIVE_TIMEOUTS_ADJUSTMENT_FACTOR=1.2
MCP_ADAPTIVE_TIMEOUTS_LEARNING_WINDOW=100
```

### Provider-Specific Configuration

#### Brave Search Provider

```yaml
mcp:
  providers:
    brave_search:
      enabled: true
      provider_type: "brave"
      priority: 1
      
      # API Configuration
      api_key: "${BRAVE_SEARCH_API_KEY}"
      base_url: "https://api.search.brave.com/res/v1/web/search"
      
      # Request Settings
      max_results: 10
      timeout_seconds: 3.0
      rate_limit_per_minute: 100
      
      # Custom Headers
      custom_headers:
        User-Agent: "Docaiche-MCP/1.0"
        Accept: "application/json"
      
      # Search Parameters
      custom_params:
        country: "US"
        search_lang: "en"
        ui_lang: "en-US"
        safesearch: "moderate"
        freshness: "pd"  # Past day, week, month, year
        
      # Health Check
      health_check:
        enabled: true
        interval: 300
        timeout: 10
        endpoint: "/health"
      
      # Performance Settings
      connection_pool_size: 10
      max_retries: 3
      backoff_factor: 2.0
```

**Environment Variables:**
```bash
MCP_BRAVE_SEARCH_ENABLED=true
MCP_BRAVE_SEARCH_PRIORITY=1
BRAVE_SEARCH_API_KEY=your_api_key_here
MCP_BRAVE_SEARCH_MAX_RESULTS=10
MCP_BRAVE_SEARCH_TIMEOUT_SECONDS=3.0
MCP_BRAVE_SEARCH_RATE_LIMIT_PER_MINUTE=100
MCP_BRAVE_SEARCH_COUNTRY=US
MCP_BRAVE_SEARCH_SEARCH_LANG=en
MCP_BRAVE_SEARCH_UI_LANG=en-US
MCP_BRAVE_SEARCH_SAFESEARCH=moderate
```

#### Google Custom Search Provider

```yaml
mcp:
  providers:
    google_search:
      enabled: true
      provider_type: "google"
      priority: 2
      
      # API Configuration
      api_key: "${GOOGLE_CUSTOM_SEARCH_API_KEY}"
      search_engine_id: "${GOOGLE_CUSTOM_SEARCH_ENGINE_ID}"
      base_url: "https://www.googleapis.com/customsearch/v1"
      
      # Request Settings
      max_results: 10
      timeout_seconds: 4.0
      rate_limit_per_minute: 100
      
      # Search Parameters
      custom_params:
        gl: "us"  # Geographic location
        hl: "en"  # Interface language
        lr: "lang_en"  # Language restrict
        safe: "medium"  # SafeSearch
        cr: "countryUS"  # Country restrict
        
      # Performance Settings
      connection_pool_size: 5
      max_retries: 3
      backoff_factor: 1.5
```

**Environment Variables:**
```bash
MCP_GOOGLE_SEARCH_ENABLED=true
MCP_GOOGLE_SEARCH_PRIORITY=2
GOOGLE_CUSTOM_SEARCH_API_KEY=your_api_key_here
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_engine_id_here
MCP_GOOGLE_SEARCH_MAX_RESULTS=10
MCP_GOOGLE_SEARCH_TIMEOUT_SECONDS=4.0
MCP_GOOGLE_SEARCH_RATE_LIMIT_PER_MINUTE=100
```

#### DuckDuckGo Provider

```yaml
mcp:
  providers:
    duckduckgo_search:
      enabled: true
      provider_type: "duckduckgo"
      priority: 3
      
      # API Configuration (no API key required)
      base_url: "https://api.duckduckgo.com/"
      
      # Request Settings
      max_results: 10
      timeout_seconds: 5.0
      rate_limit_per_minute: 60
      
      # Search Parameters
      custom_params:
        format: "json"
        no_redirect: "1"
        no_html: "1"
        skip_disambig: "1"
        
      # Performance Settings
      connection_pool_size: 3
      max_retries: 2
      backoff_factor: 1.0
```

**Environment Variables:**
```bash
MCP_DUCKDUCKGO_SEARCH_ENABLED=true
MCP_DUCKDUCKGO_SEARCH_PRIORITY=3
MCP_DUCKDUCKGO_SEARCH_MAX_RESULTS=10
MCP_DUCKDUCKGO_SEARCH_TIMEOUT_SECONDS=5.0
MCP_DUCKDUCKGO_SEARCH_RATE_LIMIT_PER_MINUTE=60
```

## Text AI Configuration

### LLM Integration Settings

```yaml
mcp:
  text_ai:
    # Enable/disable Text AI features
    enabled: true
    
    # LLM Provider Configuration
    llm_provider: "openai"  # openai, anthropic, azure, local
    
    # OpenAI Configuration
    openai:
      api_key: "${OPENAI_API_KEY}"
      model: "gpt-4"
      max_tokens: 1000
      temperature: 0.3
      timeout: 30
      
    # Query Analysis Settings
    query_analysis:
      enabled: true
      confidence_threshold: 0.7
      cache_results: true
      cache_ttl: 3600
      
    # Result Evaluation Settings
    result_evaluation:
      enabled: true
      relevance_threshold: 0.6
      completeness_threshold: 0.7
      
    # External Search Decision
    external_search_decision:
      enabled: true
      trigger_threshold: 0.4
      max_external_searches_per_query: 3
      
    # Prompt Configuration
    prompts:
      query_analysis_prompt: "prompts/query_analysis.txt"
      relevance_evaluation_prompt: "prompts/relevance_evaluation.txt"
      external_search_prompt: "prompts/external_search.txt"
```

**Environment Variables:**
```bash
MCP_TEXT_AI_ENABLED=true
MCP_TEXT_AI_LLM_PROVIDER=openai

OPENAI_API_KEY=your_openai_api_key_here
MCP_OPENAI_MODEL=gpt-4
MCP_OPENAI_MAX_TOKENS=1000
MCP_OPENAI_TEMPERATURE=0.3
MCP_OPENAI_TIMEOUT=30

MCP_QUERY_ANALYSIS_ENABLED=true
MCP_QUERY_ANALYSIS_CONFIDENCE_THRESHOLD=0.7
MCP_QUERY_ANALYSIS_CACHE_RESULTS=true
MCP_QUERY_ANALYSIS_CACHE_TTL=3600

MCP_RESULT_EVALUATION_ENABLED=true
MCP_RESULT_EVALUATION_RELEVANCE_THRESHOLD=0.6
MCP_RESULT_EVALUATION_COMPLETENESS_THRESHOLD=0.7

MCP_EXTERNAL_SEARCH_DECISION_ENABLED=true
MCP_EXTERNAL_SEARCH_DECISION_TRIGGER_THRESHOLD=0.4
MCP_EXTERNAL_SEARCH_DECISION_MAX_SEARCHES=3
```

## Performance and Monitoring Configuration

### Performance Monitoring

```yaml
monitoring:
  # Enable/disable performance monitoring
  enabled: true
  
  # Metrics Collection
  metrics:
    enabled: true
    collection_interval: 60
    retention_days: 30
    
    # Prometheus Integration
    prometheus:
      enabled: true
      endpoint: "/metrics"
      port: 9090
      
  # Health Checks
  health_checks:
    enabled: true
    interval: 60
    timeout: 10
    
    # Component Health Checks
    database_check: true
    redis_check: true
    external_providers_check: true
    
  # Performance Targets
  performance_targets:
    l1_cache_latency_ms: 0.1
    l2_cache_latency_ms: 10.0
    external_search_latency_ms: 2000.0
    system_throughput_rps: 100
    memory_usage_mb: 1000
    
  # Alerting
  alerting:
    enabled: true
    
    # Alert Thresholds
    error_rate_threshold: 0.05
    latency_p95_threshold_ms: 5000
    cache_hit_ratio_threshold: 0.8
    external_provider_failure_threshold: 0.1
```

**Environment Variables:**
```bash
MCP_MONITORING_ENABLED=true
MCP_METRICS_ENABLED=true
MCP_METRICS_COLLECTION_INTERVAL=60
MCP_METRICS_RETENTION_DAYS=30

MCP_PROMETHEUS_ENABLED=true
MCP_PROMETHEUS_ENDPOINT=/metrics
MCP_PROMETHEUS_PORT=9090

MCP_HEALTH_CHECKS_ENABLED=true
MCP_HEALTH_CHECKS_INTERVAL=60
MCP_HEALTH_CHECKS_TIMEOUT=10

MCP_TARGET_L1_CACHE_LATENCY_MS=0.1
MCP_TARGET_L2_CACHE_LATENCY_MS=10.0
MCP_TARGET_EXTERNAL_SEARCH_LATENCY_MS=2000.0
MCP_TARGET_SYSTEM_THROUGHPUT_RPS=100
MCP_TARGET_MEMORY_USAGE_MB=1000

MCP_ALERTING_ENABLED=true
MCP_ALERT_ERROR_RATE_THRESHOLD=0.05
MCP_ALERT_LATENCY_P95_THRESHOLD_MS=5000
MCP_ALERT_CACHE_HIT_RATIO_THRESHOLD=0.8
MCP_ALERT_EXTERNAL_PROVIDER_FAILURE_THRESHOLD=0.1
```

### Logging Configuration

```yaml
logging:
  # Global logging settings
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "json"  # json, text
  
  # Log outputs
  outputs:
    console:
      enabled: true
      level: "INFO"
      format: "text"
      
    file:
      enabled: true
      level: "INFO"
      format: "json"
      path: "/var/log/docaiche/app.log"
      max_size_mb: 100
      backup_count: 10
      
    syslog:
      enabled: false
      level: "WARNING"
      host: "localhost"
      port: 514
      
  # Component-specific logging
  components:
    mcp_external_search:
      level: "INFO"
      include_request_details: true
      include_response_details: false
      
    mcp_cache:
      level: "INFO"
      include_cache_stats: true
      
    mcp_text_ai:
      level: "INFO"
      include_prompt_details: false
      include_response_details: false
      
  # Security logging
  security:
    log_api_keys: false
    log_user_queries: true
    redact_pii: true
    log_ip_addresses: true
```

**Environment Variables:**
```bash
LOG_LEVEL=INFO
LOG_FORMAT=json

LOG_CONSOLE_ENABLED=true
LOG_CONSOLE_LEVEL=INFO
LOG_CONSOLE_FORMAT=text

LOG_FILE_ENABLED=true
LOG_FILE_LEVEL=INFO
LOG_FILE_FORMAT=json
LOG_FILE_PATH=/var/log/docaiche/app.log
LOG_FILE_MAX_SIZE_MB=100
LOG_FILE_BACKUP_COUNT=10

LOG_SYSLOG_ENABLED=false
LOG_SYSLOG_LEVEL=WARNING
LOG_SYSLOG_HOST=localhost
LOG_SYSLOG_PORT=514

LOG_MCP_EXTERNAL_SEARCH_LEVEL=INFO
LOG_MCP_EXTERNAL_SEARCH_INCLUDE_REQUEST_DETAILS=true
LOG_MCP_EXTERNAL_SEARCH_INCLUDE_RESPONSE_DETAILS=false

LOG_MCP_CACHE_LEVEL=INFO
LOG_MCP_CACHE_INCLUDE_CACHE_STATS=true

LOG_MCP_TEXT_AI_LEVEL=INFO
LOG_MCP_TEXT_AI_INCLUDE_PROMPT_DETAILS=false
LOG_MCP_TEXT_AI_INCLUDE_RESPONSE_DETAILS=false

LOG_SECURITY_API_KEYS=false
LOG_SECURITY_USER_QUERIES=true
LOG_SECURITY_REDACT_PII=true
LOG_SECURITY_IP_ADDRESSES=true
```

## Security Configuration

### API Security

```yaml
security:
  # API Authentication
  api_authentication:
    enabled: true
    method: "jwt"  # jwt, api_key, oauth
    
    # JWT Configuration
    jwt:
      secret_key: "${JWT_SECRET_KEY}"
      algorithm: "HS256"
      expiration_hours: 24
      refresh_enabled: true
      refresh_expiration_days: 7
      
  # Rate Limiting
  rate_limiting:
    enabled: true
    default_per_minute: 1000
    
    # Endpoint-specific limits
    endpoints:
      "/api/v1/search": 100
      "/api/v1/mcp/search": 50
      "/api/v1/mcp/providers": 10
      
  # CORS Configuration
  cors:
    enabled: true
    allowed_origins:
      - "https://your-domain.com"
      - "https://admin.your-domain.com"
    allowed_methods:
      - "GET"
      - "POST"
      - "PUT"
      - "DELETE"
      - "OPTIONS"
    allowed_headers:
      - "Content-Type"
      - "Authorization"
      - "X-Requested-With"
    expose_headers:
      - "X-RateLimit-Remaining"
      - "X-RateLimit-Reset"
    allow_credentials: true
    max_age: 3600
    
  # Input Validation
  input_validation:
    enabled: true
    max_query_length: 1000
    max_results_per_request: 100
    sanitize_html: true
    validate_json_schema: true
```

**Environment Variables:**
```bash
SECURITY_API_AUTHENTICATION_ENABLED=true
SECURITY_API_AUTHENTICATION_METHOD=jwt

JWT_SECRET_KEY=your_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
JWT_REFRESH_ENABLED=true
JWT_REFRESH_EXPIRATION_DAYS=7

SECURITY_RATE_LIMITING_ENABLED=true
SECURITY_RATE_LIMITING_DEFAULT_PER_MINUTE=1000
SECURITY_RATE_LIMITING_SEARCH_PER_MINUTE=100
SECURITY_RATE_LIMITING_MCP_SEARCH_PER_MINUTE=50
SECURITY_RATE_LIMITING_MCP_PROVIDERS_PER_MINUTE=10

SECURITY_CORS_ENABLED=true
SECURITY_CORS_ALLOWED_ORIGINS=https://your-domain.com,https://admin.your-domain.com
SECURITY_CORS_ALLOW_CREDENTIALS=true
SECURITY_CORS_MAX_AGE=3600

SECURITY_INPUT_VALIDATION_ENABLED=true
SECURITY_INPUT_VALIDATION_MAX_QUERY_LENGTH=1000
SECURITY_INPUT_VALIDATION_MAX_RESULTS_PER_REQUEST=100
SECURITY_INPUT_VALIDATION_SANITIZE_HTML=true
SECURITY_INPUT_VALIDATION_VALIDATE_JSON_SCHEMA=true
```

## Admin UI Configuration

### Frontend Configuration

```yaml
admin_ui:
  # Build Configuration
  build:
    environment: "production"  # development, staging, production
    source_maps: false
    minification: true
    compression: true
    
  # API Integration
  api:
    base_url: "https://your-domain.com/api/v1"
    timeout: 30000
    retry_attempts: 3
    retry_delay: 1000
    
  # Feature Flags
  features:
    external_search_management: true
    performance_monitoring: true
    provider_configuration: true
    system_health_monitoring: true
    advanced_caching_controls: true
    
  # UI Settings
  ui:
    theme: "light"  # light, dark, auto
    language: "en"  # en, es, fr, de
    timezone: "UTC"
    date_format: "YYYY-MM-DD"
    time_format: "HH:mm:ss"
    
  # Refresh Intervals (milliseconds)
  refresh_intervals:
    provider_status: 30000
    performance_stats: 60000
    system_health: 30000
    cache_statistics: 15000
```

**Environment Variables:**
```bash
REACT_APP_ENVIRONMENT=production
REACT_APP_API_BASE_URL=https://your-domain.com/api/v1
REACT_APP_API_TIMEOUT=30000
REACT_APP_API_RETRY_ATTEMPTS=3
REACT_APP_API_RETRY_DELAY=1000

REACT_APP_FEATURE_EXTERNAL_SEARCH_MANAGEMENT=true
REACT_APP_FEATURE_PERFORMANCE_MONITORING=true
REACT_APP_FEATURE_PROVIDER_CONFIGURATION=true
REACT_APP_FEATURE_SYSTEM_HEALTH_MONITORING=true
REACT_APP_FEATURE_ADVANCED_CACHING_CONTROLS=true

REACT_APP_UI_THEME=light
REACT_APP_UI_LANGUAGE=en
REACT_APP_UI_TIMEZONE=UTC
REACT_APP_UI_DATE_FORMAT=YYYY-MM-DD
REACT_APP_UI_TIME_FORMAT=HH:mm:ss

REACT_APP_REFRESH_PROVIDER_STATUS=30000
REACT_APP_REFRESH_PERFORMANCE_STATS=60000
REACT_APP_REFRESH_SYSTEM_HEALTH=30000
REACT_APP_REFRESH_CACHE_STATISTICS=15000
```

## Configuration Validation

### Validation Rules

The system validates all configuration on startup:

1. **Required Fields**: All required configuration fields must be present
2. **Type Validation**: All values must match expected data types
3. **Range Validation**: Numeric values must be within acceptable ranges
4. **Format Validation**: Strings must match expected formats (URLs, email, etc.)
5. **Dependency Validation**: Related settings must be consistent

### Configuration Testing

```bash
# Validate configuration
python scripts/validate_configuration.py --env production

# Test configuration with dry-run
python scripts/test_configuration.py --config config/production.yaml --dry-run

# Generate configuration template
python scripts/generate_config_template.py --output config/template.yaml
```

## Environment-Specific Configurations

### Development Configuration

```yaml
# config/development.yaml
database:
  url: "postgresql://dev:dev@localhost:5432/docaiche_dev"
  
cache:
  redis:
    url: "redis://localhost:6379/1"
  l1_cache:
    size: 100
    
mcp:
  external_search:
    enabled: true
    max_concurrent_providers: 1
    
logging:
  level: "DEBUG"
  outputs:
    console:
      enabled: true
      level: "DEBUG"
```

### Staging Configuration

```yaml
# config/staging.yaml
database:
  url: "postgresql://staging:password@staging-db:5432/docaiche_staging"
  
cache:
  redis:
    url: "redis://staging-redis:6379/0"
  l1_cache:
    size: 500
    
mcp:
  external_search:
    enabled: true
    max_concurrent_providers: 2
    
logging:
  level: "INFO"
  outputs:
    file:
      enabled: true
      path: "/var/log/docaiche/staging.log"
```

### Production Configuration

```yaml
# config/production.yaml
database:
  url: "postgresql://prod:secure_password@prod-db:5432/docaiche"
  pool_size: 20
  
cache:
  redis:
    url: "redis://prod-redis:6379/0"
  l1_cache:
    size: 2000
    
mcp:
  external_search:
    enabled: true
    max_concurrent_providers: 5
    
logging:
  level: "WARNING"
  outputs:
    file:
      enabled: true
      path: "/var/log/docaiche/production.log"
    syslog:
      enabled: true
```

---

This configuration reference provides comprehensive documentation for all MCP Search System settings. Use this guide to customize the system for your specific deployment requirements.