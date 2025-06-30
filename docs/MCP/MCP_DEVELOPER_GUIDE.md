# MCP Developer Guide

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Code Organization](#code-organization)
4. [Adding New Tools](#adding-new-tools)
5. [Adding New Resources](#adding-new-resources)
6. [Security Guidelines](#security-guidelines)
7. [Testing Strategy](#testing-strategy)
8. [Best Practices](#best-practices)
9. [Contributing](#contributing)

## Architecture Overview

### System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   MCP Client    │────▶│   MCP Server    │────▶│ DocaiChe Core   │
│  (AI Agents)    │     │  (This System)  │     │   (FastAPI)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                       │                        │
         │                       │                        │
    OAuth 2.1              Streamable HTTP           REST API
  Authentication             Transport              Integration
```

### Component Layers

1. **Transport Layer**: Handles HTTP/WebSocket communication
2. **Authentication Layer**: OAuth 2.1 with JWT validation
3. **Protocol Layer**: MCP message handling and routing
4. **Tool Layer**: Search, ingest, and feedback implementations
5. **Resource Layer**: Collections and status providers
6. **Adapter Layer**: Integration with existing FastAPI
7. **Security Layer**: Rate limiting, consent, and audit
8. **Monitoring Layer**: Logging, metrics, and tracing

## Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/docaiche.git
cd docaiche
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Configure IDE

#### VS Code Settings

```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "editor.formatOnSave": true
}
```

#### PyCharm Configuration

1. Set Python interpreter to virtual environment
2. Enable pytest as test runner
3. Configure code style to use Black
4. Enable type checking with mypy

### 4. Local Development

```bash
# Run development server with auto-reload
uvicorn src.mcp.main:app --reload --host localhost --port 8000

# Run with debug logging
LOG_LEVEL=DEBUG python -m src.mcp.main
```

## Code Organization

### Directory Structure

```
src/mcp/
├── __init__.py
├── main.py                 # Application entry point
├── server.py              # MCP server implementation
├── schemas.py             # Pydantic models
├── exceptions.py          # Custom exceptions
├── auth/                  # Authentication module
│   ├── oauth_handler.py
│   └── jwt_validator.py
├── transport/             # Transport implementations
│   ├── base_transport.py
│   ├── http_transport.py
│   └── websocket_transport.py
├── tools/                 # MCP tools
│   ├── base_tool.py
│   ├── search_tool.py
│   ├── ingest_tool.py
│   └── feedback_tool.py
├── resources/             # MCP resources
│   ├── base_resource.py
│   ├── collections_resource.py
│   └── status_resource.py
├── adapters/              # Integration adapters
│   └── fastapi_adapter.py
├── security/              # Security components
│   ├── rate_limiter.py
│   ├── consent_manager.py
│   └── security_auditor.py
├── monitoring/            # Observability
│   ├── logger.py
│   ├── metrics.py
│   └── tracing.py
└── config/                # Configuration
    └── settings.py
```

### Key Modules

#### Server Module (`server.py`)

```python
class MCPServer:
    """Main MCP server implementation."""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.transport_manager = TransportManager()
        self.tool_registry = ToolRegistry()
        self.resource_registry = ResourceRegistry()
```

#### Tool Base Class (`tools/base_tool.py`)

```python
class BaseTool(ABC):
    """Base class for all MCP tools."""
    
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for tool arguments."""
        pass
```

## Adding New Tools

### 1. Create Tool Implementation

```python
# src/mcp/tools/my_custom_tool.py
from typing import Dict, Any
from .base_tool import BaseTool
from ..schemas import ToolSchema

class MyCustomTool(BaseTool):
    """Custom tool implementation."""
    
    def __init__(self):
        self.name = "docaiche/my_custom"
        self.description = "My custom tool description"
    
    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the custom tool."""
        # Validate arguments
        validated_args = self._validate_arguments(arguments)
        
        # Implement tool logic
        result = await self._process_custom_logic(validated_args)
        
        # Return structured response
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "execution_time_ms": 100
            }
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return tool argument schema."""
        return {
            "type": "object",
            "properties": {
                "input_field": {
                    "type": "string",
                    "description": "Description of input field"
                },
                "optional_field": {
                    "type": "number",
                    "description": "Optional numeric field"
                }
            },
            "required": ["input_field"]
        }
```

### 2. Register Tool

```python
# src/mcp/tools/__init__.py
from .my_custom_tool import MyCustomTool

# Add to tool registry
AVAILABLE_TOOLS = {
    "docaiche/search": SearchTool,
    "docaiche/ingest": IngestTool,
    "docaiche/feedback": FeedbackTool,
    "docaiche/my_custom": MyCustomTool,  # Add here
}
```

### 3. Add Tests

```python
# tests/mcp/tools/test_my_custom_tool.py
import pytest
from src.mcp.tools.my_custom_tool import MyCustomTool

@pytest.mark.asyncio
async def test_my_custom_tool_execution():
    tool = MyCustomTool()
    
    result = await tool.execute({
        "input_field": "test input"
    })
    
    assert result["status"] == "success"
    assert "data" in result

@pytest.mark.asyncio
async def test_my_custom_tool_validation():
    tool = MyCustomTool()
    
    with pytest.raises(ValidationError):
        await tool.execute({})  # Missing required field
```

### 4. Document Tool

Add to `docs/MCP_API_REFERENCE.md`:

```markdown
### docaiche/my_custom

Description of what the tool does.

**Input Schema:**
```typescript
{
  "input_field": string;      // Required: description
  "optional_field"?: number;  // Optional: description
}
```

**Output Schema:**
```typescript
{
  "status": "success" | "failed";
  "data": any;
  "metadata": {
    "execution_time_ms": number;
  }
}
```
```

## Adding New Resources

### 1. Create Resource Implementation

```python
# src/mcp/resources/my_resource.py
from typing import Dict, Any, Optional
from .base_resource import BaseResource

class MyResource(BaseResource):
    """Custom resource implementation."""
    
    def __init__(self):
        self.uri_pattern = "docaiche://my_resource/*"
    
    async def read(self, uri: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Read resource data."""
        # Parse URI
        resource_id = self._parse_uri(uri)
        
        # Fetch resource data
        data = await self._fetch_resource_data(resource_id, params)
        
        # Return structured response
        return {
            "uri": uri,
            "mimeType": "application/json",
            "data": data
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """Return resource schema."""
        return {
            "uri_pattern": self.uri_pattern,
            "parameters": {
                "filter": {
                    "type": "string",
                    "description": "Optional filter parameter"
                }
            }
        }
```

### 2. Register Resource

```python
# src/mcp/resources/__init__.py
from .my_resource import MyResource

# Add to resource registry
AVAILABLE_RESOURCES = {
    "docaiche://collections": CollectionsResource,
    "docaiche://status": StatusResource,
    "docaiche://my_resource/*": MyResource,  # Add here
}
```

## Security Guidelines

### 1. Input Validation

Always validate and sanitize inputs:

```python
from pydantic import BaseModel, validator

class ToolInput(BaseModel):
    query: str
    max_results: int = 10
    
    @validator('query')
    def validate_query(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Query cannot be empty")
        if len(v) > 1000:
            raise ValueError("Query too long")
        return v.strip()
    
    @validator('max_results')
    def validate_max_results(cls, v):
        if v < 1 or v > 100:
            raise ValueError("max_results must be between 1 and 100")
        return v
```

### 2. Authentication Checks

Enforce authentication for protected operations:

```python
async def execute(self, arguments: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
    # Check authentication
    if not context.authenticated:
        raise AuthenticationError("Authentication required")
    
    # Check authorization
    if not await self._check_authorization(context.user_id, "resource:read"):
        raise ForbiddenError("Insufficient permissions")
    
    # Proceed with execution
    return await self._execute_authorized(arguments, context)
```

### 3. Rate Limiting

Implement rate limiting for expensive operations:

```python
from ..security.rate_limiter import rate_limit

@rate_limit(max_calls=10, time_window=60)  # 10 calls per minute
async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
    # Tool execution logic
    pass
```

### 4. Audit Logging

Log security-relevant events:

```python
from ..monitoring import security_logger

async def execute(self, arguments: Dict[str, Any], context: RequestContext) -> Dict[str, Any]:
    # Log the operation
    security_logger.info(
        "Tool execution started",
        tool=self.name,
        user_id=context.user_id,
        client_id=context.client_id,
        arguments=self._sanitize_for_logging(arguments)
    )
    
    try:
        result = await self._execute_internal(arguments)
        security_logger.info(
            "Tool execution completed",
            tool=self.name,
            user_id=context.user_id,
            success=True
        )
        return result
    except Exception as e:
        security_logger.error(
            "Tool execution failed",
            tool=self.name,
            user_id=context.user_id,
            error=str(e),
            success=False
        )
        raise
```

## Testing Strategy

### 1. Unit Tests

Test individual components in isolation:

```python
# tests/mcp/tools/test_search_tool.py
import pytest
from unittest.mock import Mock, AsyncMock
from src.mcp.tools.search_tool import SearchTool

@pytest.fixture
def search_tool():
    return SearchTool()

@pytest.fixture
def mock_search_engine():
    mock = AsyncMock()
    mock.search.return_value = {
        "results": [...],
        "total": 10
    }
    return mock

@pytest.mark.asyncio
async def test_search_with_valid_query(search_tool, mock_search_engine):
    search_tool.search_engine = mock_search_engine
    
    result = await search_tool.execute({
        "query": "test query",
        "max_results": 5
    })
    
    assert result["results"] is not None
    assert len(result["results"]) <= 5
    mock_search_engine.search.assert_called_once()
```

### 2. Integration Tests

Test component interactions:

```python
# tests/mcp/integration/test_server_integration.py
import pytest
from httpx import AsyncClient
from src.mcp.main import app

@pytest.mark.asyncio
async def test_search_tool_integration():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Authenticate
        auth_response = await client.post("/oauth/token", data={
            "grant_type": "client_credentials",
            "client_id": "test_client",
            "client_secret": "test_secret"
        })
        token = auth_response.json()["access_token"]
        
        # Call tool
        response = await client.post(
            "/mcp/tools/call",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "tool": "docaiche/search",
                "arguments": {
                    "query": "test"
                }
            }
        )
        
        assert response.status_code == 200
        assert "results" in response.json()
```

### 3. Security Tests

Test security controls:

```python
# tests/mcp/security/test_auth.py
import pytest
from src.mcp.auth.jwt_validator import JWTValidator

def test_invalid_token_rejected():
    validator = JWTValidator()
    
    with pytest.raises(InvalidTokenError):
        validator.validate("invalid.token.here")

def test_expired_token_rejected():
    validator = JWTValidator()
    expired_token = create_expired_token()
    
    with pytest.raises(TokenExpiredError):
        validator.validate(expired_token)
```

### 4. Performance Tests

Test performance characteristics:

```python
# tests/mcp/performance/test_search_performance.py
import pytest
import time
from src.mcp.tools.search_tool import SearchTool

@pytest.mark.performance
@pytest.mark.asyncio
async def test_search_performance():
    tool = SearchTool()
    
    start_time = time.time()
    
    # Execute 100 searches
    for _ in range(100):
        await tool.execute({
            "query": "performance test",
            "max_results": 10
        })
    
    elapsed_time = time.time() - start_time
    avg_time = elapsed_time / 100
    
    # Assert average time is under 100ms
    assert avg_time < 0.1
```

## Best Practices

### 1. Code Style

Follow PEP 8 and use automated formatting:

```bash
# Format code with Black
black src/

# Check types with mypy
mypy src/

# Lint with pylint
pylint src/
```

### 2. Error Handling

Use specific exceptions with context:

```python
class DocumentNotFoundError(MCPError):
    """Raised when requested document doesn't exist."""
    
    def __init__(self, document_id: str):
        super().__init__(
            message=f"Document not found: {document_id}",
            error_code="DOC_NOT_FOUND",
            status_code=404
        )

# Usage
if not document:
    raise DocumentNotFoundError(document_id)
```

### 3. Async Best Practices

Use async/await consistently:

```python
# Good: Concurrent execution
results = await asyncio.gather(
    fetch_document(doc_id1),
    fetch_document(doc_id2),
    fetch_document(doc_id3)
)

# Bad: Sequential execution
result1 = await fetch_document(doc_id1)
result2 = await fetch_document(doc_id2)
result3 = await fetch_document(doc_id3)
```

### 4. Resource Management

Use context managers for resources:

```python
async def process_large_file(file_path: str):
    async with aiofiles.open(file_path, 'r') as file:
        async for line in file:
            await process_line(line)
    # File automatically closed
```

### 5. Configuration Management

Use environment variables and config files:

```python
from pydantic import BaseSettings

class Settings(BaseSettings):
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000
    database_url: Optional[str] = None
    redis_url: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_prefix = "MCP_"

settings = Settings()
```

## Contributing

### 1. Fork and Clone

```bash
# Fork on GitHub, then:
git clone https://github.com/your-username/docaiche.git
cd docaiche
git remote add upstream https://github.com/your-org/docaiche.git
```

### 2. Create Feature Branch

```bash
git checkout -b feature/my-new-feature
```

### 3. Make Changes

1. Write code following style guidelines
2. Add tests for new functionality
3. Update documentation
4. Run tests locally

### 4. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/mcp --cov-report=html

# Run specific test file
pytest tests/mcp/tools/test_search_tool.py
```

### 5. Submit Pull Request

1. Push changes to your fork
2. Create pull request on GitHub
3. Fill out PR template
4. Wait for review

### Pull Request Guidelines

- Clear description of changes
- Tests for new functionality
- Documentation updates
- No breaking changes without discussion
- Follow conventional commits

### Code Review Process

1. Automated checks (CI/CD)
2. Peer review
3. Maintainer review
4. Merge when approved

## Debugging Tips

### 1. Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export LOG_LEVEL=DEBUG
```

### 2. Use Debugger

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use VS Code/PyCharm debugger
```

### 3. Inspect MCP Messages

```python
from ..monitoring import server_logger

async def _handle_request(self, request: MCPRequest):
    server_logger.debug(
        "Received MCP request",
        request_id=request.id,
        method=request.method,
        params=request.params
    )
```

### 4. Performance Profiling

```python
import cProfile
import pstats

def profile_function():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Code to profile
    result = expensive_operation()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(10)  # Top 10 functions
```

## Additional Resources

- [MCP Specification](https://modelcontextprotocol.io/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Async Best Practices](https://docs.python.org/3/library/asyncio.html)
- [OAuth 2.1 Specification](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-v2-1-07)