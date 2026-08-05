import json
import re

from fastapi.testclient import TestClient

from app.main import app
from app.services.system_health_service import _storage_health


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_id_is_returned_and_access_log_is_structured(caplog) -> None:
    caplog.set_level("INFO", logger="btsp.access")
    client = TestClient(app)

    supplied = client.get("/api/v1/health", headers={"X-Request-ID": "support-case-123"})
    generated = client.get("/api/v1/health", headers={"X-Request-ID": "invalid request id"})

    assert supplied.headers["X-Request-ID"] == "support-case-123"
    assert re.fullmatch(r"[0-9a-f]{32}", generated.headers["X-Request-ID"])
    request_logs = [
        json.loads(record.message) for record in caplog.records if record.name == "btsp.access"
    ]
    assert request_logs[-2]["request_id"] == "support-case-123"
    assert request_logs[-2]["path"] == "/api/v1/health"
    assert request_logs[-2]["status"] == 200
    assert request_logs[-2]["duration_ms"] >= 0
    assert request_logs[-1]["request_id"] == generated.headers["X-Request-ID"]


def test_readiness_returns_503_without_exposing_dependency_details(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.routes.health.dependencies_ready", lambda _engine, _redis_url: False
    )
    client = TestClient(app)

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_storage_health_reports_writable_and_missing_paths(tmp_path) -> None:
    healthy = _storage_health("test", str(tmp_path))
    missing = _storage_health("missing", str(tmp_path / "missing"))

    assert healthy.status == "healthy"
    assert healthy.writable is True
    assert healthy.free_bytes and healthy.free_bytes > 0
    assert missing.status == "unavailable"
    assert missing.writable is False
