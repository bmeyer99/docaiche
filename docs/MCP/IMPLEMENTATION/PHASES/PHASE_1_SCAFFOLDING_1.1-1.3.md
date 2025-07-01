# Phase 1: Scaffolding (Foundation Building)

## Phase Overview

**Duration**: Week 1-2  
**Objective**: Create complete structural foundation with interfaces, contracts, and frameworks  
**ASPT Focus**: Shallow Stitch reviews after each component to validate syntax, interfaces, and documentation  
**Agent Focus**: Single-domain concentration per task with clear handoff points

## Context and Prerequisites

### What Exists Currently
- Existing MCP endpoint at `/src/api/v1/mcp/` with basic JSON-RPC handler
- Mock search tool implementation returning fake data
- Basic search orchestrator at `/src/search/orchestrator.py`
- Admin UI framework with WebSocket analytics
- Existing monitoring stack: Loki/Grafana/Prometheus
- Redis-based queue system for document processing

### What We're Building
A complete MCP search system that replaces the mock implementation with:
- Intelligent Text AI decision-making service
- External search provider framework
- Configurable queue management with overload protection
- Comprehensive admin UI for search configuration
- Full observability and monitoring integration

### Key Design Principles
1. **API-First**: Every configuration must be accessible via API
2. **Full Configurability**: All thresholds, limits, and behaviors configurable via UI
3. **Performance Monitoring**: Comprehensive metrics from day one
4. **No Backwards Compatibility**: Build for MCP search as primary function
5. **Rip and Replace**: Remove redundant code without hesitation

---

## Task 1.1: Core MCP Search Infrastructure Scaffold

### Domain Focus
Core search orchestration infrastructure and configuration management

### Objective
Establish the foundational classes and interfaces for the entire MCP search system with all configurable parameters properly exposed.

### Implementation Requirements

#### Directory Structure
Create the core MCP directory structure under `/src/mcp/` with appropriate module organization:
- `core/` - Core infrastructure and orchestration
- `text_ai/` - Text AI service components
- `providers/` - External search providers
- `__init__.py` files for all directories

#### Configuration Schema
Define a comprehensive SearchConfiguration class with all parameters from PLAN.md:
- Queue management parameters (max concurrent searches, queue depth, overflow response)
- Rate limiting parameters (per-user, per-workspace limits)
- Timeout configurations (total search, workspace search, external search, AI decision)
- Performance thresholds (cache circuit breaker, relevance scores)
- Resource limits (max results, workspaces, tokens)

Each parameter must include:
- Type annotations and validation constraints
- Default values matching PLAN.md specifications
- Descriptive field documentation
- Dependency relationships between parameters

#### Search Orchestrator Base Class
Create the SearchOrchestrator abstract base class with methods for each MCP workflow phase:
1. `search()` - Main entry point accepting query, technology hint, response type, and user context
2. `_normalize_query()` - Query preprocessing and consistent hashing
3. `_check_cache()` - Cache lookup with circuit breaker protection
4. `_select_workspaces()` - AI-driven workspace selection based on query analysis
5. `_execute_vector_search()` - Parallel AnythingLLM queries with timeout management
6. `_evaluate_results()` - AI assessment of result relevance and completeness
7. `_refine_query()` - AI-powered query improvement when results insufficient
8. `_execute_external_search()` - Provider selection and external search execution
9. `_extract_content()` - AI extraction of relevant content from sources
10. `_ingest_knowledge()` - Learning loop implementation for knowledge base updates
11. `_format_response()` - Response formatting based on requested type (raw/answer)
12. `_update_cache()` - Result caching with TTL management

#### Queue Management Interfaces
Define abstract interfaces for queue management:

**QueueManager Interface:**
- Enqueue requests with overflow protection
- Dequeue by priority
- Monitor queue depth and statistics
- Check overload status
- Enforce rate limits per user and workspace

**PriorityQueue Interface:**
- Priority-based request ordering
- User/workspace prioritization logic
- Overflow handling with 503 responses

#### Error Handling Framework
Create comprehensive exception hierarchy:
- `MCPSearchError` - Base exception with error codes and structured details
- `QueueOverflowError` - Queue capacity exceeded with retry information
- `RateLimitExceededError` - User/workspace limits exceeded
- `SearchTimeoutError` - Various timeout scenarios
- `ProviderError` - External provider failures
- `TextAIError` - AI service failures
- `ConfigurationError` - Invalid configuration states

#### Data Models
Define all data structures for the search system:
- `NormalizedQuery` - Processed query with metadata and hash
- `SearchRequest` - Request with context, priority, and tracking
- `VectorSearchResults` - AnythingLLM response aggregation
- `EvaluationResult` - AI relevance assessment with confidence
- `SearchResponse` - Final response with execution metadata
- `UserContext` - User session and permission information
- `QueueStats` - Queue monitoring metrics

### ASPT Shallow Stitch Review Checkpoint

