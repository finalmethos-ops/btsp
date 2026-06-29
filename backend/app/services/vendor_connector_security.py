from typing import Any
from urllib.parse import urlsplit

_SECRET_KEY_MARKERS = {
    "api_key",
    "apikey",
    "access_token",
    "authorization",
    "client_secret",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
}


def configuration_contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(marker in normalized for marker in _SECRET_KEY_MARKERS):
                return True
            if configuration_contains_secret(nested):
                return True
        return False
    if isinstance(value, list):
        return any(configuration_contains_secret(item) for item in value)
    if isinstance(value, str) and "://" in value:
        try:
            parsed = urlsplit(value)
        except ValueError:
            return True
        return parsed.username is not None or parsed.password is not None
    return False
