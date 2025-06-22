# Task: ALM-001 - Implement AnythingLLM Client with Circuit Breaker

**PRD Reference**: [PRD-004: AnythingLLM Integration Client](../PRDs/PRD-004_AnythingLLM_Integration.md)

## Overview
Implement the complete AnythingLLM HTTP client for workspace management, document upload, vector search, and content lifecycle operations with circuit breaker pattern for reliability.

## Detailed Requirements

### 1. AnythingLLM Client Class Structure
```python
import aiohttp
import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from circuitbreaker import circuit
from datetime import datetime

from core.config.models import AnythingLLMConfig
from models.schemas import ProcessedDocument, DocumentChunk
from models.db_models import DocumentMetadata

logger = logging.getLogger(__name__)

class AnythingLLMClient:
    def __init__(self, config: AnythingLLMConfig):
        self.config = config
        self.base_url = config.endpoint.rstrip('/')
        self.api_key = config.api_key
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Circuit breaker configuration for internal service
        self.circuit_breaker = circuit(
            failure_threshold=config.circuit_breaker.failure_threshold,
            recovery_timeout=config.circuit_breaker.recovery_timeout,
            timeout=config.circuit_breaker.timeout_seconds,
            expected_exception=aiohttp.ClientError
        )
```

### 2. Session Management
```python
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Initialize HTTP session with proper headers and timeouts"""
        timeout = aiohttp.ClientTimeout(total=self.config.circuit_breaker.timeout_seconds)
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'DocAI-Cache/1.0.0'
        }
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=aiohttp.TCPConnector(limit=10, limit_per_host=5)
        )
        logger.info("AnythingLLM client session initialized")
    
    async def disconnect(self) -> None:
        """Clean up HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("AnythingLLM client session closed")
```

### 3. Core API Methods with Circuit Breaker

#### Health Check
```python
    @circuit_breaker
    async def health_check(self) -> Dict[str, Any]:
        """Check AnythingLLM service health and circuit breaker status"""
        try:
            async with self._make_request('GET', '/api/health') as response:
                health_data = await response.json()
                
                # Add circuit breaker status
                health_data['circuit_breaker'] = {
                    'state': self.circuit_breaker.state.name,
                    'failure_count': self.circuit_breaker.failure_count,
                    'last_failure': self.circuit_breaker.last_failure_time
                }
                
                return health_data
                
        except Exception as e:
            logger.error(f"AnythingLLM health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'circuit_breaker': {
                    'state': self.circuit_breaker.state.name,
                    'failure_count': self.circuit_breaker.failure_count
                }
            }
```

#### Workspace Management
```python
    @circuit_breaker
    async def list_workspaces(self) -> List[Dict[str, Any]]:
        """List all available workspaces"""
        async with self._make_request('GET', '/api/workspaces') as response:
            data = await response.json()
            return data.get('workspaces', [])
    
    @circuit_breaker
    async def get_or_create_workspace(self, workspace_slug: str, name: str = None) -> Dict[str, Any]:
        """Get existing workspace or create new one"""
        # First try to get existing workspace
        try:
            async with self._make_request('GET', f'/api/workspace/{workspace_slug}') as response:
                if response.status == 200:
                    return await response.json()
        except aiohttp.ClientResponseError as e:
            if e.status != 404:
                raise
        
        # Create new workspace if not found
        workspace_data = {
            'name': name or workspace_slug.replace('-', ' ').title(),
            'slug': workspace_slug
        }
        
        async with self._make_request('POST', '/api/workspace/new', json=workspace_data) as response:
            return await response.json()
```

#### Document Upload (ALM-004 Detailed Specification)
```python
    @circuit_breaker
    async def upload_document(self, workspace_slug: str, document: ProcessedDocument) -> Dict[str, Any]:
        """
        Upload ProcessedDocument to workspace by iterating over chunks.
        
        Process:
        1. Validate workspace exists
        2. Upload chunks with batch processing (max 5 concurrent)
        3. Track failures and retry with exponential backoff
        4. Return comprehensive result
        """
        logger.info(f"Starting upload of document {document.id} to workspace {workspace_slug}")
        
        # Step 1: Validate workspace exists
        workspace = await self.get_or_create_workspace(workspace_slug)
        
        # Step 2: Prepare upload results tracking
        upload_results = {
            'document_id': document.id,
            'workspace_slug': workspace_slug,
            'total_chunks': len(document.chunks),
            'successful_uploads': 0,
            'failed_uploads': 0,
            'uploaded_chunk_ids': [],
            'failed_chunk_ids': [],
            'errors': []
        }
        
        # Step 3: Upload chunks in batches
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent uploads
        
        async def upload_chunk(chunk: DocumentChunk) -> bool:
            async with semaphore:
                return await self._upload_single_chunk(workspace_slug, document, chunk, upload_results)
        
        # Execute all chunk uploads
        tasks = [upload_chunk(chunk) for chunk in document.chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                upload_results['failed_uploads'] += 1
                upload_results['failed_chunk_ids'].append(document.chunks[i].id)
                upload_results['errors'].append(str(result))
            elif result:
                upload_results['successful_uploads'] += 1
                upload_results['uploaded_chunk_ids'].append(document.chunks[i].id)
            else:
                upload_results['failed_uploads'] += 1
                upload_results['failed_chunk_ids'].append(document.chunks[i].id)
        
        # Log results
        success_rate = upload_results['successful_uploads'] / upload_results['total_chunks']
        logger.info(f"Document upload completed: {success_rate:.1%} success rate "
                   f"({upload_results['successful_uploads']}/{upload_results['total_chunks']} chunks)")
        
        return upload_results
    
    async def _upload_single_chunk(self, workspace_slug: str, document: ProcessedDocument, 
                                 chunk: DocumentChunk, results: Dict[str, Any]) -> bool:
        """Upload a single document chunk with retry logic"""
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                chunk_data = {
                    'content': chunk.content,
                    'metadata': {
                        'chunk_id': chunk.id,
                        'chunk_index': chunk.chunk_index,
                        'total_chunks': chunk.total_chunks,
                        'document_title': document.title,
                        'document_id': document.id,
                        'technology': document.technology,
                        'source_url': document.source_url
                    }
                }
                
                async with self._make_request('POST', f'/api/workspace/{workspace_slug}/upload-text', 
                                            json=chunk_data) as response:
                    if response.status in [200, 201]:
                        return True
                    else:
                        logger.warning(f"Chunk upload failed with status {response.status}: {chunk.id}")
                        
            except Exception as e:
                logger.warning(f"Chunk upload attempt {attempt + 1} failed for {chunk.id}: {e}")
                
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
                else:
                    results['errors'].append(f"Chunk {chunk.id}: {str(e)}")
        
        return False
```

