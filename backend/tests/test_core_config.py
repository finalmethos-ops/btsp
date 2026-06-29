import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _production_settings(**overrides: str) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "SECRET_KEY": "production-secret-key-with-32-bytes",
        "BOOTSTRAP_ADMIN_TOKEN": "production-bootstrap-token",
        "CORS_ORIGINS": "https://btsp.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_production_settings_accept_explicit_safe_values() -> None:
    settings = _production_settings()

    assert settings.environment == "production"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"SECRET_KEY": "change-me-before-production"}, "SECRET_KEY must be changed"),
        ({"SECRET_KEY": "too-short"}, "SECRET_KEY must be at least 32 bytes"),
        (
            {"BOOTSTRAP_ADMIN_TOKEN": "change-me-before-bootstrap"},
            "BOOTSTRAP_ADMIN_TOKEN must be changed",
        ),
        ({"CORS_ORIGINS": "http://localhost:3000"}, "CORS_ORIGINS must not use localhost"),
    ],
)
def test_production_settings_reject_unsafe_values(overrides: dict[str, str], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        _production_settings(**overrides)
