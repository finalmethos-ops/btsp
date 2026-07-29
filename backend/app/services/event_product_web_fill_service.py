import ipaddress
import json
import socket
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.core.config import settings
from app.schemas.event_product_slide import EventProductWebFillResponse
from app.services.upload_validation import content_matches_declared_type

USER_AGENT = "BTSP-Event-Product-Research/1.0"


class EventProductWebFillError(ValueError):
    pass


class _PublicHttpsRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        _public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open_public_url(request: Request, timeout: int):
    return build_opener(_PublicHttpsRedirectHandler()).open(request, timeout=timeout)


def _public_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise EventProductWebFillError("Remote resource must use a public HTTPS URL")
    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    except OSError as exc:
        raise EventProductWebFillError("Remote host could not be resolved") from exc
    for address in addresses:
        if not ipaddress.ip_address(address[4][0]).is_global:
            raise EventProductWebFillError("Remote host is not public")
    return value


def _brave_json(path: str, query: str) -> dict:
    request = Request(
        f"https://api.search.brave.com/res/v1/{path}?q={quote(query)}&count=10",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "X-Subscription-Token": settings.brave_search_api_key or "",
        },
    )
    _public_url(request.full_url)
    with _open_public_url(request, timeout=8) as response:
        return json.loads(response.read(1_000_001))


def _full_size_image_url(query: str) -> str | None:
    """Return the source image URL, never the search provider thumbnail URL."""
    try:
        payload = _brave_json("images/search", query)
    except (OSError, ValueError, json.JSONDecodeError, EventProductWebFillError):
        return None
    for result in payload.get("results", []):
        properties = result.get("properties") or {}
        candidate = properties.get("url") or result.get("url")
        if not isinstance(candidate, str):
            continue
        try:
            return _public_url(candidate)
        except EventProductWebFillError:
            continue
    return None


def search_product(model_number: str, product_name: str | None) -> EventProductWebFillResponse:
    if not settings.brave_search_api_key:
        raise EventProductWebFillError(
            "Web Fill requires BRAVE_SEARCH_API_KEY in the BTSP environment"
        )
    query = " ".join(
        item
        for item in (
            model_number.strip(),
            (product_name or "").strip(),
            "product specifications",
        )
        if item
    )
    request = Request(
        f"https://api.search.brave.com/res/v1/web/search?q={quote(query)}&count=10",
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            "X-Subscription-Token": settings.brave_search_api_key,
        },
    )
    try:
        _public_url(request.full_url)
        with _open_public_url(request, timeout=8) as response:
            payload = json.loads(response.read(1_000_001))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise EventProductWebFillError("Product web search failed") from exc
    results = payload.get("web", {}).get("results", [])
    if not results:
        raise EventProductWebFillError("No web results were found for this model number")
    exact = model_number.casefold()
    result = next(
        (
            item
            for item in results
            if exact in f"{item.get('title', '')} {item.get('description', '')}".casefold()
        ),
        results[0],
    )
    image_url = _full_size_image_url(query)
    return EventProductWebFillResponse(
        model_number=model_number.strip(),
        title=(result.get("title") or product_name or model_number).strip(),
        summary=(result.get("description") or "No description was provided by the source").strip(),
        source_url=_public_url(result["url"]),
        image_url=image_url,
    )


def download_public_image(image_url: str) -> tuple[str, bytes]:
    safe_url = _public_url(image_url)
    request = Request(safe_url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"})
    try:
        with _open_public_url(request, timeout=8) as response:
            content_type = response.headers.get_content_type()
            if content_type not in {"image/png", "image/jpeg", "image/webp"}:
                raise EventProductWebFillError("Web result did not return a supported image")
            content = response.read(8 * 1024 * 1024 + 1)
    except EventProductWebFillError:
        raise
    except OSError as exc:
        raise EventProductWebFillError("Web image download failed") from exc
    if not content or len(content) > 8 * 1024 * 1024:
        raise EventProductWebFillError("Web image must be between 1 byte and 8 MB")
    if not content_matches_declared_type(content, content_type):
        raise EventProductWebFillError("Web image content does not match its declared type")
    return content_type, content
