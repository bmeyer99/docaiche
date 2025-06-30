# Search System Data Collection Requirements

This document outlines the comprehensive data collection requirements for the MCP search system. These metrics, logs, and traces will power the monitoring dashboards and provide insights into system performance, reliability, and effectiveness.

## 1. Search Process Metrics

### Core Search Performance
- **Search Execution Time (Histogram)**
  - Overall time from request to response
  - Broken down by search phase (cache check, vector search, etc.)
  - Percentiles: p50, p90, p95, p99
  - Tagged by query type, workspace, and response type

- **Search Result Counts (Counter)**
  - Total results returned
  - Results per source (AnythingLLM, external providers)
  - Tagged by query type and technology

- **Search Quality Metrics (Gauge)**
  - Relevance scores (as determined by Text AI)
  - Result completeness scores
  - User feedback ratings (if available)

- **Search Path Distribution (Counter)**
  - Cache hit count
  - AnythingLLM successful search count
  - Refined query count
  - External search count
  - Tagged by query type and technology

### Cache Performance
- **Cache Hit Rate (Gauge)**
  - Overall hit rate percentage
  - Hit rate by query type and technology
  - Hit rate by time of day

- **Cache Operation Latency (Histogram)**
  - Time for cache checks
  - Time for cache writes
  - Tagged by operation type

- **Cache Size (Gauge)**
  - Current cache entry count
  - Memory utilization
  - Entry count by query type

- **Cache TTL Distribution (Histogram)**
  - Distribution of TTL values
  - Expiration counts

### AnythingLLM Performance
- **Vector Search Latency (Histogram)**
  - Time for vector search operations
  - Broken down by workspace
  - Percentiles: p50, p90, p95, p99

- **Vector Search Quality (Gauge)**
  - Similarity scores distribution
  - Result count distribution

- **Workspace Utilization (Gauge)**
  - Document count by workspace
  - Search distribution by workspace
  - Success rate by workspace

- **Connection Status (Gauge)**
  - Connection availability
  - Connection errors
  - Retries

### Text AI Performance
- **AI Request Latency (Histogram)**
  - Time for AI evaluations
  - Broken down by decision type
  - Percentiles: p50, p90, p95, p99

- **Token Usage (Counter)**
  - Tokens used by prompt type
  - Total tokens per request
  - Tokens by model

- **AI Decision Distribution (Counter)**
  - Result relevance assessments
  - External search decisions
  - Query refinement decisions
  - Tagged by query type

- **Prompt Version Performance (Gauge)**
  - Effectiveness metrics by prompt version
  - Comparison between versions

### External Search Providers
- **Provider Request Latency (Histogram)**
  - Time for external search operations
  - Broken down by provider
  - Percentiles: p50, p90, p95, p99

- **Provider Usage (Counter)**
  - Requests by provider
  - Results by provider
  - Fallback occurrences

- **Provider Availability (Gauge)**
  - Success rate by provider
  - Error rate by provider
  - Rate limit hits

- **Provider Selection (Counter)**
  - Provider selection by query type
  - Provider selection by rule

### Ingestion Pipeline
- **Ingestion Volume (Counter)**
  - Documents ingested
  - Total content size
  - Tagged by source and workspace

- **Ingestion Latency (Histogram)**
  - Processing time per document
  - Total ingestion pipeline time
  - Percentiles: p50, p90, p95, p99

- **Quality Control (Counter)**
  - Validation success/failure counts
  - Rejection reasons
  - Duplicate detections

- **Workspace Assignment (Counter)**
  - Assignment counts by workspace
  - Assignment rule triggers

## 2. System Resource Metrics

### Compute Resources
- **CPU Utilization (Gauge)**
  - Overall utilization
  - Per-component utilization
  - Peak utilization periods

- **Memory Usage (Gauge)**
  - Overall memory usage
  - Per-component memory usage
  - Memory growth patterns

- **Goroutine/Thread Count (Gauge)**
  - Active goroutines/threads
  - Blocked goroutines/threads
  - Tagged by component

