import jwt
import pytest

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.core.config import settings


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", password_hash) is True
    assert verify_password("incorrect", password_hash) is False


def test_access_token_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret-key-with-at-least-32-bytes")
    token = create_access_token("admin@example.com")

    payload = decode_access_token(token)

    assert payload["sub"] == "admin@example.com"
    assert "exp" in payload
    assert payload["iss"] == settings.app_name
    assert payload["aud"] == settings.app_name
    assert "jti" in payload


def test_legacy_token_without_required_claims_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret-key-with-at-least-32-bytes")
    token = jwt.encode({"sub": "admin@example.com"}, settings.secret_key, algorithm="HS256")

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token)


@pytest.mark.parametrize(
    "password_hash",
    [
        "",
        "not-a-password-hash",
        "pbkdf2_sha256$invalid$salt$digest",
        "pbkdf2_sha256$1$salt$" + ("0" * 64),
        "pbkdf2_sha256$999999999$salt$" + ("0" * 64),
        "unknown$600000$salt$" + ("0" * 64),
        "pbkdf2_sha256$600000$salt$short",
    ],
)
def test_malformed_password_hash_fails_closed(password_hash: str) -> None:
    assert verify_password("password", password_hash) is False
