# Admin UI Search Configuration Page Requirements

## Overview

This document outlines the requirements for a new administration page in the DocAIche admin-ui that allows users to configure, monitor, and optimize the MCP search system. The page will provide comprehensive control over search providers, AnythingLLM integration, Text AI prompts, and performance metrics.

## Page Structure

### 1. Main Sections

The Search Configuration page should be organized into the following tabbed sections:

1. **Dashboard** - Overview of search system status and key metrics
2. **Vector Search** - AnythingLLM configuration and workspace management
3. **Text AI** - Configuration of the AI decision making system and prompts
4. **Search Providers** - Management of external search providers
5. **Ingestion** - Configuration of the documentation ingestion pipeline
6. **Monitoring** - Detailed performance metrics and logs
7. **Settings** - Global search system settings

## Detailed Requirements

### 1. Dashboard Section

**Purpose:** Provide at-a-glance status of the search system and key performance indicators.

**Requirements:**
- Real-time status indicators for all search components
- Key performance metrics:
  - Average search time (last 24h)
  - Cache hit rate
  - AnythingLLM query success rate
  - External search usage rate
  - Most frequent search topics/categories
- Recent activity log (last 10 searches)
- System health alerts and notifications
- Quick access buttons to other sections

**UI Components:**
- Status cards with health indicators
- Metric cards with trend sparklines
- Mini time series charts for key metrics
- Recent activity table
- Alert/notification panel

### 2. Vector Search Configuration

**Purpose:** Configure and manage AnythingLLM integration and workspaces.

**Requirements:**
- AnythingLLM connection settings
  - Base URL
  - API key/authentication
  - Connection timeout
  - Retry settings
- Workspace management
  - List of available workspaces
  - Workspace creation/editing
  - Technology mapping to workspaces
  - Document counts per workspace
- Vector search settings
  - Similarity threshold
  - Maximum results
  - Embedding model selection
  - Context window size
- Testing interface
  - Test query capability
  - Result visualization
  - Performance metrics

**UI Components:**
- Connection settings form
- Workspace management table with CRUD operations
- Settings configuration panel
- Testing interface with query input and result display

### 3. Text AI Configuration

**Purpose:** Configure the Text AI model and customize decision prompts.

**Requirements:**
- Text AI connection settings
  - Model selection
  - Base URL/API endpoint
  - Authentication credentials
  - Request parameters (temperature, max tokens)
- Prompt template management
  - List of all decision point prompts
  - Prompt editor with syntax highlighting
  - Version history of prompts
  - Template variable documentation
- Prompt enhancement
  - AI-assisted prompt improvement feature
  - A/B testing of prompt variations
  - Performance metrics per prompt
- Default response settings
  - Configure default response formats
  - Sample response visualization

**UI Components:**
- Settings form for AI model configuration
- Interactive prompt editor with template variables
- Prompt version history timeline
- "Enhance with AI" button for each prompt
- Performance comparison charts
- Response format configuration panel

### 4. Search Providers Configuration

**Purpose:** Manage external search providers and their configuration.

**Requirements:**
- Provider registry
  - List of available search providers
  - Enable/disable providers
  - Provider priority ordering
- Provider configuration
  - API endpoints
  - Authentication credentials
  - Rate limits and quotas
  - Request parameters
  - Domain/site restrictions
- Provider testing
  - Test search interface
  - Response visualization
  - Performance metrics
- Provider selection rules
  - Configure rules for automatic provider selection
  - Domain-specific provider preferences

**UI Components:**
- Provider registry table with status toggles
- Drag-and-drop priority reordering
- Provider configuration forms (dynamic based on provider type)
- Test interface with query input and result display
- Rule builder for provider selection logic

### 5. Ingestion Configuration

**Purpose:** Configure the documentation ingestion pipeline for AnythingLLM.

**Requirements:**
- Ingestion settings
  - Chunking strategy
  - Metadata extraction rules
  - Content filtering rules
  - Document processing settings
- Automatic ingestion
  - Source monitoring configuration
  - Scheduling settings
  - Trigger conditions
- Quality control
  - Content validation rules
  - Manual approval workflow
  - Duplicate detection settings
- Workspace assignment
  - Rules for automatic workspace assignment
  - Technology detection settings

