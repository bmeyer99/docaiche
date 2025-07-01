**CONTINUATION OF PHASE_1_SCAFFOLDING_1.1-1.3.md**

## Task 1.4: Configuration API Scaffold

### Domain Focus
API endpoints for managing all search system configuration with validation and audit trails

### Objective
Create comprehensive REST API for configuring the entire MCP search system with proper validation, audit logging, and hot reload capabilities.

### Context from Previous Tasks
- Configuration schemas from Tasks 1.1-1.3 need API endpoints
- All 28 API endpoints from PLAN.md must be implemented
- UI will consume these APIs for configuration management

### Implementation Requirements

#### Router Structure
Create API router structure under `/src/api/v1/admin/search/`

#### Configuration Management Endpoints
Core configuration endpoints to implement:
- `GET /api/v1/admin/search/config` - Retrieve current search configuration
- `PUT /api/v1/admin/search/config` - Update search configuration with validation
- `GET /api/v1/admin/search/config/history` - Configuration change history
- `POST /api/v1/admin/search/config/validate` - Validate without saving
- `POST /api/v1/admin/search/config/export` - Export configuration
- `POST /api/v1/admin/search/config/import` - Import configuration

Queue configuration endpoints:
- `GET/PUT /api/v1/admin/search/config/queues` - Queue settings management
- `GET/PUT /api/v1/admin/search/config/timeouts` - Timeout configurations

#### Vector Search Configuration
AnythingLLM integration endpoints:
- `GET /api/v1/admin/search/vector/status` - Connection status and health
- `GET/PUT /api/v1/admin/search/vector/connection` - Connection settings
- `POST /api/v1/admin/search/vector/test` - Test connection functionality

Workspace management:
- Full CRUD operations for workspaces
- Technology mapping configuration
- Search parameter settings

#### Text AI Configuration
Model configuration endpoints:
- `GET /api/v1/admin/search/text-ai/status` - AI service status
- `GET/PUT /api/v1/admin/search/text-ai/model` - Model configuration

Prompt management:
- List all prompts with versions
- Get/update specific prompts
- AI-powered prompt enhancement
- Prompt version history
- Test prompts with sample data

#### Provider Configuration
Provider management endpoints:
- List all providers with health status
- Add/update/delete providers
- Update provider priorities
- Test provider connectivity
- Monitor provider health

#### Monitoring and Metrics
Metrics endpoints:
- Search performance metrics
- Provider usage metrics
- Queue depth monitoring
- Filtered log access
- Request trace retrieval

Alert management:
- Active alert monitoring
- Alert configuration updates

#### Request/Response Models
Define Pydantic models for:
- All request payloads with validation
- Response formats with examples
- Error response schemas
- Configuration update models

Validation features:
- Range validation for numeric parameters
- Dependency validation between fields
- Custom validators for complex rules
- Helpful error messages with context

#### Router Integration
Main router setup requirements:
- Include all sub-routers
- Common middleware (auth, logging, rate limiting)
- Error handling and standardization
- OpenAPI documentation generation

### ASPT Shallow Stitch Review Checkpoint

**Review Focus:** API completeness, validation, documentation  
**Duration:** 10 minutes  

#### Validation Checklist:
- [ ] All 28 API endpoints from PLAN.md are defined
- [ ] Each endpoint has proper HTTP method and path
- [ ] Request/response models use Pydantic with validation
- [ ] All configuration parameters are exposed via API
- [ ] Validation rules match configuration schemas from Tasks 1.1-1.3
- [ ] Error responses have consistent format
- [ ] OpenAPI documentation is complete with examples
- [ ] Authentication and authorization are properly integrated
- [ ] Rate limiting is applied to appropriate endpoints
- [ ] Audit logging is planned for all configuration changes

### Deliverables
- Complete REST API for search system configuration
- All 28 endpoints with proper validation
- Pydantic models for all requests/responses
- OpenAPI documentation with examples
- Error handling and audit logging framework
- Integration points for hot configuration reload

### Handoff to Next Task
Task 1.5 will build the admin UI that will consume these APIs to provide a user-friendly configuration interface.

---

## Task 1.5: Admin UI Page Structure Scaffold

### Domain Focus
User interface components for search system configuration with real-time updates

### Objective
Create the complete admin UI structure for search configuration with all 7 tabs, form components, and WebSocket integration for real-time updates.

### Context from Previous Tasks
- Configuration APIs from Task 1.4 need UI consumption
- All configuration schemas from Tasks 1.1-1.3 need form interfaces
- Existing admin UI framework provides base components and navigation

### Implementation Requirements

#### Navigation Integration
Update the existing navigation to include Search Configuration section with:
- Main dashboard link
- Vector Search configuration
- Text AI configuration
- Search Providers management
- Ingestion rules
- Monitoring dashboards
- System settings

Include keyboard shortcuts and proper icons for each section.

#### Main Layout Component
Create the search configuration layout with:
- Tabbed navigation matching the mockup design
- Breadcrumb navigation for context
- Real-time status indicators
- Save/discard change notifications
- Help tooltips and documentation links
- Responsive design for mobile and desktop

