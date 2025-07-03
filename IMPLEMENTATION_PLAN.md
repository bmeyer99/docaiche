# MCP Pipeline Implementation Checklist

## Overview
Based on comprehensive analysis of documentation and codebase, the MCP implementation is **mostly complete** but has key gaps that prevent the full 10-step pipeline from executing consistently.

## Expected Pipeline (10 Steps) - Current Status
- [x] 1. Request → MCP endpoint (IMPLEMENTED via `/api/v1/search`)
- [x] 2. API → Search Orchestrator (IMPLEMENTED in `orchestrator.py`)
- [x] 3. TextAI → optimized query (IMPLEMENTED but simple logic)
- [x] 4. Vector search execution → results (IMPLEMENTED via workspace strategy)
- [x] 5. TextAI evaluation → satisfaction check (IMPLEMENTED with basic scoring)
- [⚠️] 6. Decision: return/refine query/external search (CONDITIONAL - not always executed)
- [⚠️] 6a. TextAI refine query → retry (IMPLEMENTED but rarely triggered)
- [⚠️] 7. TextAI → external search query (ONLY when internal results poor)
- [⚠️] 8. External search results (CONDITIONAL execution)
- [⚠️] 9. Link retrieval → ingestion (BACKGROUND task, not in main flow)
- [x] 10. Final answer (IMPLEMENTED with formatting)

## Critical Implementation Gaps

### 🔴 **Gap 1: External Search Decision Logic**
**Problem**: External search only triggers when:
- Explicitly requested via `use_external_search=True`
- Internal results score < 0.6
- No internal results found

**Impact**: Steps 7-9 are often skipped when they should execute based on confidence scores

**Files to Modify**:
- `/src/search/orchestrator.py` (lines 281-298)
- `/src/mcp/text_ai/llm_adapter.py` (decision logic)

### 🟡 **Gap 2: TextAI Uses Simple Logic Instead of LLM**
**Problem**: Many TextAI methods use basic heuristics rather than actual LLM calls
- `should_use_external_search()` returns simple boolean
- `optimize_query()` does minimal transformation
- `refine_query()` adds basic terms

**Files to Modify**:
- `/src/mcp/text_ai/llm_adapter.py` (all decision methods)

### 🟡 **Gap 3: Knowledge Ingestion Not in Main Pipeline**
**Problem**: Step 9 (link retrieval → ingestion) runs as background task
- Not part of synchronous flow
- Results not immediately available

**Files to Modify**:
- `/src/search/orchestrator.py` (integrate ingestion)
- `/src/mcp/core/knowledge_manager.py` (if exists)

### 🟡 **Gap 4: Query Refinement Loop Not Triggering**
**Problem**: Refinement logic exists but rarely executes
- Threshold logic not properly implemented
- No retry mechanism for refined queries

**Files to Modify**:
- `/src/search/orchestrator.py` (refinement loop)
- `/src/mcp/text_ai/llm_adapter.py` (refinement decision)

## Implementation Tasks (Order of Execution)

### Task 1: Fix External Search Decision Logic
- [ ] Modify TextAI evaluation to properly score internal results
- [ ] Ensure external search triggers when confidence < 0.6
- [ ] Add comprehensive logging for all decision points
- [ ] Add metrics: decision_type, confidence_score, trigger_reason
- [ ] Test with various query types to verify proper triggering
- **Verification**: 
  - [ ] Log shows confidence scores for all searches
  - [ ] External search triggers for low-confidence results
  - [ ] Metrics capture decision branching
  - [ ] Integration tests pass

### Task 2: Implement Full LLM Integration for TextAI
- [ ] Replace simple heuristics with actual LLM calls
- [ ] Implement proper prompts for each of the 10 decision points
- [ ] Add timeout handling (100ms per decision)
- [ ] Implement fallback to heuristics on LLM failure
- [ ] Add metrics for LLM call performance
- **Verification**:
  - [ ] All 10 TextAI methods use LLM
  - [ ] Logs show LLM calls with timing
  - [ ] Fallback logic works on timeout
  - [ ] Performance stays under 50ms P95