**UI Components:**
- Ingestion settings form
- Automatic ingestion configuration panel
- Quality control settings panel
- Workspace assignment rule builder
- Test ingestion interface

### 6. Monitoring Section

**Purpose:** Provide detailed performance metrics, logs, and debugging tools.

**Requirements:**
- Performance dashboards
  - Search performance metrics
  - Component-level performance
  - Cache performance
  - AI model performance
- Log explorer
  - Structured log search
  - Log filtering and sorting
  - Log level configuration
  - Log export
- Tracing visualization
  - Request trace visualization
  - Component timing breakdown
  - Error traces
- Alert configuration
  - Performance threshold alerts
  - Error rate alerts
  - System health alerts
  - Notification channels

**UI Components:**
- Embedded Grafana dashboards
- Log explorer with filtering options
- Trace visualization tool
- Alert configuration interface
- Real-time metric charts

### 7. Settings Section

**Purpose:** Configure global search system settings.

**Requirements:**
- Cache settings
  - Enable/disable caching
  - Cache TTL configuration
  - Cache size limits
  - Cache circuit breaker settings
- Performance settings
  - Timeouts
  - Concurrency limits
  - Maximum resource usage
- Security settings
  - Access control
  - Rate limiting
  - Content filtering
- Advanced settings
  - Feature flags
  - Experimental features
  - Debug mode

**UI Components:**
- Settings forms organized by category
- Save/reset configuration buttons
- Configuration export/import
- Environment indicator (dev/staging/prod)

## API Requirements

### New API Endpoints Needed

1. **Configuration Management**
   - `GET /api/v1/admin/search/config` - Get current search configuration
   - `PUT /api/v1/admin/search/config` - Update search configuration
   - `GET /api/v1/admin/search/config/history` - Get configuration change history
   - `POST /api/v1/admin/search/config/validate` - Validate configuration changes

2. **Vector Search**
   - `GET /api/v1/admin/search/vector/status` - Get AnythingLLM connection status
   - `GET /api/v1/admin/search/vector/workspaces` - List workspaces
   - `POST /api/v1/admin/search/vector/workspaces` - Create workspace
   - `PUT /api/v1/admin/search/vector/workspaces/{id}` - Update workspace
   - `DELETE /api/v1/admin/search/vector/workspaces/{id}` - Delete workspace
   - `POST /api/v1/admin/search/vector/test` - Test vector search

3. **Text AI**
   - `GET /api/v1/admin/search/text-ai/status` - Get Text AI status
   - `GET /api/v1/admin/search/text-ai/prompts` - List prompt templates
   - `PUT /api/v1/admin/search/text-ai/prompts/{id}` - Update prompt template
   - `POST /api/v1/admin/search/text-ai/prompts/{id}/enhance` - Enhance prompt with AI
   - `GET /api/v1/admin/search/text-ai/prompts/{id}/history` - Get prompt version history
   - `POST /api/v1/admin/search/text-ai/test` - Test prompt with sample query

4. **Search Providers**
   - `GET /api/v1/admin/search/providers` - List search providers
   - `POST /api/v1/admin/search/providers` - Add search provider
   - `PUT /api/v1/admin/search/providers/{id}` - Update provider config
   - `DELETE /api/v1/admin/search/providers/{id}` - Delete provider
   - `PUT /api/v1/admin/search/providers/order` - Update provider priority
   - `POST /api/v1/admin/search/providers/{id}/test` - Test provider

5. **Ingestion**
   - `GET /api/v1/admin/search/ingestion/config` - Get ingestion configuration
   - `PUT /api/v1/admin/search/ingestion/config` - Update ingestion configuration
   - `POST /api/v1/admin/search/ingestion/test` - Test ingestion with sample document
   - `GET /api/v1/admin/search/ingestion/queue` - Get ingestion queue status

6. **Monitoring**
   - `GET /api/v1/admin/search/metrics` - Get search performance metrics
   - `GET /api/v1/admin/search/logs` - Get filtered logs
   - `GET /api/v1/admin/search/traces/{id}` - Get specific request trace
   - `GET /api/v1/admin/search/alerts` - Get configured alerts
   - `PUT /api/v1/admin/search/alerts` - Update alert configuration

### Existing API Integration