**Review Focus:** Structure, interfaces, documentation  
**Duration:** 10 minutes  

#### Validation Checklist:
- [ ] All directory structures created correctly
- [ ] SearchConfiguration includes ALL parameters from PLAN.md
- [ ] Parameter validation ranges match specifications exactly
- [ ] All SearchOrchestrator methods have proper signatures and docstrings
- [ ] Queue interfaces support priority and rate limiting
- [ ] Exception hierarchy covers all error scenarios
- [ ] Data models have complete type annotations
- [ ] All classes have comprehensive docstrings
- [ ] Import statements are correct and circular imports avoided
- [ ] Naming conventions are consistent (snake_case/PascalCase)

### Deliverables
- Complete `/src/mcp/core/` module structure
- Fully defined configuration schema with all parameters
- Search orchestrator interface with all MCP workflow methods
- Queue management interfaces with overflow protection
- Comprehensive error handling framework
- All data models for the search system

### Handoff to Next Task
Task 1.2 will build the Text AI decision service that the SearchOrchestrator will use for all intelligent decision-making.

---

## Task 1.2: Text AI Decision Service Scaffold

### Domain Focus
Text AI service for intelligent decision-making throughout the search workflow

### Objective
Create the complete Text AI service framework with all 10 decision prompts, template management, and A/B testing infrastructure.

### Context from Previous Task
The SearchOrchestrator from Task 1.1 expects a TextAIService that can make intelligent decisions at various points in the search workflow.

### Implementation Requirements

#### Directory Structure
Create the Text AI service structure under `/src/mcp/text_ai/`

#### Prompt Templates Definition
Define all 10 decision prompts from mcp_search_decision_prompts.md:

1. **Query Understanding** - Analyze intent, domain, entities, and suggest workspaces
2. **Result Relevance Evaluation** - Score results and assess completeness
3. **Query Refinement** - Generate improved queries based on missing information
4. **External Search Decision** - Determine if external search is needed
5. **External Search Query Generation** - Optimize queries for specific providers
6. **Content Extraction** - Extract relevant sections from documents
7. **Response Format Selection** - Choose between raw results and formatted answers
8. **Learning Opportunity Identification** - Find knowledge gaps for ingestion
9. **Search Provider Selection** - Choose optimal provider based on context
10. **Search Failure Analysis** - Understand failures and provide recommendations

Each prompt must include:
- Exact text from documentation with variable placeholders
- Metadata about expected variables and output format
- Validation schemas for prompt responses
- Clear instructions for AI interpretation

#### TextAI Service Interface
Define the TextAIService abstract class with methods corresponding to each decision:
- `analyze_query()` - Returns QueryAnalysis with intent, domain, entities
- `evaluate_relevance()` - Returns EvaluationResult with scores and completeness
- `refine_query()` - Returns improved query string
- `decide_external_search()` - Returns ExternalSearchDecision with reasoning
- `generate_search_query()` - Returns provider-optimized query
- `extract_content()` - Returns ExtractedContent with relevant sections
- `select_response_format()` - Returns FormattedResponse based on type
- `identify_learning_opportunities()` - Returns LearningOpportunities
- `select_provider()` - Returns provider ID with selection reasoning
- `analyze_failure()` - Returns FailureAnalysis with recommendations

#### Prompt Template Manager
Create template management system with:
- Version control for all prompt templates
- Template variable validation
- Active/inactive version management
- Performance metrics tracking per template
- Import/export functionality
- Template rendering with variable substitution

#### Data Models for Text AI
Define response models for each decision:
- `QueryAnalysis` - Intent, domain, entities, workspace suggestions
- `EvaluationResult` - Relevance score, completeness, missing information
- `ExternalSearchDecision` - Boolean decision with reasoning and confidence
- `ExtractedContent` - Relevant sections, summaries, code examples
- `FormattedResponse` - Type-specific formatting with citations
- `LearningOpportunities` - Knowledge gaps and suggested sources
- `FailureAnalysis` - Failure reasons, limitations, recommendations

Supporting models:
- `PromptTemplate` - Template with metadata and variable definitions
- `TemplateVersion` - Version information with performance metrics
- `ValidationResult` - Template validation outcomes

#### A/B Testing Framework
Define A/B testing infrastructure:
- Test configuration with variants and traffic splitting
- User assignment logic for consistent testing
- Outcome tracking and metrics collection
- Statistical analysis interfaces
- Test lifecycle management (create, run, conclude)

### ASPT Shallow Stitch Review Checkpoint

**Review Focus:** Interface completeness, prompt accuracy, documentation  
**Duration:** 10 minutes  

