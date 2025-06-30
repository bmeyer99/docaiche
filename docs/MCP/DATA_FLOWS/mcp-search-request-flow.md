# MCP Search Request Data Flow

This document describes the complete data flow for an MCP search request through the DocAIche architecture.

## Overview

The MCP (Model Context Protocol) endpoint provides AI agents with access to DocAIche's search capabilities through a JSON-RPC 2.0 interface. This document traces the complete journey of a search request from entry to response.

## Data Flow Diagram

### 1. **Request Entry** 
```
AI Agent → http://localhost:4080/api/v1/mcp
         ↓
   admin-ui (Next.js on port 4080)
         ↓
   Proxy rewrite → http://api:4000/api/v1/mcp
```

### 2. **FastAPI Processing**
```
FastAPI Router (/src/api/v1/mcp/router.py)
    ↓
MCPHandler (/src/api/v1/mcp/handlers.py)
    ↓
JSON-RPC 2.0 validation & routing
    ↓
Method: "tools/call" with name: "docaiche_search"
```

### 3. **Tool Execution**
```
SearchTool.execute() (/src/api/v1/mcp/tools/search_tool.py)
    ↓
SearchOrchestrator dependency injection
    ↓
SearchOrchestrator.search() (/src/search/orchestrator.py)
```

### 4. **Search Orchestration**
```
Query Normalization
    ↓
Cache Check (Redis) - if hit, return cached results
    ↓ (cache miss)
Multi-Workspace Search Strategy
    ↓
WorkspaceSearchStrategy (/src/search/strategies.py)
```

### 5. **Workspace Search**
```
Identify Relevant Workspaces (from database)
    ↓
Parallel Search (max 5 concurrent)
    ↓
For each workspace:
    AnythingLLMClient.search_workspace()
        ↓
    HTTP request to AnythingLLM service
        ↓
    Vector similarity search in workspace
        ↓
    Returns matching documents
```

### 6. **Result Processing**
```
Aggregate results from all workspaces
    ↓
ResultRanker ranks by relevance
    ↓
Optional: LLM evaluation (currently mocked)
    ↓
Optional: Trigger enrichment (background task)
    ↓
Cache results in Redis
```

### 7. **Response Formation**
```
SearchOrchestrator returns SearchResponse
    ↓
SearchTool wraps in ToolResult
    ↓
MCPHandler formats as JSON-RPC response:
{
    "jsonrpc": "2.0",
    "result": {
        "content": [{
            "type": "text",
            "text": {
                "query": "...",
                "results": [...],
                "total_count": N,
                ...
            }
        }]
    },
    "id": request_id
}
```

### 8. **Response Return**
```
FastAPI → admin-ui proxy → AI Agent
```

## Key Components & Their Roles

1. **admin-ui (port 4080)**: Just a proxy, forwards requests
2. **FastAPI MCP Router**: Handles JSON-RPC protocol
3. **MCPHandler**: Routes to appropriate tool/resource
4. **SearchTool**: Adapter between MCP and search system
5. **SearchOrchestrator**: Core search logic & caching
6. **WorkspaceSearchStrategy**: Multi-workspace coordination
7. **AnythingLLMClient**: Vector search in workspaces
8. **Redis**: Caches search results
9. **Database**: Stores workspace metadata

## Data Transformations

1. **Input**: JSON-RPC request with search query
2. **Query Processing**: Normalized, stemmed, cleaned
3. **Vector Search**: Query → Vector → Similar documents
4. **Ranking**: Score and order results
5. **Output**: JSON-RPC response with search results

## Example Request/Response

### Request
```json
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "docaiche_search",
        "arguments": {
            "query": "python async programming",
            "technology": "python",
            "limit": 10
        }
    },
    "id": "12345"
}
```

### Response
```json
{
    "jsonrpc": "2.0",
    "result": {
        "content": [{
            "type": "text",
            "text": {
                "query": "python async programming",
                "technology": "python",
                "results": [
                    {
                        "content_id": "doc_123",
                        "title": "Python Async/Await Guide",
                        "snippet": "Understanding async and await in Python...",
                        "source_url": "https://example.com/async-guide",
                        "technology": "python",
                        "relevance_score": 0.92,
                        "content_type": "documentation",
                        "workspace": "python-docs"
                    }
                ],
                "total_count": 1,
                "returned_count": 1,
                "cache_hit": false,
                "execution_time_ms": 235
            }
        }]
    },
    "id": "12345"
}
```

## AI Provider Usage

### No AI Provider Needed For:
- Basic search functionality
- Vector similarity matching
- Result retrieval

### AI Provider Would Be Used For:
- Query understanding/expansion
- Result quality evaluation
- Enrichment recommendations
- Semantic reranking

The architecture is designed so search works without an AI provider - it's purely vector similarity search through AnythingLLM.

## Performance Characteristics

- **Cache Hit**: ~5-10ms response time
- **Cache Miss**: 100-500ms depending on workspace count
- **Timeout**: 2s per workspace, 30s overall
- **Concurrency**: Max 5 parallel workspace searches

## Error Handling

- Individual workspace failures don't fail the entire search
- Circuit breaker protects against Redis failures
- Graceful degradation when services unavailable
- Partial results returned when possible