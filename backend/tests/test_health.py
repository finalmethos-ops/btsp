from fastapi.testclient import TestClient

from app.main import app
from app.services.system_health_service import _storage_health


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
