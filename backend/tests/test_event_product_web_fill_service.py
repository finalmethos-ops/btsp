from email.message import Message
from urllib.request import Request

import pytest

from app.services import event_product_web_fill_service as service


class _ImageResponse:
    def __init__(self, content_type: str, content: bytes) -> None:
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self._content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self._content


def test_web_image_redirects_must_remain_public_https() -> None:
    handler = service._PublicHttpsRedirectHandler()

    with pytest.raises(service.EventProductWebFillError, match="public HTTPS"):
        handler.redirect_request(
            Request("https://images.example.com/product.png"),
            None,
            302,
            "Found",
            {},
            "http://127.0.0.1/internal.png",
        )


def test_web_image_content_must_match_declared_type(monkeypatch) -> None:
    monkeypatch.setattr(
        service.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(2, 1, 6, "", ("93.184.216.34", 443))],
    )
    monkeypatch.setattr(
        service,
        "_open_public_url",
        lambda _request, timeout: _ImageResponse("image/png", b"not-a-png"),
    )

    with pytest.raises(service.EventProductWebFillError, match="declared type"):
        service.download_public_image("https://images.example.com/product.png")
