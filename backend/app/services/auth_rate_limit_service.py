import hashlib
import threading
import time
from collections import deque

from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings

_FALLBACK_MAX_KEYS = 10_000
_fallback_attempts: dict[str, deque[float]] = {}
_fallback_lock = threading.Lock()


class LoginRateLimitError(ValueError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many login attempts")
        self.retry_after = max(1, retry_after)


def _login_keys(email: str, client_host: str) -> tuple[str, str]:
    email_digest = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()
    host_digest = hashlib.sha256(client_host.encode("utf-8")).hexdigest()
    return f"btsp:login:email:{email_digest}", f"btsp:login:host:{host_digest}"


def _register_fallback_attempt(keys: tuple[str, str], now: float | None = None) -> None:
    current = time.monotonic() if now is None else now
    window = settings.login_rate_limit_window_seconds
    cutoff = current - window
    limits = (settings.login_rate_limit_email_attempts, settings.login_rate_limit_host_attempts)
    retry_after = 0
    with _fallback_lock:
        for key, limit in zip(keys, limits, strict=True):
            attempts = _fallback_attempts.setdefault(key, deque())
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            attempts.append(current)
            if len(attempts) > limit:
                retry_after = max(retry_after, int(attempts[0] + window - current) + 1)
        while len(_fallback_attempts) > _FALLBACK_MAX_KEYS:
            _fallback_attempts.pop(next(iter(_fallback_attempts)))
    if retry_after:
        raise LoginRateLimitError(retry_after)


def _clear_fallback_attempts(keys: tuple[str, str]) -> None:
    with _fallback_lock:
        for key in keys:
            _fallback_attempts.pop(key, None)


def register_login_attempt(email: str, client_host: str) -> tuple[str, str]:
    keys = _login_keys(email, client_host)
    try:
        client = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        pipeline = client.pipeline()
        for key in keys:
            pipeline.incr(key)
            pipeline.expire(key, settings.login_rate_limit_window_seconds, nx=True)
        results = pipeline.execute()
        email_count = int(results[0])
        host_count = int(results[2])
        if (
            email_count > settings.login_rate_limit_email_attempts
            or host_count > settings.login_rate_limit_host_attempts
        ):
            retry_after = max(int(client.ttl(key)) for key in keys)
            raise LoginRateLimitError(retry_after)
    except LoginRateLimitError:
        raise
    except (RedisError, OSError, ValueError):
        _register_fallback_attempt(keys)
    return keys


def clear_login_attempts(keys: tuple[str, str]) -> None:
    _clear_fallback_attempts(keys)
    try:
        Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
        ).delete(*keys)
    except (RedisError, OSError):
        pass
