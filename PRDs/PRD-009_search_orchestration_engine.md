# PRD-009: Search Orchestration Engine

## Overview
Specifies the core search workflow orchestrator. Manages the end-to-end process of a search query: cache check, vector search, AI evaluation, enrichment decision, and response compilation.

## Technical Boundaries
- High-level coordinator called by the /api/v1/search API endpoint.
- Invokes clients (AnythingLLM, LLM Provider) and business logic (Knowledge Enricher).
- No direct I/O or data transformation.

## Success Criteria
- Executes search workflow exactly as defined.
- Handles all decision points based on AI evaluation.
- Meets configured performance timeouts.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-001: HTTP API Foundation | Exposes search endpoint |
| PRD-002: Database & Caching Layer | Caches and retrieves search results |
| PRD-004: AnythingLLM Integration | Executes vector search |
| PRD-005: LLM Provider Integration | Evaluates search results |
| PRD-010: Knowledge Enrichment System | Triggers enrichment workflow |

## Cross-References
- Uses `CacheManager` from PRD-002 for caching.
- Calls `AnythingLLMClient` from PRD-004 for search.
- Calls `LLMProviderClient` from PRD-005 for evaluation.
- Triggers `KnowledgeEnricher` from PRD-010 for enrichment.

## Workflow Logic

1. **Query Normalization**: Lowercase, trim, hash.
2. **Cache Check**: Use query_hash to check Redis for SearchResponse.
3. **Multi-Workspace Search**: Execute intelligent workspace selection and parallel search.
4. **AI Evaluation**: Call llm_client.evaluate_search_results().
5. **Enrichment Decision**: Use EvaluationResult to decide on enrichment.
6. **Knowledge Enrichment**: Call enricher.enrich_knowledge() as background task.
7. **Response Compilation & Caching**: Format SearchResponse, cache, return.

## Multi-Workspace Handling Strategy

```python
class WorkspaceSearchStrategy:
    async def identify_relevant_workspaces(self, query: str, technology_hint: Optional[str] = None) -> List[WorkspaceInfo]:
        """
        Intelligent workspace selection based on query analysis.
        
        Strategy:
        1. If technology_hint provided, prioritize matching workspaces
        2. Extract technology keywords from query (e.g., "python", "react", "docker")
        3. Query database for workspace-technology mappings
        4. Default to searching all workspaces if no clear technology match
        5. Limit to max 5 workspaces for performance
        
        Returns workspaces ordered by relevance score
        """
        pass
    
    async def execute_parallel_search(self, query: str, workspaces: List[WorkspaceInfo]) -> List[SearchResult]:
        """
        Execute search across multiple workspaces in parallel.
        
        Process:
        1. Launch concurrent searches (max 5 simultaneous)
        2. Apply per-workspace timeout (2 seconds each)
        3. Collect results as they complete
        4. Handle individual workspace failures gracefully
        5. Aggregate and deduplicate results by content hash
        6. Apply technology-based ranking boost
        7. Return top 20 results across all workspaces
        """
        pass

class WorkspaceInfo(BaseModel):
    slug: str
    technology: str
    relevance_score: float
    last_updated: datetime
```

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| SO-001  | Implement SearchOrchestrator class |
| SO-002  | Implement execute_search workflow sequence |
| SO-003  | Integrate cache check using CacheManager |
| SO-004  | Aggregate and deduplicate results from workspaces |
| SO-005  | Implement enrichment decision matrix logic |
| SO-006  | Integrate BackgroundTasks for enrichment call |
| SO-007  | Enforce performance contracts with asyncio.wait_for |
| SO-008  | Connect orchestrator to live API endpoints |

## Integration Contracts
- Accepts normalized query and returns SearchResponse.
- Integrates with AnythingLLM, LLM Provider, and Knowledge Enricher.
- Caches results in Redis.

## Summary Tables

### Methods Table

| Method Name      | Description                                 | Returns           |
|------------------|---------------------------------------------|-------------------|
| execute_search   | Runs full search workflow                   | SearchResponse    |

### Dependencies Table

| Component        | Used For                                    |
|------------------|---------------------------------------------|
| CacheManager     | Caching search results                      |
| AnythingLLMClient| Vector search                               |
| LLMProviderClient| AI evaluation                               |
| KnowledgeEnricher| Enrichment workflow                         |

### Implementation Tasks Table
(see Implementation Tasks above)

---