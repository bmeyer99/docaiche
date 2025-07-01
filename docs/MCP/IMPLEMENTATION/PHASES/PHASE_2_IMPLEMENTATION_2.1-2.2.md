# Phase 2: Implementation (Business Logic Development)

## Phase Overview

**Duration**: Week 3-5  
**Objective**: Implement business logic within established scaffolding from Phase 1  
**ASPT Focus**: Medium Stitch reviews after each implementation to validate functionality, error handling, and test coverage  
**Agent Focus**: Single-domain implementation per task with comprehensive testing

## Context and Prerequisites

### What Was Built in Phase 1
- Complete scaffolding infrastructure in `/src/mcp/core/`
- Text AI service interfaces and prompt templates
- External search provider framework with health monitoring
- Configuration API endpoints (28 total) with validation
- Admin UI structure with all 7 tabs

### What We're Implementing in Phase 2
Transform the scaffolded interfaces into fully functional implementations:
- SearchOrchestrator with complete MCP workflow
- Text AI service with LLM integration
- Provider implementations for external search
- Configuration management with hot reload
- Admin UI functionality with real-time updates

### Key Implementation Principles
1. **Interface Adherence**: All implementations must strictly follow Phase 1 interfaces
2. **Comprehensive Testing**: 90%+ test coverage for all implementations
3. **Error Resilience**: Robust error handling with graceful degradation
4. **Performance Focus**: Meet all performance targets from PLAN.md
5. **Security Compliance**: Full validation and security controls

---

## Task 2.1: SearchOrchestrator Implementation

### Domain Focus
Core search orchestration logic implementing the complete MCP workflow

### Objective
Transform the SearchOrchestrator from Phase 1 into a fully functional implementation that executes all 10 phases of the MCP search workflow.

### Context from Phase 1
Phase 1 created the SearchOrchestrator interface in `/src/mcp/core/orchestrator.py` with method stubs for the complete workflow.

### Implementation Requirements

#### Main Search Method
Implement the primary search method that orchestrates the entire MCP workflow:
1. Track execution time and search path through all phases
2. Handle user context for personalization and rate limiting
3. Implement proper error handling at each phase
4. Ensure graceful degradation when components fail
5. Maintain search path audit trail for debugging

The method must coordinate all 10 workflow phases in sequence:
- Query normalization and caching check
- Workspace selection using Text AI
- Vector search execution with timeouts
- Result evaluation and potential refinement
- External search fallback if needed
- Content extraction and ingestion
- Response formatting and cache update

#### Query Normalization
Implement query preprocessing that:
- Cleans and standardizes query text
- Removes redundant whitespace and special characters
- Generates consistent hash for cache lookups
- Tokenizes query for search optimization
- Preserves original query for display

Include technology hint processing and query intent detection preparation.

#### Cache Management with Circuit Breaker
Implement cache checking that:
- Uses circuit breaker to prevent cascading failures
- Validates cache entries haven't expired
- Records success/failure for circuit breaker state
- Falls back gracefully when cache unavailable
- Tracks cache hit rates for monitoring

Cache updates must include:
- TTL based on configuration
- Proper serialization of response objects
- Atomic operations to prevent race conditions

#### Text AI Integration for Workspace Selection
Implement workspace selection that:
- Retrieves available workspaces from database
- Calls Text AI service to analyze query intent
- Matches workspaces based on technology, tags, and concepts
- Enforces maximum workspace limits
- Provides fallback when AI service unavailable
- Always returns at least one workspace if any exist

#### Vector Search Execution
Implement parallel vector search that:
- Creates async tasks for each workspace
- Enforces per-workspace timeouts
- Handles partial failures gracefully
- Cancels pending tasks on timeout
- Aggregates results from all workspaces
- Limits total results to configured maximum
- Tracks which workspaces failed for diagnostics

#### Result Evaluation and Refinement
Implement the evaluation flow that:
- Passes results to Text AI for relevance scoring
- Determines if refinement is needed
- Executes refined search if necessary
- Re-evaluates refined results
- Tracks refinement attempts to prevent loops

#### External Search Integration
Implement external search fallback that:
- Triggers based on evaluation thresholds
- Selects appropriate provider via provider registry
- Executes search with proper error handling
- Extracts content from external results
- Ingests new knowledge into vector database
- Maintains audit trail of external searches

#### Response Formatting
Implement response formatting that:
- Merges vector and external results
- Applies requested format (raw vs answer)
- Uses Text AI for answer generation
- Includes proper citations and sources
- Adds execution metadata and search path

#### Performance Optimization
Ensure implementation meets performance targets:
- Total search time under 2 seconds for cached results
- Vector search timeout enforcement
- Efficient result aggregation
- Minimal memory footprint
- Connection pooling for external calls

### ASPT Medium Stitch Review Checkpoint

**Review Focus:** Functionality, error handling, performance  
**Duration:** 10 minutes  