#### Vector Search
```python
    @circuit_breaker
    async def search_workspace(self, workspace_slug: str, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Execute vector search against workspace"""
        search_data = {
            'message': query,
            'limit': limit,
            'mode': 'query'  # AnythingLLM search mode
        }
        
        async with self._make_request('POST', f'/api/workspace/{workspace_slug}/search', 
                                    json=search_data) as response:
            data = await response.json()
            return data.get('results', [])
```

#### Document Management
```python
    @circuit_breaker
    async def list_workspace_documents(self, workspace_slug: str) -> List[Dict[str, Any]]:
        """List all documents in workspace"""
        async with self._make_request('GET', f'/api/workspace/{workspace_slug}/list') as response:
            data = await response.json()
            return data.get('documents', [])
    
    @circuit_breaker 
    async def delete_document(self, workspace_slug: str, document_id: str) -> bool:
        """Delete document from workspace"""
        try:
            async with self._make_request('DELETE', f'/api/workspace/{workspace_slug}/delete/{document_id}') as response:
                return response.status in [200, 204, 404]  # 404 means already deleted
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                return True  # Already deleted
            raise
```

### 4. HTTP Request Handler
```python
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request with proper error handling and logging"""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")
        
        url = f"{self.base_url}{endpoint}"
        trace_id = kwargs.pop('trace_id', None)
        
        logger.debug(f"AnythingLLM request: {method} {url}", extra={'trace_id': trace_id})
        
        try:
            response = await self.session.request(method, url, **kwargs)
            
            # Log response status
            logger.debug(f"AnythingLLM response: {response.status}", extra={'trace_id': trace_id})
            
            # Handle error status codes
            if response.status >= 400:
                error_text = await response.text()
                logger.error(f"AnythingLLM API error {response.status}: {error_text}")
                response.raise_for_status()
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"AnythingLLM request timeout: {method} {url}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"AnythingLLM client error: {e}")
            raise
```

## Error Handling and Logging

### Custom Exceptions
```python
class AnythingLLMError(Exception):
    """Base exception for AnythingLLM client errors"""
    pass

class AnythingLLMConnectionError(AnythingLLMError):
    """Connection-related errors"""
    pass

class AnythingLLMAuthenticationError(AnythingLLMError):
    """Authentication failures"""
    pass

class AnythingLLMRateLimitError(AnythingLLMError):
    """Rate limiting errors"""
    pass
```

## Acceptance Criteria
- [ ] All methods implemented as specified in PRD-004
- [ ] Circuit breaker pattern properly implemented with configurable thresholds
- [ ] Async context manager for session lifecycle
- [ ] Comprehensive error handling for all failure modes
- [ ] Batch document upload with concurrency control
- [ ] Retry logic with exponential backoff for failed uploads
- [ ] Detailed logging with trace ID support
- [ ] Health check includes circuit breaker status
- [ ] All HTTP interactions properly handle timeouts
- [ ] Type hints for all methods and parameters

## Dependencies
- aiohttp >= 3.8.0
- circuitbreaker >= 1.4.0
- asyncio (standard library)

## Files to Create/Modify
- `src/clients/__init__.py` (create)
- `src/clients/anythingllm.py` (create)
- `src/clients/exceptions.py` (create)

## Testing
- Test all CRUD operations against AnythingLLM API
- Test circuit breaker behavior under failure conditions
- Test batch upload with partial failures
- Test retry logic with network issues
- Test session lifecycle management
- Integration tests with real AnythingLLM instance

## Integration Notes
- Client will be used by Search Orchestrator (PRD-009) for vector search
- Upload functionality integrates with Content Processor (PRD-008)
- Health check status feeds into system health endpoint (PRD-001)
- Circuit breaker configuration comes from Configuration Management (PRD-003)
- Error handling must align with global error handling patterns (API-004)