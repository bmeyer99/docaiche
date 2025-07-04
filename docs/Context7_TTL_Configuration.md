# Context7 TTL Configuration System

## Overview

The Context7 TTL (Time-To-Live) configuration system provides comprehensive control over how long Context7 documentation remains valid in the system. This configuration supports intelligent TTL calculation based on technology stacks, document types, content freshness, and popularity metrics.

## Key Features

- **Default TTL Settings**: Configurable base TTL with min/max bounds
- **Technology-Specific Multipliers**: Different TTL values for different tech stacks
- **Document Type Adjustments**: TTL variations based on content type
- **Feature Toggles**: Enable/disable specific TTL components
- **Environment Variable Support**: Full override capability via env vars
- **Cache Integration**: Automatic cache TTL calculation
- **Background Job Configuration**: Automated cleanup and maintenance
- **Service Restart Integration**: Automatic service restarts on config changes

## Configuration Structure

### Main Configuration Sections

```yaml
context7:
  enabled: true                           # Enable Context7 ingestion
  ttl: {}                                # TTL-specific settings
  ingestion: {}                          # Ingestion and processing settings
  cache: {}                              # Cache configuration
  background_jobs: {}                    # Background job settings
  weaviate_ttl_enabled: true             # Apply TTL to Weaviate docs
  enable_audit_logging: true             # Enable audit logging
  enable_performance_monitoring: true    # Enable performance metrics
  max_memory_usage_mb: 512               # Memory limit
```

### TTL Configuration (`context7.ttl`)

#### Base Settings
```yaml
ttl:
  default_days: 7        # Default TTL for all documents
  min_days: 1           # Minimum allowed TTL
  max_days: 90          # Maximum allowed TTL
```

#### Feature Toggles
```yaml
ttl:
  enable_tech_multipliers: true      # Enable technology-specific multipliers
  enable_doc_type_adjustments: true  # Enable document type adjustments
  enable_freshness_boost: true       # Give fresh content longer TTL
  enable_popularity_boost: true      # Give popular content longer TTL
```

#### Technology Multipliers
```yaml
ttl:
  tech_multipliers:
    python: 2.0          # Python docs get 2x longer TTL
    react: 1.5           # React docs get 1.5x longer TTL
    vue: 1.5             # Vue docs get 1.5x longer TTL
    docker: 1.8          # Docker docs get 1.8x longer TTL
    kubernetes: 2.0      # Kubernetes docs get 2x longer TTL
    javascript: 1.2      # JavaScript docs get 1.2x longer TTL
    # Add more as needed
```

#### Document Type Adjustments
```yaml
ttl:
  doc_type_adjustments:
    api: 0.8             # API docs expire faster (more volatile)
    tutorial: 1.5        # Tutorials last longer (more stable)
    reference: 2.0       # Reference docs last much longer
    changelog: 0.5       # Changelogs expire quickly
    blog: 0.6            # Blog posts expire relatively quickly
    news: 0.4            # News expires very quickly
```

#### Freshness and Popularity
```yaml
ttl:
  freshness_boost_days: 30           # Days considered "fresh"
  freshness_boost_multiplier: 1.5    # Multiplier for fresh content
  popularity_threshold: 100          # Min views/stars for popularity boost
  popularity_boost_multiplier: 1.3   # Multiplier for popular content
```

### Ingestion Configuration (`context7.ingestion`)

```yaml
ingestion:
  batch_size: 10                     # Documents per batch
  max_concurrent_batches: 3          # Max concurrent processing
  ingestion_timeout_seconds: 300     # Timeout for operations
  retry_attempts: 3                  # Retry failed ingestions
  retry_delay_seconds: 60            # Delay between retries
  
  # Synchronous ingestion
  sync_enabled: true                 # Enable sync ingestion
  sync_timeout_seconds: 15           # Timeout for sync operations
  sync_batch_size: 5                 # Batch size for sync
  
  # Pipeline settings
  enable_smart_pipeline: true        # Use intelligent processing
  enable_content_validation: true    # Validate before ingestion
  enable_duplicate_detection: true   # Detect duplicates
  
  # Fallback handling
  fallback_storage_enabled: true     # Enable fallback storage
  max_fallback_items: 1000          # Max items in fallback
  fallback_cleanup_days: 7          # Cleanup after days
```

### Cache Configuration (`context7.cache`)

```yaml
cache:
  enabled: true                      # Enable caching
  ttl_multiplier: 1.0               # Cache TTL = doc TTL * multiplier
  max_cache_size: 10000             # Max cached items
  eviction_policy: "lru"            # Eviction policy (lru/lfu/ttl)
  cleanup_interval_seconds: 300     # Cache cleanup interval
  
  # Cache warming
  enable_preload: false             # Enable preloading
  preload_popular_items: true       # Preload popular items
  preload_batch_size: 50            # Preloading batch size
```

