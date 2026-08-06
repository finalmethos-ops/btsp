import jwt
import pytest

from app.auth.security import (
    create_access_token,
    create_presenter_token,
    create_projector_token,
    decode_access_token,
    decode_presenter_token,
    decode_projector_token,
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


def test_projector_token_is_read_only_and_sub_event_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret-key-with-at-least-32-bytes")
    token, expires_at = create_projector_token("sub-event-a")

    payload = decode_projector_token(token, "sub-event-a")

    assert payload["scope"] == "event_projector"
    assert payload["sub_event_id"] == "sub-event-a"
    assert payload["aud"] == f"{settings.app_name}:projector"
    assert expires_at.isoformat()
    with pytest.raises(jwt.PyJWTError):
        decode_projector_token(token, "sub-event-b")


def test_user_access_token_cannot_be_used_as_projector_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret-key-with-at-least-32-bytes")

    with pytest.raises(jwt.PyJWTError):
        decode_projector_token(create_access_token("admin@example.com"), "sub-event-a")


def test_presenter_token_is_read_only_and_sub_event_scoped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "secret_key", "test-secret-key-with-at-least-32-bytes")
    token, expires_at = create_presenter_token("sub-event-a")

    payload = decode_presenter_token(token, "sub-event-a")

    assert payload["scope"] == "event_presenter_monitor"
    assert payload["sub_event_id"] == "sub-event-a"
    assert payload["aud"] == f"{settings.app_name}:presenter-monitor"
    assert expires_at.isoformat()
    with pytest.raises(jwt.PyJWTError):
        decode_presenter_token(token, "sub-event-b")
    with pytest.raises(jwt.PyJWTError):
        decode_projector_token(token, "sub-event-a")


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
