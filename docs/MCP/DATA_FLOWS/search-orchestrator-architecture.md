# SearchOrchestrator Architecture Flow

This document provides a detailed architectural overview of the SearchOrchestrator component, which is the core engine powering DocAIche's search functionality.

## Overview

The SearchOrchestrator implements a sophisticated search workflow with caching, parallel execution, fault tolerance, and optional AI enhancement. It coordinates multiple components to deliver fast, relevant search results across multiple documentation workspaces.

## Architecture Flow Diagram

```
SearchOrchestrator.search()
    ↓
execute_search()
    ├── 1. Query Normalization
    │   ├── Text Cleaning
    │   ├── Tokenization
    │   ├── Stemming
    │   └── Hash Generation
    │
    ├── 2. Cache Check (with Circuit Breaker)
    │   ├── Check Circuit Breaker Status
    │   ├── Redis Cache Lookup (if circuit closed)
    │   └── Return Cached Results (on hit)
    │
    ├── 3. Multi-Workspace Search
    │   ├── Identify Relevant Workspaces
    │   ├── Execute Parallel Search (max 5 concurrent)
    │   ├── Per-Workspace Timeout (2s)
    │   └── AnythingLLM Vector Search
    │
    ├── 4. Result Aggregation
    │   ├── Collect All Results
    │   ├── Handle Failed Searches
    │   └── Deduplicate by Content Hash
    │
    ├── 5. Result Ranking
    │   ├── Technology Boost
    │   ├── Relevance Scoring
    │   └── Apply Limit/Offset
    │
    ├── 6. AI Evaluation (Optional)
    │   ├── Check LLM Client Availability
    │   ├── Evaluate Results Quality
    │   └── Generate Enrichment Recommendations
    │
    ├── 7. Enrichment Decision
    │   ├── Check if Enrichment Needed
    │   └── Trigger Background Task
    │
    ├── 8. Cache Results
    │   ├── Check Circuit Breaker
    │   └── Store in Redis
    │
    └── 9. Return SearchResults
```

## Detailed Component Breakdown

### 1. Query Normalization (`_normalize_query`)

Transforms raw user queries into standardized format for consistent searching.

```python
Input: "Python Async Programming!"
Process:
  - Lowercase: "python async programming!"
  - Clean text: Remove special characters
  - Tokenize: ["python", "async", "programming"]
  - Stem: ["python", "async", "program"]
  - Generate hash: "a1b2c3d4..."
Output: Normalized SearchQuery object
```

### 2. Cache Management with Circuit Breaker

Implements resilient caching with automatic failure recovery.

**Circuit Breaker States:**
- **CLOSED**: Normal operation, all requests go through
- **OPEN**: Too many failures, bypass cache temporarily
- **HALF-OPEN**: Testing if service recovered

**Configuration:**
- Failure threshold: 3 consecutive failures
- Initial backoff: 2 seconds
- Max backoff: 30 seconds
- Auto-recovery: Test after backoff period

### 3. Multi-Workspace Search Strategy

Intelligently selects and searches relevant workspaces in parallel.

```python
WorkspaceSearchStrategy.execute_parallel_search()
├── Workspace Selection
│   ├── Query database for workspace metadata
│   ├── Match by technology patterns
│   └── Score by relevance (0-1)
│
├── Parallel Execution
│   ├── Semaphore(5) - max concurrent searches
│   ├── Per-workspace timeout: 2 seconds
│   └── asyncio.gather() with exception handling
│
└── Individual Workspace Search
    ├── AnythingLLMClient.search_workspace()
    ├── HTTP POST to AnythingLLM service
    └── Vector similarity search
```

### 4. Result Processing Pipeline

Transforms raw search results into ranked, deduplicated output.

```python
Raw Results → Processed SearchResults

1. Aggregation
   - Combine results from all workspaces
   - Track successful vs failed searches
   - Handle partial failures gracefully

2. Deduplication
   - Generate content hash for each result
   - Remove duplicates across workspaces
   - Preserve highest relevance score

3. Ranking (ResultRanker)
   - Base relevance score from vector search
   - Technology match boost (+0.2)
   - Workspace quality factor
   - Sort by final score descending
```

### 5. Optional AI Enhancement

When an LLM client is available, evaluates and enhances results.

