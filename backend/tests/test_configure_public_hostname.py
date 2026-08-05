from __future__ import annotations

import argparse

import pytest

from scripts.configure_public_hostname import public_hostname, update_environment


def test_public_hostname_normalizes_valid_name() -> None:
    assert public_hostname("App.BTSP-Platform.com.") == "app.btsp-platform.com"


@pytest.mark.parametrize(
    "hostname",
    [
        "localhost",
        "192.168.0.146",
        "https://app.example.com",
        "-app.example.com",
        "app_example.com",
    ],
)
def test_public_hostname_rejects_non_public_name(hostname: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        public_hostname(hostname)


def test_update_environment_preserves_private_origin_and_secrets() -> None:
    source = "SECRET_KEY=do-not-change\n" "CORS_ORIGINS=https://192.168.0.146:18443\n"

    result = update_environment(source, "app.example.com")

    assert "SECRET_KEY=do-not-change" in result
    assert "CORS_ORIGINS=https://app.example.com,https://192.168.0.146:18443" in result
    assert "BTSP_PUBLIC_HOSTNAME=app.example.com" in result


def test_update_environment_is_idempotent() -> None:
    source = "CORS_ORIGINS=https://app.example.com\n"
    first = update_environment(source, "app.example.com")
    second = update_environment(first, "app.example.com")

    assert first == second
