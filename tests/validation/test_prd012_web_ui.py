import pytest
from fastapi.testclient import TestClient
from src.web_ui.main import app

client = TestClient(app)

# --- Functional Tests ---

def test_dashboard_page_renders():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "health" in resp.text.lower()
    assert "metrics" in resp.text.lower()
    assert "recent queries" in resp.text.lower()

def test_config_page_renders():
    resp = client.get("/config")
    assert resp.status_code == 200
    assert "configuration" in resp.text.lower()
    assert "save" in resp.text.lower()
    assert "reset" in resp.text.lower()

def test_content_page_renders():
    resp = client.get("/content")
    assert resp.status_code == 200
    assert "collections" in resp.text.lower()
    assert "search" in resp.text.lower()
    assert "flag" in resp.text.lower()

def test_dashboard_api_integration():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    resp = client.get("/api/v1/stats")
    assert resp.status_code == 200

def test_config_api_integration():
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200

def test_content_api_integration():
    resp = client.get("/api/v1/collections")
    assert resp.status_code == 200
    resp = client.post("/api/v1/admin/search-content", json={"query": "test"})
    assert resp.status_code in (200, 422)  # 422 for validation errors

# --- Security Tests ---

def test_csrf_token_present_on_forms():
    resp = client.get("/config")
    assert "csrf" in resp.text.lower()
    resp = client.get("/content")
    assert "csrf" in resp.text.lower()

def test_csrf_protection_enforced():
    # Simulate POST without CSRF token
    resp = client.post("/config", data={"key": "value"})
    assert resp.status_code in (400, 403)

def test_content_security_policy_header():
    resp = client.get("/")
    assert "content-security-policy" in resp.headers

def test_input_validation_on_config_update():
    resp = client.post("/api/v1/config", json={"invalid": "data"})
    assert resp.status_code in (400, 422)

# --- Performance Tests ---

def test_dashboard_page_load_time():
    import time
    start = time.time()
    resp = client.get("/")
    elapsed = time.time() - start
    assert elapsed < 1.5

def test_static_file_serving():
    resp = client.get("/static/js/common.js")
    assert resp.status_code == 200
    assert "function" in resp.text

# --- Integration & Real-time Tests ---

def test_websocket_real_time_updates():
    with client.websocket_connect("/ws/updates") as ws:
        ws.send_text("ping")
        data = ws.receive_text()
        assert "pong" in data or "update" in data.lower()

# --- Error Handling Tests ---

def test_404_error_handling():
    resp = client.get("/nonexistent")
    assert resp.status_code == 404
    assert "not found" in resp.text.lower()

def test_api_error_handling():
    resp = client.post("/api/v1/config", json={"bad": "data"})
    assert resp.status_code in (400, 422)
    assert "error" in resp.text.lower()

# --- Configuration Tests ---

def test_config_reset_functionality():
    resp = client.post("/api/v1/config/reset")
    assert resp.status_code in (200, 204, 202)

# --- API Contract Tests ---

def test_api_contract_health():
    resp = client.get("/api/v1/health")
    assert resp.headers["content-type"].startswith("application/json")
    assert "status" in resp.json()

def test_api_contract_stats():
    resp = client.get("/api/v1/stats")
    assert resp.headers["content-type"].startswith("application/json")
    assert "metrics" in resp.json()

def test_api_contract_collections():
    resp = client.get("/api/v1/collections")
    assert resp.headers["content-type"].startswith("application/json")
    assert isinstance(resp.json(), list)

def test_api_contract_config():
    resp = client.get("/api/v1/config")
    assert resp.headers["content-type"].startswith("application/json")
    assert isinstance(resp.json(), dict)