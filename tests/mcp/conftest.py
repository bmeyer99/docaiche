"""
Pytest configuration for MCP tests
==================================

Shared fixtures and test configuration for MCP test suite.
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock

# Configure event loop for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock external dependencies
@pytest.fixture
def mock_aiohttp():
    """Mock aiohttp for tests."""
    with pytest.mock.patch('src.mcp.transport.streamable_http.aiohttp_available', True):
        mock_session = AsyncMock()
        mock_session.close = AsyncMock()
        yield mock_session


@pytest.fixture
def mock_pydantic():
    """Mock pydantic for tests."""
    with pytest.mock.patch('src.mcp.schemas.pydantic_available', True):
        yield


# Test data fixtures
@pytest.fixture
def sample_mcp_request():
    """Sample MCP request for testing."""
    from src.mcp.schemas import MCPRequest
    return MCPRequest(
        id="test-request-123",
        method="tool/execute",
        params={
            "tool": "docaiche_search",
            "arguments": {
                "query": "machine learning",
                "limit": 10
            }
        }
    )


@pytest.fixture
def sample_mcp_response():
    """Sample MCP response for testing."""
    from src.mcp.schemas import MCPResponse
    return MCPResponse(
        id="test-request-123",
        result={
            "results": [
                {
                    "id": "doc1",
                    "title": "Introduction to ML",
                    "content": "Machine learning basics...",
                    "score": 0.95
                }
            ],
            "total": 1
        }
    )


@pytest.fixture
def sample_auth_token():
    """Sample JWT token for testing."""
    return {
        "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
        "claims": {
            "sub": "user123",
            "aud": "docaiche-mcp",
            "iss": "https://auth.example.com",
            "scope": "read write",
            "resource": ["docaiche:search", "docaiche:collections"]
        }
    }


# API client mocks
@pytest.fixture
def mock_api_client():
    """Mock DocaiChe API client."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def mock_database_manager():
    """Mock database manager."""
    manager = AsyncMock()
    manager.fetch_one = AsyncMock()
    manager.fetch_all = AsyncMock()
    manager.execute = AsyncMock()
    manager.health_check = AsyncMock(return_value={
        "status": "healthy",
        "response_time_ms": 5
    })
    return manager


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager."""
    manager = AsyncMock()
    manager.get = AsyncMock()
    manager.set = AsyncMock()
    manager.delete = AsyncMock()
    manager.health_check = AsyncMock(return_value={
        "status": "healthy",
        "response_time_ms": 1
    })
    return manager


# Test environment setup
@pytest.fixture
def test_config_dir():
    """Create temporary config directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        # Create default test config
        config_file = config_dir / "config.test.yaml"
        config_file.write_text("""
server:
  host: localhost
  port: 8080
  workers: 2

security:
  enable_auth: true
  jwt_secret: test-secret

database:
  url: postgresql://test/docaiche

redis:
  url: redis://localhost:6379/0

testing:
  enabled: true
  mock_external: true
""")
        yield config_dir


@pytest.fixture
def test_env_vars():
    """Set test environment variables."""
    env_vars = {
        "MCP_ENVIRONMENT": "test",
        "MCP_LOG_LEVEL": "DEBUG",
        "MCP_TESTING_MODE": "true"
    }
    
    import os
    old_environ = dict(os.environ)
    os.environ.update(env_vars)
    
    yield env_vars
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(old_environ)


# Security testing fixtures
@pytest.fixture
def mock_security_context():
    """Mock security context for tests."""
    return {
        "authenticated": True,
        "client_id": "test-client",
        "scopes": ["read", "write"],
        "resource_access": {
            "docaiche:search": True,
            "docaiche:collections": True,
            "docaiche:ingest": True
        }
    }


@pytest.fixture
def mock_consent_manager():
    """Mock consent manager."""
    manager = AsyncMock()
    manager.check_consent = AsyncMock(return_value=True)
    manager.record_consent = AsyncMock()
    manager.revoke_consent = AsyncMock()
    return manager


@pytest.fixture
def mock_audit_logger():
    """Mock audit logger."""
    logger = AsyncMock()
    logger.log_event = AsyncMock()
    logger.log_security_event = AsyncMock()
    logger.log_request = AsyncMock()
    logger.search_logs = AsyncMock(return_value=[])
    return logger


# Transport testing fixtures
@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    ws = AsyncMock()
    ws.send_str = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_http_response():
    """Mock HTTP response."""
    response = AsyncMock()
    response.status = 200
    response.headers = {"Content-Type": "application/json"}
    response.json = AsyncMock(return_value={
        "jsonrpc": "2.0",
        "id": "test-123",
        "result": {"status": "success"}
    })
    response.text = AsyncMock(return_value='{"status": "success"}')
    return response


# Test utilities
class TestMetrics:
    """Test metrics collector."""
    
    def __init__(self):
        self.counters = {}
        self.timers = {}
        self.gauges = {}
    
    def increment(self, metric, value=1):
        self.counters[metric] = self.counters.get(metric, 0) + value
    
    def record_time(self, metric, duration):
        if metric not in self.timers:
            self.timers[metric] = []
        self.timers[metric].append(duration)
    
    def set_gauge(self, metric, value):
        self.gauges[metric] = value
    
    def get_metrics(self):
        return {
            "counters": self.counters,
            "timers": self.timers,
            "gauges": self.gauges
        }


@pytest.fixture
def test_metrics():
    """Test metrics instance."""
    return TestMetrics()


# Async test helpers
async def async_return(value):
    """Helper to return async value."""
    return value


async def async_raise(exception):
    """Helper to raise async exception."""
    raise exception


# Test markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "system: System tests"
    )
    config.addinivalue_line(
        "markers", "security: Security tests"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow running tests"
    )


# Test collection customization
def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add markers based on test location
    for item in items:
        # Mark all async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # Mark by test type
        if "unit" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        elif "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "system" in item.nodeid:
            item.add_marker(pytest.mark.system)
        
        # Mark security tests
        if "security" in item.nodeid or "auth" in item.nodeid:
            item.add_marker(pytest.mark.security)