### Task 3: Add Context7 Integration
- [ ] Create Context7Provider extending BaseMCPProvider
- [ ] Implement MCP stdio communication protocol
- [ ] Add resolve-library-id and get-library-docs tools
- [ ] Create direct documentation retrieval API endpoint
- [ ] Implement version tracking and update detection
- [ ] Add caching layer for Context7 responses
- **Verification**:
  - [ ] Context7 provider successfully initialized
  - [ ] Can fetch documentation for known libraries
  - [ ] Version tracking works correctly
  - [ ] Direct API endpoint returns raw docs
  - [ ] Ingestion happens on retrieval

### Task 4: Make Knowledge Ingestion Synchronous Option
- [ ] Add sync_ingestion configuration flag
- [ ] Create fast-path ingestion for critical content
- [ ] Modify orchestrator to wait for ingestion when sync mode
- [ ] Add ingestion status to search response
- [ ] Implement timeout handling for sync ingestion
- **Verification**:
  - [ ] Sync mode ingests before returning results
  - [ ] Async mode maintains current behavior
  - [ ] Ingestion status appears in response
  - [ ] Performance impact documented

### Task 5: Implement Query Refinement Loop
- [ ] Fix refinement trigger logic (0.4-0.8 confidence range)
- [ ] Implement retry mechanism with refined queries
- [ ] Add iteration limit (max 2 refinements)
- [ ] Track refinement attempts in metrics
- [ ] Log refinement decisions and results
- **Verification**:
  - [ ] Refinement triggers for medium confidence
  - [ ] Refined queries show improvement
  - [ ] Loop terminates after max iterations
  - [ ] Metrics show refinement rate

### Task 6: Add Comprehensive Pipeline Metrics
- [ ] Implement OpenTelemetry tracing for all 10 steps
- [ ] Add execution path logging with trace IDs
- [ ] Create step-level metrics:
  - [ ] Step execution counters
  - [ ] Step timing histograms
  - [ ] Decision branch tracking
  - [ ] Cache hit/miss per step
  - [ ] External provider performance
- [ ] Add WebSocket endpoint for real-time streaming
- [ ] Create pipeline visualization data structure
- **Verification**:
  - [ ] Every request has full trace
  - [ ] Metrics exported to Prometheus
  - [ ] WebSocket streams live data
  - [ ] Visualization data structure complete

## Detailed Verification Steps for Each Task

### Component Verification Checklist
- [ ] Component exists and is functional
- [ ] Integration points are properly connected
- [ ] Error handling is implemented
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Documentation updated
- [ ] Logs show expected behavior
- [ ] Metrics capture performance
- [ ] No regression in existing functionality

### End-to-End Verification
- [ ] Test: Query with high-confidence internal results (no external search)
- [ ] Test: Query with low-confidence results (triggers external search)
- [ ] Test: Query requiring refinement (0.4-0.8 confidence)
- [ ] Test: Context7 documentation retrieval
- [ ] Test: Synchronous ingestion flow
- [ ] Verify all 10 steps execute when appropriate
- [ ] Check response includes all expected data
- [ ] Validate performance meets targets
- [ ] Verify metrics pipeline captures all events

## Configuration Changes

### New Configuration Options
```yaml
mcp:
  pipeline:
    confidence_thresholds:
      high: 0.8      # Return internal results immediately
      medium: 0.4    # Trigger refinement
      low: 0.4       # Trigger external search
    sync_ingestion: false  # Synchronous knowledge ingestion
    max_refinements: 2     # Maximum refinement iterations
    
  text_ai:
    use_llm: true  # Use actual LLM vs heuristics
    fallback_to_heuristics: true  # Graceful degradation
    decision_timeout_ms: 100  # Fast decisions
    
  providers:
    context7:
      enabled: true
      command: "npx"
      args: ["-y", "@upstash/context7-mcp"]
      cache_ttl: 3600  # Cache docs for 1 hour
      version_check_interval: 86400  # Daily version checks
      
  metrics:
    opentelemetry:
      enabled: true
      endpoint: "http://localhost:4317"
      service_name: "docaiche-search"
    websocket:
      enabled: true
      port: 8765
      path: "/ws/pipeline"
```