#### Validation Checklist:
- [ ] Main search method implements complete MCP workflow
- [ ] All 10 workflow phases are properly implemented
- [ ] Error handling covers all failure scenarios
- [ ] Timeout handling prevents hanging operations
- [ ] Circuit breaker pattern protects against cascading failures
- [ ] Performance meets targets (< 2s total search time)
- [ ] Logging provides adequate troubleshooting information
- [ ] Text AI integration follows established patterns
- [ ] Cache management includes proper expiration
- [ ] Resource limits are enforced (max workspaces, results)

### Deliverables
- Complete SearchOrchestrator implementation
- Full MCP workflow execution
- Robust error handling and timeout management
- Circuit breaker protection for external dependencies
- Comprehensive logging and monitoring integration
- Performance optimization for sub-2-second searches

### Handoff to Next Task
Task 2.2 will implement the Text AI service that the SearchOrchestrator depends on for intelligent decision-making.

---

## Task 2.2: Text AI Service Implementation

### Domain Focus
LLM integration for intelligent decision-making throughout the search workflow

### Objective
Implement the complete Text AI service with LLM integration, prompt management, and all 10 decision-making capabilities.

### Context from Previous Tasks
- Phase 1 created TextAIService interface with 10 decision methods
- Task 2.1 requires Text AI for workspace selection and result evaluation
- Prompt templates are defined but need LLM integration

### Implementation Requirements

#### LLM Client Integration
Create a flexible LLM client that:
- Supports multiple providers (OpenAI, Anthropic, local models)
- Handles authentication and configuration
- Implements retry logic with exponential backoff
- Enforces token limits and timeout constraints
- Tracks usage for cost monitoring
- Provides provider-specific optimizations

The client must handle:
- System prompts for consistent behavior
- Message formatting for different providers
- Response parsing and validation
- Error handling for API failures
- Token counting and truncation

#### Text AI Service Implementation
Implement all 10 decision methods with proper error handling:

**Query Analysis Implementation:**
- Parse LLM response into structured QueryAnalysis
- Handle malformed JSON responses gracefully
- Provide sensible defaults when AI fails
- Log analysis results for debugging
- Track confidence scores for quality monitoring

**Result Evaluation Implementation:**
- Prepare results for token-efficient evaluation
- Truncate snippets to prevent token overflow
- Parse evaluation into structured format
- Handle conservative fallbacks on failure
- Track evaluation accuracy over time

**Additional Decision Methods:**
Each of the remaining 8 methods must:
- Render appropriate prompt template
- Call LLM with proper configuration
- Parse response into expected format
- Handle errors with sensible defaults
- Track performance metrics
- Support A/B testing variants

#### Prompt Template Manager Implementation
Complete the template management system:
- Load templates from storage backend
- Cache active templates for performance
- Validate template variables before rendering
- Support Jinja2 template syntax
- Track template performance metrics
- Handle template versioning

Version management features:
- Create new versions with metadata
- Set active versions atomically
- Maintain version history
- Support rollback capabilities
- Track version performance

#### A/B Testing Implementation
Implement the A/B testing framework:
- Consistent user assignment to variants
- Traffic splitting based on configuration
- Outcome tracking with metrics
- Statistical significance calculation
- Automatic winner detection
- Test lifecycle management

The system must support:
- Multiple concurrent tests
- Different success metrics
- Minimum sample size enforcement
- Maximum duration limits
- Early stopping for clear winners

#### Error Handling and Fallbacks
Implement comprehensive error handling:
- Graceful degradation when LLM unavailable
- Sensible defaults for each decision type
- Retry logic for transient failures
- Circuit breaker for LLM endpoints
- Detailed error logging for debugging

#### Performance Optimization
Ensure Text AI service meets performance targets:
- Response caching for identical queries
- Parallel execution where possible
- Token optimization in prompts
- Connection pooling for API calls
- Timeout enforcement under 5 seconds

### ASPT Medium Stitch Review Checkpoint

**Review Focus:** LLM integration, decision accuracy, error handling  
**Duration:** 10 minutes  

#### Validation Checklist:
- [ ] LLM client handles multiple providers (OpenAI, Anthropic, etc.)
- [ ] All 10 Text AI decision methods are implemented
- [ ] Prompt templates are properly validated and rendered
- [ ] Error handling includes fallback responses
- [ ] Response parsing handles malformed JSON gracefully
- [ ] A/B testing framework tracks outcomes properly
- [ ] Token limits are respected in all prompts
- [ ] Retry logic prevents cascading failures
- [ ] Performance meets targets (<5s per decision)
- [ ] Cost tracking is implemented for LLM usage

### Deliverables
- Complete Text AI service with LLM integration
- All 10 decision-making methods implemented
- Robust prompt template management system
- A/B testing framework for prompt optimization
- Comprehensive error handling and fallback logic
- Cost and performance monitoring integration

### Handoff to Next Task
Task 2.3 will implement the external search providers that the Text AI service will select and the SearchOrchestrator will use for fallback searches.