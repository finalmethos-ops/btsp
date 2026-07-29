import pytest
from redis.exceptions import RedisError

from app.services.auth_rate_limit_service import (
    LoginRateLimitError,
    _clear_fallback_attempts,
    _login_keys,
    register_login_attempt,
)


class _Pipeline:
    def incr(self, _key: str) -> None:
        pass

    def expire(self, _key: str, _seconds: int, *, nx: bool) -> None:
        assert nx is True

    def execute(self) -> list[int | bool]:
        return [9, True, 1, True]


class _RedisClient:
    def pipeline(self) -> _Pipeline:
        return _Pipeline()

    def ttl(self, _key: str) -> int:
        return 120


def test_login_keys_do_not_expose_email_or_host() -> None:
    keys = _login_keys("Admin@Example.com", "192.0.2.1")

    assert all("admin" not in key and "192.0.2.1" not in key for key in keys)


def test_login_rate_limit_returns_retry_window(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.auth_rate_limit_service.Redis.from_url",
        lambda *_args, **_kwargs: _RedisClient(),
    )

    with pytest.raises(LoginRateLimitError) as error:
        register_login_attempt("admin@example.com", "192.0.2.1")

    assert error.value.retry_after == 120


def test_login_rate_limit_uses_bounded_fallback_when_redis_is_unavailable(
    monkeypatch,
) -> None:
    class _UnavailableRedis:
        @staticmethod
        def from_url(*_args, **_kwargs):
            raise RedisError("offline")

    monkeypatch.setattr(
        "app.services.auth_rate_limit_service.Redis",
        _UnavailableRedis,
    )
    monkeypatch.setattr(
        "app.services.auth_rate_limit_service.settings.login_rate_limit_email_attempts",
        2,
    )
    keys = _login_keys("fallback@example.com", "192.0.2.50")
    _clear_fallback_attempts(keys)
    try:
        register_login_attempt("fallback@example.com", "192.0.2.50")
        register_login_attempt("fallback@example.com", "192.0.2.50")
        with pytest.raises(LoginRateLimitError):
            register_login_attempt("fallback@example.com", "192.0.2.50")
    finally:
        _clear_fallback_attempts(keys)