#### Validation Checklist:
- [ ] All 10 prompt templates present and match documentation exactly
- [ ] Template variables use consistent naming ({query}, {results_json})
- [ ] TextAIService has all 10 decision methods with proper signatures
- [ ] PromptTemplateManager supports version control and validation
- [ ] A/B testing framework has statistical methods
- [ ] All data models have proper type annotations and field validation
- [ ] Abstract methods have clear docstrings with input/output specs
- [ ] Prompt templates include expected output format specifications
- [ ] Template variable validation can detect missing variables
- [ ] All response models match expected JSON structures from prompts

### Deliverables
- Complete Text AI service interface with all 10 decision methods
- All prompt templates exactly from MCP documentation
- Prompt template management with versioning
- A/B testing framework for prompt optimization
- Complete data models for all AI responses
- Template validation and rendering system

### Handoff to Next Task
Task 1.3 will build the external search provider framework that the TextAI service will use for provider selection and the SearchOrchestrator will use for external searches.

---

## Task 1.3: External Search Provider Framework Scaffold

### Domain Focus
External search provider abstraction, health monitoring, and fallback mechanisms

### Objective
Create a pluggable framework for external search providers with health monitoring, circuit breakers, and standardized result formatting.

### Context from Previous Tasks
- SearchOrchestrator (Task 1.1) needs provider fallback when vector search insufficient
- TextAI service (Task 1.2) needs provider selection capabilities

### Implementation Requirements

#### Directory Structure
Create the provider framework under `/src/mcp/providers/`

#### Base Provider Interface
Define SearchProvider abstract class with:
- `search()` - Execute search with standardized options
- `get_capabilities()` - Return provider features and limitations
- `check_health()` - Provider health status check
- `get_rate_limits()` - Current rate limit information
- `get_cost_info()` - Usage and cost tracking data
- `validate_config()` - Configuration validation

Built-in features to include:
- Circuit breaker pattern integration
- Automatic health monitoring hooks
- Rate limit enforcement mechanisms
- Cost tracking and budget limits
- Result standardization interface

#### Provider Registry
Create ProviderRegistry for managing multiple providers:
- Dynamic provider registration and unregistration
- Priority-based ordering (supports UI drag-drop)
- Health-based availability filtering
- Provider selection algorithms
- Failover chain management
- Performance-based routing

#### Provider Implementations
Create implementation scaffolds for each provider:

**Brave Search:**
- API authentication handling
- Query optimization for Brave's format
- Result parsing and standardization
- Rate limiting specific to Brave's limits
- Cost tracking based on usage

**Google Custom Search:**
- Custom Search API integration setup
- Domain-specific search configuration
- Result formatting from Google's response
- Quota management for daily limits

**Additional Providers (Bing, DuckDuckGo, SearXNG):**
- Similar structure to Brave implementation
- Provider-specific query optimizations
- Unified result format transformation

#### Data Models
Define provider-related data structures:

**Search Models:**
- `SearchOptions` - Query parameters, filters, language, date range
- `SearchResult` - Standardized result format across providers
- `SearchResults` - Collection with metadata and execution time
- `ProviderCapabilities` - Feature support and limitations

**Monitoring Models:**
- `HealthStatus` - Provider health enumeration
- `RateLimitInfo` - Current rate limit status
- `CostInfo` - Usage and cost tracking
- `HealthCheck` - Health check result with timestamp

#### Health Monitoring System
Create ProviderHealthMonitor with:
- Periodic health check scheduling (configurable intervals)
- Health history tracking and trending
- Failure pattern detection algorithms
- Recovery monitoring and alerts
- Health metrics calculation and export

Circuit breaker integration:
- Automatic circuit opening on consecutive failures
- Configurable failure thresholds
- Recovery timeout management
- Health-based circuit state control

#### Configuration Schemas
Define JSON schemas for each provider:
- Required and optional configuration fields
- Validation rules for API keys and endpoints
- Default values and acceptable ranges
- Provider-specific parameter definitions
- Configuration migration support

### ASPT Shallow Stitch Review Checkpoint

**Review Focus:** Interface design, provider abstraction, configuration  
**Duration:** 10 minutes  

#### Validation Checklist:
- [ ] SearchProvider interface has all required abstract methods
- [ ] Provider registry supports priority ordering and health filtering
- [ ] All provider implementations follow the same interface pattern
- [ ] Health monitoring has configurable check intervals
- [ ] Circuit breaker pattern is properly integrated
- [ ] Configuration schemas validate all required fields
- [ ] Result standardization works across all providers
- [ ] Rate limiting and cost tracking are provider-agnostic
- [ ] Error handling covers all provider failure scenarios
- [ ] Health metrics can be exported to monitoring systems

### Deliverables
- Complete provider abstraction framework
- Provider registry with health-based selection
- Implementation scaffolds for 5 search providers
- Health monitoring with circuit breaker integration
- Configuration validation schemas
- Standardized result format across providers

### Handoff to Next Task
Task 1.4 will build the configuration API that will manage all the configuration schemas defined in Tasks 1.1-1.3.

**CONTINUE PHASE 1 IN PHASE_1_SCAFFOLDING_1.4-1.5.md**