- **Request Queue Depth (Gauge)**
  - Pending requests
  - Rejected requests due to overload

### Network Resources
- **Network Throughput (Counter)**
  - Bytes sent/received
  - Request/response sizes
  - Tagged by endpoint

- **Connection Pool Stats (Gauge)**
  - Active connections
  - Idle connections
  - Connection creation rate

- **DNS Resolution Time (Histogram)**
  - Time for DNS lookups
  - Failed resolutions

- **TLS Handshake Time (Histogram)**
  - Time for TLS handshakes
  - Failed handshakes

### Storage Resources
- **Disk Usage (Gauge)**
  - Storage utilization
  - Storage growth rate
  - Tagged by data type

- **I/O Operations (Counter)**
  - Read/write operations
  - I/O errors
  - Tagged by component

- **Database Metrics (Multiple)**
  - Query execution time
  - Connection pool stats
  - Transaction rates
  - Index performance

- **File Operation Latency (Histogram)**
  - Read/write operation time
  - File open/close time

## 3. Application Health Metrics

### Error Rates
- **Error Count (Counter)**
  - Overall error count
  - Errors by component
  - Errors by type
  - Errors by severity

- **Error Distribution (Counter)**
  - Client errors (400s)
  - Server errors (500s)
  - Timeout errors
  - Dependency errors

- **Retry Metrics (Counter)**
  - Retry attempts
  - Retry success rate
  - Maximum retry count reached

- **Circuit Breaker Status (Gauge)**
  - Open/closed status
  - Trip counts
  - Recovery times

### Availability Metrics
- **Service Uptime (Gauge)**
  - Uptime percentage
  - Component availability
  - Tracked by service instance

- **Health Check Status (Gauge)**
  - Component health status
  - Dependency health status
  - Failed health checks

- **Initialization Time (Histogram)**
  - Service startup time
  - Component initialization time
  - Configuration load time

- **Graceful Shutdown Stats (Histogram)**
  - Shutdown time
  - Pending request completion rate

### Dependency Health
- **Dependency Availability (Gauge)**
  - Availability by dependency
  - Error rates by dependency

- **Dependency Latency (Histogram)**
  - Response time by dependency
  - Percentiles: p50, p90, p95, p99

- **Dependency Saturation (Gauge)**
  - Load on dependencies
  - Backpressure indicators

- **Dependency Errors (Counter)**
  - Error count by dependency
  - Error types by dependency

## 4. User Interaction Metrics

### UI Performance
- **Page Load Time (Histogram)**
  - Initial page load time
  - Time to interactive
  - Tagged by page/component

- **Component Render Time (Histogram)**
  - Render time by component
  - Re-render frequencies
  - Tagged by component type

- **UI Interaction Latency (Histogram)**
  - Time from click to response
  - Form submission time
  - Modal open/close time

- **Client-Side Errors (Counter)**
  - JavaScript exceptions
  - Failed API requests
  - Tagged by error type and page

### User Behavior
- **Feature Usage (Counter)**
  - Feature usage counts
  - Tagged by feature and user role

- **Configuration Changes (Counter)**
  - Settings modification counts
  - Tagged by setting type and user

- **Search Pattern Analysis (Counter)**
  - Query types distribution
  - Technology focus distribution
  - Response type preferences

- **Session Metrics (Histogram)**
  - Session duration
  - Pages per session
  - Actions per session

## 5. Logging Requirements

### Log Levels and Content
- **INFO Level**
  - Standard operation events
  - Configuration changes
  - Search requests and results summary
  - System initialization events

- **DEBUG Level**
  - Detailed operation flow
  - Cache operations
  - Decision points with outcomes
  - Performance details

- **WARNING Level**
  - Slow operations
  - Retry events
  - Resource pressure indicators
  - Potential issues

- **ERROR Level**
  - Failed operations
  - Exception details
  - Resource exhaustion
  - Security violations

