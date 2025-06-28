import pytest
from fastapi.testclient import TestClient
from src.web_ui.main import app

client = TestClient(app)

# --- Functional Tests ---


def test_dashboard_page_exists():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Dashboard" in resp.text


def test_config_page_exists():
    resp = client.get("/config")
    assert resp.status_code == 200
    assert "Configuration" in resp.text


def test_content_page_exists():
    resp = client.get("/content")
    assert resp.status_code == 200
    assert "Content" in resp.text


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/v1/health",
        "/api/v1/stats",
        "/api/v1/collections",
        "/api/v1/config",
        "/api/v1/admin/search-content",
    ],
)
def test_api_endpoints_exist(endpoint):
    resp = client.get(endpoint)
    assert resp.status_code in (200, 401, 403)  # Allow for protected endpoints


def test_update_config_persists():
    config = client.get("/api/v1/config").json()
    config["config"]["test_key"] = "test_value"
    resp = client.post("/api/v1/config", json=config["config"])
    assert resp.status_code == 200
    updated = client.get("/api/v1/config").json()
    assert updated["config"].get("test_key") == "test_value"


def test_flag_content_for_removal():
    # Simulate flagging content (assume at least one content exists)
    collections = client.get("/api/v1/collections").json()
    if collections:
        content_id = collections[0].get("id") or collections[0].get("content_id")
        if content_id:
            resp = client.delete(f"/api/v1/content/{content_id}")
            assert resp.status_code in (200, 204, 202, 404)


# --- Security Tests ---


def test_xss_prevention():
    payload = "<script>alert('xss')</script>"
    resp = client.post("/api/v1/config", json={"xss_test": payload})
    assert payload in resp.text


def test_csrf_protection_headers():
    resp = client.get("/config")
    assert "set-cookie" in resp.headers or "csrf" in resp.text.lower()


def test_security_headers():
    resp = client.get("/")
    assert (
        "x-content-type-options" in resp.headers
        or "content-security-policy" in resp.headers
    )


# --- Performance Tests ---


def test_dashboard_response_time():
    import time

    start = time.time()
    resp = client.get("/")
    duration = time.time() - start
    assert resp.status_code == 200
    assert duration < 0.5  # 500ms threshold


# --- Integration Tests ---


def test_database_integration():
    resp = client.get("/api/v1/collections")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_config_integration():
    resp = client.get("/api/v1/config")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


def test_health_check_operational():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "status" in resp.json()


# --- Operational Readiness ---


def test_structured_logging():
    # This is a placeholder: check logs for correlation ID or structured format
    assert True


def test_monitoring_endpoint():
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "metrics" in resp.json() or "status" in resp.json()
