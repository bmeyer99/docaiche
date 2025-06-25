import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

import src.main
from src.api.v1.mcp_endpoints import router as mcp_router
from src.api.v1.mcp_endpoints import get_anythingllm_client, get_search_orchestrator

# Always include the MCP router for testing
src.main.app.include_router(mcp_router)

client = TestClient(src.main.app)

@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    src.main.app.dependency_overrides = {}
    yield
    src.main.app.dependency_overrides = {}

def test_initialize():
    resp = client.post("/mcp", json={"message_type": "initialize"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_name"] == "docaiche-mcp"
    assert data["server_version"] == "1.0.0"
    assert "fetch_documentation" in data["capabilities"]

def test_get_tools():
    resp = client.post("/mcp", json={"message_type": "get_tools"})
    assert resp.status_code == 200
    data = resp.json()
    assert "tools" in data
    tool = next((t for t in data["tools"] if t["name"] == "fetch_documentation"), None)
    assert tool is not None
    assert tool["input_schema"]["type"] == "object"
    assert "symbol" in tool["input_schema"]["properties"]

@pytest.mark.asyncio
async def test_execute_tool_cache_miss():
    # Simulate AnythingLLM returns empty (cache miss)
    mock_anythingllm = AsyncMock()
    mock_anythingllm.search_workspace.return_value = []
    mock_anythingllm.upload_document.return_value = None

    # Simulate SearchOrchestrator returns documentation
    mock_search = AsyncMock()
    mock_result = MagicMock()
    mock_result.results = [MagicMock(content="Doc for TestSymbol")]
    mock_search.execute_search.return_value = (mock_result, None)

    # Patch SearchQuery to always provide a valid strategy
    from src.search import models as search_models
    orig_search_query = search_models.SearchQuery

    class PatchedSearchQuery(orig_search_query):
        def __init__(self, **kwargs):
            if "strategy" not in kwargs or kwargs["strategy"] is None:
                kwargs["strategy"] = "vector"
            super().__init__(**kwargs)

    src.main.app.dependency_overrides[get_anythingllm_client] = lambda: mock_anythingllm
    src.main.app.dependency_overrides[get_search_orchestrator] = lambda: mock_search
    search_models.SearchQuery = PatchedSearchQuery

    payload = {
        "message_type": "execute_tool",
        "tool": "fetch_documentation",
        "arguments": {"symbol": "TestSymbol"},
        "request_id": "req-1"
    }
    with TestClient(src.main.app) as async_client:
        resp = async_client.post("/mcp", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == "req-1"
        assert data["result"]["documentation"] == "Doc for TestSymbol"
        assert data["error"] is None

@pytest.mark.asyncio
async def test_execute_tool_cache_hit():
    # Simulate AnythingLLM returns documentation (cache hit)
    mock_anythingllm = AsyncMock()
    mock_anythingllm.search_workspace.return_value = [{"content": "Cached doc"}]

    # SearchOrchestrator should not be called
    mock_search = AsyncMock()

    # Patch SearchQuery to always provide a valid strategy
    from src.search import models as search_models
    orig_search_query = search_models.SearchQuery

    class PatchedSearchQuery(orig_search_query):
        def __init__(self, **kwargs):
            if "strategy" not in kwargs or kwargs["strategy"] is None:
                kwargs["strategy"] = "vector"
            super().__init__(**kwargs)

    src.main.app.dependency_overrides[get_anythingllm_client] = lambda: mock_anythingllm
    src.main.app.dependency_overrides[get_search_orchestrator] = lambda: mock_search
    search_models.SearchQuery = PatchedSearchQuery

    payload = {
        "message_type": "execute_tool",
        "tool": "fetch_documentation",
        "arguments": {"symbol": "TestSymbol"},
        "request_id": "req-2"
    }
    with TestClient(src.main.app) as async_client:
        resp = async_client.post("/mcp", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["request_id"] == "req-2"
        assert data["result"]["documentation"] == "Cached doc"
        assert data["error"] is None

@pytest.mark.asyncio
async def test_execute_tool_anythingllm_error():
    # Simulate AnythingLLM raises exception
    mock_anythingllm = AsyncMock()
    mock_anythingllm.search_workspace.side_effect = Exception("LLM down")

    mock_search = AsyncMock()

    # Patch SearchQuery to always provide a valid strategy
    from src.search import models as search_models
    orig_search_query = search_models.SearchQuery

    class PatchedSearchQuery(orig_search_query):
        def __init__(self, **kwargs):
            if "strategy" not in kwargs or kwargs["strategy"] is None:
                kwargs["strategy"] = "vector"
            super().__init__(**kwargs)

    src.main.app.dependency_overrides[get_anythingllm_client] = lambda: mock_anythingllm
    src.main.app.dependency_overrides[get_search_orchestrator] = lambda: mock_search
    search_models.SearchQuery = PatchedSearchQuery

    payload = {
        "message_type": "execute_tool",
        "tool": "fetch_documentation",
        "arguments": {"symbol": "TestSymbol"},
        "request_id": "req-3"
    }
    with TestClient(src.main.app) as async_client:
        resp = async_client.post("/mcp", json=payload)
        assert resp.status_code == 503
        data = resp.json()
        assert data["request_id"] == "req-3"
        assert "Documentation cache unavailable" in data["error"]

@pytest.mark.asyncio
async def test_execute_tool_search_orchestrator_error():
    # Simulate AnythingLLM returns empty (cache miss)
    mock_anythingllm = AsyncMock()
    mock_anythingllm.search_workspace.return_value = []

    # Simulate SearchOrchestrator raises exception
    mock_search = AsyncMock()
    mock_search.execute_search.side_effect = Exception("Search error")

    # Patch SearchQuery to always provide a valid strategy
    from src.search import models as search_models
    orig_search_query = search_models.SearchQuery

    class PatchedSearchQuery(orig_search_query):
        def __init__(self, **kwargs):
            if "strategy" not in kwargs or kwargs["strategy"] is None:
                kwargs["strategy"] = "vector"
            super().__init__(**kwargs)

    src.main.app.dependency_overrides[get_anythingllm_client] = lambda: mock_anythingllm
    src.main.app.dependency_overrides[get_search_orchestrator] = lambda: mock_search
    search_models.SearchQuery = PatchedSearchQuery

    payload = {
        "message_type": "execute_tool",
        "tool": "fetch_documentation",
        "arguments": {"symbol": "TestSymbol"},
        "request_id": "req-4"
    }
    with TestClient(src.main.app) as async_client:
        resp = async_client.post("/mcp", json=payload)
        assert resp.status_code == 500
        data = resp.json()
        assert data["request_id"] == "req-4"
        assert "Documentation search failed" in data["error"]

def test_execute_tool_invalid_tool():
    payload = {
        "message_type": "execute_tool",
        "tool": "unknown_tool",
        "arguments": {"symbol": "TestSymbol"},
        "request_id": "req-5"
    }
    resp = client.post("/mcp", json=payload)
    assert resp.status_code == 400
    data = resp.json()
    assert data["request_id"] == "req-5"
    assert "Unsupported tool" in data["error"]

def test_execute_tool_missing_symbol():
    payload = {
        "message_type": "execute_tool",
        "tool": "fetch_documentation",
        "arguments": {},
        "request_id": "req-6"
    }
    resp = client.post("/mcp", json=payload)
    assert resp.status_code == 422
    data = resp.json()
    assert data["request_id"] == "req-6"
    assert "Missing or invalid 'symbol'" in data["error"]

def test_invalid_message_type():
    resp = client.post("/mcp", json={"message_type": "unknown"})
    assert resp.status_code == 400
    data = resp.json()
    assert "Invalid or unsupported message_type" in data["error"]