### Log Structure
- **Standard Fields**
  - Timestamp (ISO 8601)
  - Log level
  - Component/service name
  - Operation name
  - Request ID (correlation)
  - User ID (if applicable)

- **Context Fields**
  - Query text (anonymized if needed)
  - Operation parameters (sanitized)
  - Result counts and metrics
  - Performance timing data

- **Error Fields**
  - Error code
  - Error message
  - Stack trace (in development)
  - Exception type
  - Recovery actions taken

### Log Storage
- **Retention Requirements**
  - INFO and below: 7 days
  - WARNING: 30 days
  - ERROR: 90 days

- **Storage Format**
  - JSON structured logs
  - Compressed for archival
  - Indexed for quick search

## 6. Distributed Tracing

### Trace Spans
- **Search Request Spans**
  - Overall search request
  - Cache check operation
  - Vector search operation
  - Text AI evaluation
  - External search operation
  - Response formatting

- **API Request Spans**
  - API endpoint handling
  - Authentication
  - Validation
  - Business logic
  - Database operations
  - Response generation

- **Dependency Spans**
  - AnythingLLM requests
  - Text AI requests
  - External search provider requests
  - Database operations
  - Cache operations

### Span Attributes
- **Common Attributes**
  - Operation name
  - Component name
  - Request parameters (sanitized)
  - Result summary
  - Error details (if applicable)

- **Performance Attributes**
  - Start time
  - Duration
  - CPU time
  - Idle time
  - Queue time

- **Relationship Attributes**
  - Parent span ID
  - Followed by span ID
  - Triggered by span ID

### Sampling Strategy
- **Always Sample**
  - Error cases
  - Slow operations (above threshold)
  - Critical business operations

- **Sampling Rate**
  - Production: 10% of regular traffic
  - Staging: 50% of traffic
  - Development: 100% of traffic

## 7. Alert Definitions

### Performance Alerts
- **High Latency Alert**
  - Trigger: p95 search time > 1s for 5 minutes
  - Severity: Warning

- **Error Rate Alert**
  - Trigger: Error rate > 1% for 5 minutes
  - Severity: Critical

- **Resource Saturation Alert**
  - Trigger: CPU > 80% for 10 minutes
  - Trigger: Memory > 85% for 10 minutes
  - Severity: Warning

- **Dependency Failure Alert**
  - Trigger: Any dependency error rate > 5% for 5 minutes
  - Severity: Critical

### Functional Alerts
- **Cache Effectiveness Alert**
  - Trigger: Cache hit rate < 50% for 30 minutes
  - Severity: Warning

- **Search Quality Alert**
  - Trigger: Average relevance score < 0.7 for 30 minutes
  - Severity: Warning

- **External Search Dependency Alert**
  - Trigger: External search usage > 30% for 30 minutes
  - Severity: Warning

- **Component Health Alert**
  - Trigger: Any component health check fails twice in 5 minutes
  - Severity: Critical

## 8. Dashboard Templates

### Executive Dashboard
- System health overview
- Search volume trends
- Success rate metrics
- Key performance indicators

### Operational Dashboard
- Detailed system health
- Component status
- Error distribution
- Resource utilization

### Performance Dashboard
- Detailed latency breakdowns
- Cache performance
- Database performance
- Network performance

### Search Quality Dashboard
- Relevance scores
- Result distributions
- External search usage
- Query pattern analysis

### User Interaction Dashboard
- Feature usage statistics
- Configuration change patterns
- UI performance metrics
- Session analytics

## 9. Data Retention Policies

### Metrics Retention
- High-resolution metrics (10s): 24 hours
- Medium-resolution metrics (1m): 7 days
- Low-resolution metrics (10m): 30 days
- Aggregated metrics (1h): 1 year

### Log Retention
- INFO logs: 7 days
- WARNING logs: 30 days
- ERROR logs: 90 days
- CRITICAL logs: 1 year

### Trace Retention
- Full traces: 7 days
- Trace summaries: 30 days
- Error traces: 90 days

### Alert History
- Alert events: 90 days
- Alert configuration changes: 1 year