#### Dashboard Tab Component
SearchConfigDashboard features:
- Real-time metrics cards (queue depth, search times, cache hit rate)
- System health status matrix showing all components
- Recent search activity table with filtering
- Provider health indicators with status badges
- Quick action buttons for common tasks
- Performance charts (search volume, latency trends)

#### Vector Search Tab
VectorSearchConfig features:
- AnythingLLM connection configuration form
- Connection test button with real-time results
- Workspace management table with CRUD operations
- Technology mapping interface (drag-drop or multi-select)
- Search parameter configuration (similarity threshold, max results)
- Live search testing interface with result preview

#### Text AI Tab
TextAIConfig features:
- Model selection dropdown with capability display
- Parameter configuration (temperature, max tokens, timeout)
- Prompt template editor with syntax highlighting
- Template variable documentation and autocomplete
- Prompt version history timeline view
- A/B test configuration interface
- "Enhance with AI" button for prompt improvement
- Prompt testing interface with sample data

#### Search Providers Tab
SearchProvidersConfig features:
- Provider cards with enable/disable toggles
- Drag-and-drop priority ordering
- Provider-specific configuration modals
- Rate limit configuration with visual indicators
- Cost tracking displays and budget limits
- Health status indicators with last check time
- Test interface for each provider

#### Additional Tabs Structure
**Ingestion Tab:**
- Rule builder interface for content ingestion
- Workspace assignment configuration
- Quality threshold settings
- Schedule configuration with cron-like UI

**Monitoring Tab:**
- Embedded Grafana dashboards
- Log explorer with advanced filtering
- Alert configuration interface
- Custom dashboard builder

**Settings Tab:**
- Global system settings forms
- Import/export configuration
- System maintenance controls
- Feature flag toggles

#### Shared Components
Create reusable components:

**Form Components:**
- `ConfigurationForm` - Base form with validation
- `ParameterSlider` - Range inputs with visual feedback
- `ProviderCard` - Reusable provider display
- `HealthIndicator` - Status display component
- `MetricCard` - Real-time metric display

**Data Components:**
- `ConfigurationTable` - Sortable configuration lists
- `HealthMatrix` - System health overview
- `ActivityFeed` - Recent activity display
- `ChartContainer` - Chart wrapper with real-time updates

#### TypeScript Interfaces
Define all TypeScript interfaces for:
- Configuration types matching API schemas
- Form state management types
- WebSocket message types
- Component prop interfaces
- Validation error types

#### WebSocket Integration
Create WebSocket hooks for:
- Configuration change notifications
- System health updates
- Queue depth monitoring
- Provider status changes
- Metric updates for dashboard
- Activity feed updates

### ASPT Shallow Stitch Review Checkpoint

**Review Focus:** Component structure, navigation, interface design  
**Duration:** 10 minutes  

#### Validation Checklist:
- [ ] Navigation properly integrates with existing sidebar
- [ ] All 7 tab components are created with proper structure
- [ ] TypeScript interfaces match API schemas exactly
- [ ] WebSocket hooks are properly typed
- [ ] Form components have validation integration
- [ ] Real-time updates are planned for appropriate data
- [ ] Component naming follows existing conventions
- [ ] Import/export statements are correct
- [ ] Responsive design considerations are included
- [ ] Accessibility features are planned (ARIA labels, keyboard nav)

### Deliverables
- Complete admin UI structure for search configuration
- All 7 tab components with proper layouts
- Navigation integration with existing admin UI
- TypeScript interfaces for all configuration types
- WebSocket integration for real-time updates
- Reusable form and display components
- Responsive design structure

### Handoff to Phase 2
Phase 2 will implement the actual functionality for all the scaffolded components, starting with the SearchOrchestrator implementation that ties together all the frameworks built in Phase 1.

---

## Phase 1 Completion Criteria

### Overall Success Metrics
- [ ] All 5 tasks completed with Shallow Stitch reviews passed
- [ ] Complete scaffolding for core infrastructure, Text AI service, providers, APIs, and UI
- [ ] All configuration parameters properly exposed and validated
- [ ] Clear interfaces established between all components
- [ ] Comprehensive error handling framework in place
- [ ] Documentation complete for all scaffolded components

### Phase 1 Artifacts
1. **Core Infrastructure** - Complete configuration and orchestrator framework
2. **Text AI Service** - All decision interfaces and prompt management
3. **Provider Framework** - Pluggable provider system with health monitoring
4. **Configuration API** - All 28 endpoints with validation
5. **Admin UI Structure** - Complete interface for configuration management

### Technical Debt and Notes
- All TODO comments should reference Phase 2 implementation
- Configuration validation rules may need refinement during implementation
- Provider interface may need additions based on real-world provider requirements
- UI components will need styling and interaction polish in Phase 2

### Known Dependencies for Phase 2
- LLM client integration for Text AI service
- AnythingLLM client for vector search
- External provider API credentials for testing
- Database schema for configuration storage
- Redis setup for queue management

This completes Phase 1 scaffolding. Phase 2 will implement all the business logic within these established frameworks.