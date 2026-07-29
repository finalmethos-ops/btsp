from __future__ import annotations

import argparse

import pytest

from scripts.generate_intranet_env import private_ipv4, render_environment, tcp_port


def test_private_ipv4_accepts_rfc_1918_address() -> None:
    assert private_ipv4("192.168.0.146") == "192.168.0.146"


@pytest.mark.parametrize("address", ["8.8.8.8", "127.0.0.1", "169.254.1.1"])
def test_private_ipv4_rejects_non_rfc_1918_address(address: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        private_ipv4(address)


@pytest.mark.parametrize("port", ["0", "65536"])
def test_tcp_port_rejects_out_of_range_values(port: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        tcp_port(port)


def test_render_environment_uses_unique_secrets() -> None:
    first = render_environment("192.168.0.146", 18080)
    second = render_environment("192.168.0.146", 18080)

    assert "ENVIRONMENT=production" in first
    assert "CORS_ORIGINS=http://192.168.0.146:18080" in first
    assert first != second