## Logging Requirements

### Required Log Points
1. **Request Entry**: Query, workspace, request_id, session_id
2. **TextAI Decisions**: Decision type, input, output, timing, confidence
3. **Cache Operations**: Hit/miss, key, latency
4. **External Search**: Provider, query, result count, timing
5. **Refinement**: Original query, refined query, iteration
6. **Ingestion**: Source, document count, sync/async, timing
7. **Response**: Total time, steps executed, final result count

### Log Format
```json
{
  "timestamp": "2025-01-03T12:00:00Z",
  "trace_id": "abc123",
  "span_id": "def456",
  "service": "search-orchestrator",
  "step": "text_ai_evaluation",
  "duration_ms": 45,
  "attributes": {
    "confidence_score": 0.65,
    "decision": "use_external_search",
    "query": "python async programming"
  }
}
```

## Metrics Requirements

### Key Metrics to Track
1. **Pipeline Metrics**
   - `pipeline.request.total` - Total requests (counter)
   - `pipeline.request.duration` - Full pipeline duration (histogram)
   - `pipeline.step.duration` - Per-step duration (histogram)
   - `pipeline.step.executed` - Which steps ran (counter with labels)

2. **Decision Metrics**
   - `textai.decision.count` - Decisions by type (counter)
   - `textai.confidence.score` - Confidence distribution (histogram)
   - `textai.llm.calls` - LLM usage (counter)
   - `textai.llm.duration` - LLM latency (histogram)

3. **Search Metrics**
   - `search.internal.results` - Internal result count (histogram)
   - `search.external.results` - External result count (histogram)
   - `search.refinement.count` - Refinement attempts (counter)
   - `search.cache.hit_rate` - Cache effectiveness (gauge)

4. **Context7 Metrics**
   - `context7.fetch.duration` - Doc fetch time (histogram)
   - `context7.fetch.success` - Success rate (counter)
   - `context7.version.updates` - Version changes detected (counter)
   - `context7.cache.size` - Cached docs (gauge)

## Success Criteria

### Pipeline Completeness
- ✅ All 10 steps execute based on confidence scores
- ✅ External search enhances (not replaces) when appropriate
- ✅ Query refinement improves result quality
- ✅ Context7 provides real-time documentation
- ✅ Synchronous ingestion available when needed

### Performance Targets
- ✅ P95 latency < 200ms (with caching)
- ✅ External search adds < 100ms overhead
- ✅ LLM decisions complete in < 50ms
- ✅ Context7 fetch < 150ms
- ✅ Zero increase in error rates

### Observability
- ✅ Full request tracing available
- ✅ Real-time metrics streaming works
- ✅ Pipeline visualization data complete
- ✅ All decisions logged with reasoning

## Risk Mitigation

### Potential Issues & Solutions
1. **LLM Latency**: 
   - Aggressive 100ms timeout
   - Fallback to heuristics
   - Parallel LLM calls where possible

2. **External Search Failures**: 
   - Circuit breakers per provider
   - Cached fallback results
   - Hedged requests

3. **Context7 Availability**:
   - Local cache for popular docs
   - Graceful degradation
   - Background version checks

4. **Pipeline Complexity**: 
   - Comprehensive tracing
   - Step-by-step logging
   - Feature flags for gradual rollout

## Implementation Schedule

### Week 1
- Task 1: Fix External Search Decision Logic (2 days)
- Task 2: Implement Full LLM Integration (3 days)

### Week 2  
- Task 3: Add Context7 Integration (3 days)
- Task 4: Make Knowledge Ingestion Synchronous (2 days)

### Week 3
- Task 5: Implement Query Refinement Loop (2 days)
- Task 6: Add Comprehensive Pipeline Metrics (3 days)

### Week 4
- Integration testing
- Performance optimization
- Documentation updates
- Production rollout

## Next Steps

1. **Begin with Task 1** - Fix external search decision logic
2. **Daily progress updates** using the quick progress tracker
3. **Checkpoint after each task** for verification
4. **No scope creep** - Only implement what's listed
5. **Full system test** after all tasks complete