### Background Jobs Configuration (`context7.background_jobs`)

```yaml
background_jobs:
  # TTL cleanup
  ttl_cleanup_enabled: true                    # Enable cleanup job
  ttl_cleanup_interval_seconds: 3600          # Cleanup every hour
  ttl_cleanup_batch_size: 100                 # Items per batch
  
  # Metrics collection
  metrics_collection_enabled: true            # Enable metrics
  metrics_collection_interval_seconds: 300   # Every 5 minutes
  
  # Health checks
  health_check_enabled: true                  # Enable health checks
  health_check_interval_seconds: 60          # Every minute
  
  # Maintenance window
  maintenance_window_enabled: false          # Disable by default
  maintenance_window_start_hour: 2           # Start at 2 AM
  maintenance_window_duration_hours: 4       # 4-hour window
```

## Environment Variables

All configuration options can be overridden using environment variables with the `CONTEXT7_` prefix:

### Core Settings
```bash
CONTEXT7_ENABLED=true
CONTEXT7_WEAVIATE_TTL_ENABLED=true
CONTEXT7_ENABLE_AUDIT_LOGGING=true
CONTEXT7_ENABLE_PERFORMANCE_MONITORING=true
CONTEXT7_MAX_MEMORY_USAGE_MB=512
```

### TTL Settings
```bash
CONTEXT7_TTL_DEFAULT_DAYS=7
CONTEXT7_TTL_MIN_DAYS=1
CONTEXT7_TTL_MAX_DAYS=90
CONTEXT7_TTL_ENABLE_TECH_MULTIPLIERS=true
CONTEXT7_TTL_ENABLE_DOC_TYPE_ADJUSTMENTS=true
CONTEXT7_TTL_ENABLE_FRESHNESS_BOOST=true
CONTEXT7_TTL_ENABLE_POPULARITY_BOOST=true
```

### Technology Multipliers
```bash
CONTEXT7_TTL_TECH_PYTHON_MULTIPLIER=2.0
CONTEXT7_TTL_TECH_REACT_MULTIPLIER=1.5
CONTEXT7_TTL_TECH_DOCKER_MULTIPLIER=1.8
CONTEXT7_TTL_TECH_KUBERNETES_MULTIPLIER=2.0
```

### Document Type Adjustments
```bash
CONTEXT7_TTL_DOC_API_ADJUSTMENT=0.8
CONTEXT7_TTL_DOC_TUTORIAL_ADJUSTMENT=1.5
CONTEXT7_TTL_DOC_REFERENCE_ADJUSTMENT=2.0
CONTEXT7_TTL_DOC_CHANGELOG_ADJUSTMENT=0.5
```

### Ingestion Settings
```bash
CONTEXT7_INGESTION_BATCH_SIZE=10
CONTEXT7_INGESTION_SYNC_ENABLED=true
CONTEXT7_INGESTION_ENABLE_SMART_PIPELINE=true
CONTEXT7_INGESTION_FALLBACK_STORAGE_ENABLED=true
```

### Cache Settings
```bash
CONTEXT7_CACHE_ENABLED=true
CONTEXT7_CACHE_TTL_MULTIPLIER=1.0
CONTEXT7_CACHE_MAX_CACHE_SIZE=10000
CONTEXT7_CACHE_EVICTION_POLICY=lru
```

### Background Jobs
```bash
CONTEXT7_BACKGROUND_TTL_CLEANUP_ENABLED=true
CONTEXT7_BACKGROUND_TTL_CLEANUP_INTERVAL_SECONDS=3600
CONTEXT7_BACKGROUND_METRICS_COLLECTION_ENABLED=true
CONTEXT7_BACKGROUND_HEALTH_CHECK_ENABLED=true
```

## TTL Calculation Logic

The effective TTL for a document is calculated using the following formula:

```
effective_ttl = base_ttl * tech_multiplier * doc_type_adjustment * freshness_boost * popularity_boost
```

Then bounded by:
```
final_ttl = max(min_days, min(effective_ttl, max_days))
```

### Example Calculations

1. **Python Tutorial** (fresh and popular):
   ```
   base_ttl = 7 days
   tech_multiplier = 2.0 (python)
   doc_type_adjustment = 1.5 (tutorial)
   freshness_boost = 1.5 (fresh content)
   popularity_boost = 1.3 (popular)
   
   effective_ttl = 7 * 2.0 * 1.5 * 1.5 * 1.3 = 40.95 days
   final_ttl = min(40, 90) = 40 days
   ```

