# PRD-004: AnythingLLM Integration Client

## Overview
Specifies the complete HTTP client for interacting with an AnythingLLM instance. Handles workspace management, content lifecycle (uploading, deleting), and vector searches. Pure integration component with no business logic.

## Technical Boundaries
- Wraps the AnythingLLM REST API.
- Called by Search Orchestrator and Content Acquisition Engine.
- Depends on Configuration Management for endpoint and API key.

## Success Criteria
- Performs all specified operations against a running AnythingLLM instance.
- Handles all API error conditions gracefully.
- Implements retry logic and accurate health reporting.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-003: Configuration Management | Loads endpoint and API key |
| PRD-008: Content Processing Pipeline | Provides chunked documents for upload |
| PRD-009: Search Orchestration Engine | Calls search and upload methods |

## Cross-References
- Receives `ProcessedDocument` and `DocumentChunk` from PRD-002 (canonical models).
- Used by PRD-009 for search and enrichment workflows.
- Health check endpoint referenced in PRD-012 (Web UI).
- Implements circuit breaker pattern for reliability.

## API Interaction Summary

| Method | Endpoint                                 | Description                       | Error Responses                   |
|--------|------------------------------------------|-----------------------------------|-----------------------------------|
| POST   | /api/workspace/{slug}/upload-text        | Uploads a document chunk          | 400, 401, 429, 500, 503          |
| GET    | /api/workspace/{slug}/list               | Lists workspace documents         | 400, 401, 429, 500, 503          |
| POST   | /api/workspace/{slug}/search             | Executes a vector search          | 400, 401, 429, 500, 503          |
| DELETE | /api/workspace/{slug}/delete/{doc_id}    | Deletes a document                | 400, 401, 404, 429, 500, 503     |
| GET    | /api/health                              | Health check                      | 500, 503                          |

## Circuit Breaker Configuration

**Service Category**: Internal Services
**Rationale**: AnythingLLM is an internal service with predictable behavior. Medium tolerance with shorter recovery allows for quick failover while maintaining reasonable availability.

```python
from circuitbreaker import circuit

class AnythingLLMClient:
    def __init__(self, config: AnythingLLMConfig):
        self.circuit_breaker = circuit(
            failure_threshold=3,
            recovery_timeout=60,
            timeout=30,
            expected_exception=aiohttp.ClientError
        )
    
    @circuit_breaker
    async def _make_request(self, method: str, endpoint: str, **kwargs):
        # Protected HTTP request implementation
        pass
```

## Data Models

All data models are now defined in [`PRD-002`](PRD-002_DB_and_Caching_Layer.md) as canonical models:
- [`ProcessedDocument`](PRD-002_DB_and_Caching_Layer.md:89) - Complete document with metadata and chunks
- [`DocumentChunk`](PRD-002_DB_and_Caching_Layer.md:78) - Individual content chunk
- [`DocumentMetadata`](PRD-002_DB_and_Caching_Layer.md:67) - Document metadata and versioning

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| ALM-001 | Implement AnythingLLMClient class with aiohttp.ClientSession and circuit breaker |
| ALM-002 | Implement health_check method with circuit breaker status |
| ALM-003 | Implement list_workspaces and get_or_create_workspace methods |
| ALM-004 | Implement upload_document method with detailed specifications (see below) |
| ALM-005 | Implement search_workspace method with error handling |
| ALM-006 | Implement delete_document method with proper error responses |
| ALM-007 | Implement circuit breaker pattern with configurable thresholds |
| ALM-008 | Implement comprehensive logging with trace IDs |
| ALM-009 | Write unit tests for all methods including circuit breaker scenarios |
| ALM-010 | Integrate health_check with system health endpoint and circuit breaker status |

### ALM-004 Detailed Specification: upload_document Method

```python
async def upload_document(self, workspace_slug: str, document: ProcessedDocument) -> UploadResult:
    """
    Uploads a ProcessedDocument to AnythingLLM workspace by iterating over chunks.
    
    Args:
        workspace_slug: Target workspace identifier
        document: ProcessedDocument with pre-computed chunks
        
    Returns:
        UploadResult with success status and uploaded chunk IDs
        
    Process:
    1. Validate workspace exists (call get_or_create_workspace if needed)
    2. Iterate through document.chunks in order
    3. For each chunk, POST to /api/workspace/{slug}/upload-text with:
       - content: chunk.content
       - metadata: chunk.id, chunk.chunk_index, document.title, document.technology
    4. Implement batch upload (max 5 concurrent uploads)
    5. Track failed uploads and retry with exponential backoff
    6. Update document metadata in database after successful upload
    7. Return comprehensive result with success/failure details
    
    Error Handling:
    - Circuit breaker triggers after 5 consecutive failures
    - Individual chunk failures don't stop the entire upload
    - Partial uploads are tracked and can be resumed
    - All errors logged with trace_id for debugging
    """
    pass
```

## Integration Contracts
- Accepts `ProcessedDocument` with pre-computed `DocumentChunk` objects.
- Uploads each chunk via AnythingLLM API.
- Handles errors and retries as specified.

## Summary Tables

### Endpoints Table
(see API Interaction Summary above)

### Data Models Table

| Model Name        | Description                       | Used In Endpoint(s)                |
|-------------------|-----------------------------------|------------------------------------|
| DocumentChunk     | Chunk of a processed document     | upload_document                    |
| ProcessedDocument | Full processed document           | upload_document, search_workspace  |

### Implementation Tasks Table
(see Implementation Tasks above)

---