```python
if llm_client:
    evaluation = await _evaluate_with_llm()
    Returns:
    - overall_quality: 0.0-1.0
    - relevance_assessment: 0.0-1.0
    - completeness_score: 0.0-1.0
    - needs_enrichment: boolean
    - enrichment_topics: list of topics
else:
    # Mock evaluation based on result count
    # Returns simplified evaluation
```

### 6. Background Enrichment

Triggers asynchronous content enrichment when needed.

```python
if evaluation.needs_enrichment and background_tasks:
    background_tasks.add_task(
        knowledge_enricher.enrich_knowledge,
        query=query,
        topics=evaluation.enrichment_topics
    )
```

## Key Design Patterns

### Circuit Breaker Pattern
```python
class CacheCircuitBreaker:
    - failure_count: int
    - is_open: bool
    - backoff_seconds: float
    - next_attempt_time: float
    
    def on_success():
        reset_failures()
        close_circuit()
    
    def on_failure():
        increment_failures()
        if failures >= threshold:
            open_circuit()
            calculate_backoff()
```

### Bulkhead Pattern
```python
# Isolate failures between workspaces
semaphore = asyncio.Semaphore(5)

async with semaphore:
    # Each workspace search is isolated
    # Failure in one doesn't affect others
```

### Timeout Pattern
```python
# Prevent hanging requests
await asyncio.wait_for(
    search_coro,
    timeout=2.0  # Per workspace
)
# Overall timeout: 30 seconds
```

### Cache-Aside Pattern
```python
# 1. Check cache
cached = await cache.get(key)
if cached:
    return cached

# 2. Compute if miss
result = await compute_result()

# 3. Store for future
await cache.set(key, result, ttl=3600)
return result
```

## Error Handling Strategy

```python
try:
    # Normal search flow
    results = await search()
    
except SearchTimeoutError:
    # Return partial results if available
    logger.warning("Search timed out, returning partial results")
    return partial_results
    
except VectorSearchError:
    # Return empty results with error metadata
    logger.error("Vector search failed")
    return SearchResults(
        results=[],
        error="Search service unavailable"
    )
    
except Exception as e:
    # Log and wrap in SearchOrchestrationError
    logger.error(f"Unexpected error: {e}")
    raise SearchOrchestrationError(str(e))
```

## Performance Characteristics

### Response Times
- **Cache Hit**: 5-10ms
- **Single Workspace**: 100-200ms
- **Multiple Workspaces**: 200-500ms
- **Worst Case (timeout)**: 2000ms

### Concurrency Limits
- **Max parallel searches**: 5
- **Per-workspace timeout**: 2 seconds
- **Overall timeout**: 30 seconds

### Cache Configuration
- **TTL**: 1 hour (3600 seconds)
- **Key**: SHA256 hash of normalized query
- **Storage**: Redis

## Observability

### Logging Points
```python
# Query processing
INFO: "Starting search orchestration for query: {query}"
DEBUG: "Normalized query: {normalized}"

# Cache operations
INFO: "Cache hit - returning {count} results"
WARNING: "Cache check failed, continuing without cache"

# Workspace search
INFO: "Executing parallel search across {count} workspaces"
DEBUG: "Workspace {name} search completed: {results} results"
WARNING: "Search timeout in workspace {name}"

# Results
INFO: "Search completed: {success} successful, {failed} failed"

# Performance
INFO: "Total search time: {time}ms"
```

### Metrics
- Query execution time
- Cache hit rate
- Workspace search success rate
- Circuit breaker state changes
- Enrichment trigger rate

## Configuration

```python
# Circuit Breaker
CB_FAILURE_THRESHOLD = 3
CB_INITIAL_BACKOFF = 2.0  # seconds
CB_MAX_BACKOFF = 30.0     # seconds

# Search Limits
MAX_CONCURRENT_SEARCHES = 5
WORKSPACE_TIMEOUT = 2.0    # seconds
OVERALL_TIMEOUT = 30.0     # seconds

# Cache
CACHE_TTL = 3600          # 1 hour
CACHE_KEY_PREFIX = "search:results:"
```

## Resilience Features

1. **Graceful Degradation**
   - Works without cache (Redis down)
   - Works without LLM (AI evaluation)
   - Partial results on timeout

2. **Fault Isolation**
   - Workspace failures isolated
   - Cache failures don't block search
   - Background tasks don't affect response

3. **Self-Healing**
   - Circuit breaker auto-recovery
   - Exponential backoff
   - Health monitoring

The SearchOrchestrator is designed to be resilient, performant, and observable, providing reliable search functionality even when external dependencies fail.