1. **Text AI API**
   - Need endpoint to call Text AI model for prompt enhancement
   - If not available, create new endpoint: `POST /api/v1/text-ai/improve-prompt`

2. **Monitoring Stack**
   - Prometheus API for metrics
   - Loki API for logs
   - Grafana API for dashboards
   - Need appropriate proxy endpoints if not directly accessible

## Monitoring and Logging Requirements

### Performance Metrics

1. **Search Performance**
   - Average search time (overall)
   - Time breakdown by search phase
   - Cache hit/miss ratio
   - Results relevance scores
   - External provider usage rate

2. **Component Performance**
   - AnythingLLM query time
   - Text AI response time
   - External search provider response time
   - Content extraction time
   - Ingestion processing time

3. **Resource Usage**
   - Memory usage
   - CPU utilization
   - Network bandwidth
   - Storage utilization
   - Token usage (for AI models)

4. **Error Rates**
   - Overall error rate
   - Component-specific error rates
   - Timeout frequency
   - Retry counts
   - Circuit breaker status

### Logging Requirements

1. **Search Events**
   - Search requests (anonymized queries)
   - Search results summary
   - Decision points and outcomes
   - External provider usage
   - Cache operations

2. **Configuration Changes**
   - All configuration changes
   - User who made changes
   - Previous and new values
   - Configuration validation results

3. **Error Logs**
   - Detailed error information
   - Stack traces
   - Context information
   - Correlation IDs
   - Recovery actions

4. **Performance Logs**
   - Slow query logs
   - Resource exhaustion events
   - Timeouts
   - Rate limit hits

### Integration with Monitoring Stack

1. **Prometheus Integration**
   - Custom metrics for all search components
   - Histogram metrics for timing
   - Counter metrics for events
   - Gauge metrics for status
   - Alert rules for performance thresholds

2. **Loki Integration**
   - Structured logging format
   - Log level configuration
   - Label-based filtering
   - Context correlation
   - Log visualization

3. **Grafana Integration**
   - Embedded dashboards
   - Custom panels for search metrics
   - Alerting integration
   - Variable-based filtering
   - Template dashboards

## UI/UX Requirements

1. **Responsive Design**
   - Fully responsive layout
   - Mobile-friendly controls
   - Adaptive charts and tables

2. **Accessibility**
   - WCAG 2.1 AA compliance
   - Keyboard navigation
   - Screen reader support
   - Sufficient color contrast
   - Text zoom support

3. **User Experience**
   - Consistent layout and navigation
   - Contextual help and documentation
   - Input validation with clear error messages
   - Undo/redo for configuration changes
   - Auto-save drafts

4. **Performance**
   - Lazy loading of heavy components
   - Pagination for large data sets
   - Efficient data fetching
   - Optimistic UI updates
   - Background processing for heavy operations

## Security Requirements

1. **Access Control**
   - Role-based access to configuration
   - Audit logging of all changes
   - Sensitive data protection (API keys, credentials)
   - Configuration change approval workflow

2. **Data Protection**
   - Encryption of sensitive configuration
   - Masking of credentials in logs
   - Secure credential storage
   - No sensitive data in client-side storage

## Implementation Considerations

1. **Frontend Technologies**
   - React components consistent with existing admin-ui
   - Form validation using existing patterns
   - Chart components compatible with current libraries
   - Code editor component for prompt editing

2. **Backend Integration**
   - RESTful API following existing patterns
   - Consistent error handling
   - Proper validation
   - Appropriate caching

3. **Documentation**
   - Inline help text
   - Tooltip explanations
   - "Learn more" links to detailed documentation
   - Sample configurations

4. **Testing Requirements**
   - Unit tests for all components
   - Integration tests for API interactions
   - End-to-end tests for critical workflows
   - Performance testing

## Future Enhancements

1. **Advanced Analytics**
   - Search quality scoring
   - User satisfaction metrics
   - Knowledge gap analysis
   - A/B testing framework

2. **Machine Learning Optimization**
   - Automatic prompt optimization
   - Search parameter auto-tuning
   - Intelligent caching strategies
   - Anomaly detection

3. **Integration Expansion**
   - Additional search provider types
   - More vector database options
   - Custom content extractors
   - External knowledge base connections