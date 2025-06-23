import pytest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
import src.main
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def client():
    # Ensure no LLM provider env vars are set
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OLLAMA_BASE_URL", None)
    os.environ.pop("OLLAMA_MODEL", None)
    os.environ.pop("LLM_PROVIDER", None)
    yield TestClient(src.main.app)
import pytest

@pytest.mark.parametrize("endpoint,method", [
    ("/api/v1/health", "get"),
    ("/api/v1/search", "post"),
    ("/api/v1/ingestion/upload", "post"),  # Changed from /api/v1/ingest to the production endpoint
    ("/api/v1/config", "get"),
    ("/docs", "get"),
])
def test_all_endpoints_accessible_without_llm(client, endpoint, method):
    req = getattr(client, method)
    if method == "post":
        resp = req(endpoint, json={"query": "test"})
    else:
        resp = req(endpoint)
    assert resp.status_code in (200, 400, 422), f"{endpoint} failed with {resp.status_code}"