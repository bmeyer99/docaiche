import sys
import os
# Only add the project root to sys.path for src.main import to work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

import pytest
from fastapi.testclient import TestClient

import src.main

@pytest.fixture(scope="module")
def client():
    # Ensure no LLM provider env vars are set
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OLLAMA_BASE_URL", None)
    os.environ.pop("OLLAMA_MODEL", None)
    os.environ.pop("LLM_PROVIDER", None)
    # Optionally clear config file if used
    yield TestClient(src.main.app)

def test_startup_no_llm_config(client):
    # System should start and health endpoint should work
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"

def test_no_llm_provider_errors_on_startup(client):
    # No OpenAI/Ollama errors should be present in health or logs
    resp = client.get("/health")
    data = resp.json()
    assert "llm" not in data or data["llm"] in (None, "unavailable", "not_configured")

def test_document_processing_without_llm(client):
    # Upload a document and ensure processing works without LLM
    files = {"file": ("test.txt", b"hello world")}
    resp = client.post("/api/v1/ingestion/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "document_id" in data

def test_api_endpoints_work_without_llm(client):
    # Core endpoints should function
    resp = client.get("/api/v1/search?q=test")
    assert resp.status_code in (200, 204, 404)
    # Should not 500 due to missing LLM
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200

def test_llm_enhancement_status_in_api(client):
    # If LLM is called, response should indicate unavailability
    resp = client.post("/api/v1/enrichment/llm", json={"text": "test"})
    assert resp.status_code in (503, 501, 400)
    assert "llm" in resp.json().get("detail", "").lower() or "not available" in resp.json().get("detail", "").lower()

def test_graceful_degradation_on_llm_call(client):
    # LLM-dependent endpoints should degrade gracefully
    resp = client.post("/api/v1/enrichment/llm", json={"text": "test"})
    assert resp.status_code in (503, 501, 400)
    # Should not crash or expose stack trace
    assert "traceback" not in resp.text.lower()

def test_regression_with_llm_config(monkeypatch):
    # Simulate LLM config present
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    client = TestClient(src.main.app)
    resp = client.get("/health")
    assert resp.status_code == 200
    # LLM status should not be "unavailable"
    data = resp.json()
    assert "llm" not in data or data["llm"] not in ("unavailable", "not_configured")