2. **API Changelog**:
   ```
   base_ttl = 7 days
   tech_multiplier = 1.0 (no tech specified)
   doc_type_adjustment = 0.5 (changelog)
   
   effective_ttl = 7 * 1.0 * 0.5 = 3.5 days
   final_ttl = max(1, 3) = 3 days
   ```

## Service Restart Integration

Configuration changes automatically trigger service restarts for the Context7 service:

### Monitored Configuration Keys
- `context7.*` - Any Context7 configuration change
- `context7.enabled` - Enable/disable Context7
- `context7.ttl.*` - TTL configuration changes
- `context7.ingestion.*` - Ingestion settings
- `context7.cache.*` - Cache configuration
- `context7.background_jobs.*` - Background job settings

### Service Priority
The Context7 service has restart priority 4, ensuring it restarts after core services (Redis, DB, AnythingLLM) but before monitoring services.

## Usage Examples

### Scenario 1: High-Performance Python Documentation Site
```yaml
context7:
  ttl:
    default_days: 14
    tech_multipliers:
      python: 3.0
      django: 2.5
      flask: 2.0
  ingestion:
    batch_size: 20
    max_concurrent_batches: 5
  cache:
    ttl_multiplier: 1.5
    max_cache_size: 20000
```

### Scenario 2: Fast-Changing API Documentation
```yaml
context7:
  ttl:
    default_days: 3
    doc_type_adjustments:
      api: 0.5
      changelog: 0.3
    enable_freshness_boost: true
    freshness_boost_multiplier: 2.0
  background_jobs:
    ttl_cleanup_interval_seconds: 1800  # 30 minutes
```

### Scenario 3: Enterprise Setup
```yaml
context7:
  ttl:
    default_days: 10
    max_days: 180
  ingestion:
    batch_size: 50
    max_concurrent_batches: 10
  background_jobs:
    maintenance_window_enabled: true
    maintenance_window_start_hour: 2
    maintenance_window_duration_hours: 6
  max_memory_usage_mb: 1024
```

## API Methods

### Context7Config Methods

#### `get_effective_ttl(technology, doc_type, is_fresh, is_popular)`
Calculates the effective TTL for a document based on all configured factors.

```python
config = Context7Config()
ttl = config.get_effective_ttl(
    technology="python",
    doc_type="tutorial", 
    is_fresh=True,
    is_popular=True
)
```

#### `get_cache_ttl(doc_ttl_days)`
Calculates cache TTL in seconds based on document TTL in days.

```python
cache_ttl_seconds = config.get_cache_ttl(7)  # Returns 604800 (7 days in seconds)
```

## Validation Rules

### TTL Bounds
- `min_days` must be less than `max_days`
- `default_days` must be between `min_days` and `max_days`
- All TTL values must be positive integers

### Multipliers and Adjustments
- Technology multipliers must be between 0.1 and 10.0
- Document type adjustments must be between 0.1 and 10.0
- Freshness boost multiplier must be between 1.0 and 5.0
- Popularity boost multiplier must be between 1.0 and 3.0

### Timeouts and Intervals
- All timeout values must be positive integers
- Cleanup intervals must be at least 60 seconds
- Batch sizes must be between 1 and configured maximums

## Best Practices

1. **Start with Defaults**: Use the default configuration as a baseline and adjust as needed
2. **Monitor TTL Effectiveness**: Use metrics to track how TTL settings affect cache hit rates
3. **Technology-Specific Tuning**: Adjust multipliers based on how frequently different technologies change
4. **Document Type Optimization**: Set appropriate adjustments for different content types
5. **Environment-Specific Settings**: Use environment variables for deployment-specific overrides
6. **Regular Review**: Periodically review and adjust TTL settings based on usage patterns

## Troubleshooting

### Common Issues

1. **TTL Too Short**: Documents expire too quickly, causing frequent re-ingestion
   - Increase `default_days` or relevant multipliers
   
2. **TTL Too Long**: Stale content remains in system too long
   - Decrease `default_days` or relevant adjustments
   
3. **High Memory Usage**: Cache grows too large
   - Reduce `max_cache_size` or `ttl_multiplier`
   
4. **Performance Issues**: Ingestion is too slow
   - Increase `batch_size` and `max_concurrent_batches`
   
5. **Configuration Not Applied**: Changes don't take effect
   - Check if Context7 service restarted successfully
   - Verify environment variables are properly set

### Debugging

Enable debug logging to see TTL calculations:
```bash
CONTEXT7_ENABLE_AUDIT_LOGGING=true
CONTEXT7_ENABLE_PERFORMANCE_MONITORING=true
```

Check configuration loading:
```bash
# View current configuration
curl http://localhost:4080/api/v1/config/context7

# Check environment overrides
env | grep CONTEXT7_
```