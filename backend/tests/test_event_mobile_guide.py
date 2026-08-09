from datetime import UTC, datetime
from io import BytesIO

from pypdf import PdfReader
from starlette.requests import Request

from app.api.v1.routes.event_presentations import _request_origin
from app.models.event_management import ManagedEvent, ManagedSubEvent
from app.services.event_mobile_guide_service import render_event_mobile_quick_start_pdf


def test_mobile_guide_origin_ignores_client_forwarded_host() -> None:
    request = Request(
        {
            "type": "http",
            "scheme": "https",
            "server": ("purchasing-events.us", 443),
            "path": "/api/v1/event-presentations/example/mobile-quick-start.pdf",
            "headers": [
                (b"host", b"purchasing-events.us"),
                (b"x-forwarded-host", b"attacker.example"),
                (b"x-forwarded-proto", b"https"),
            ],
        }
    )

    assert _request_origin(request) == "https://purchasing-events.us"


def test_mobile_quick_start_pdf_contains_event_login_and_instructions() -> None:
    event = ManagedEvent(
        id="event-1",
        slug="leadership-meeting-2027",
        name="2027 Buddy's Leadership Meeting",
        status="published",
        starts_at=datetime(2027, 8, 9, 13, tzinfo=UTC),
        ends_at=datetime(2027, 8, 12, 21, tzinfo=UTC),
        timezone="America/New_York",
        venue_name="Convention Center",
        address_line1="100 Show Way",
        city="Orlando",
        state_code="FL",
        postal_code="32801",
        theme_primary_color="#07142c",
        theme_accent_color="#ffd400",
        created_by="admin@example.com",
    )
    sub_event = ManagedSubEvent(
        id="sub-event-1",
        event_id=event.id,
        name="2027 Hot Show",
        starts_at=datetime(2027, 8, 10, 23, tzinfo=UTC),
        ends_at=datetime(2027, 8, 11, 1, tzinfo=UTC),
        location="Pacifica Ballroom",
        status="published",
        module_codes=["live_display"],
    )
    login_url = "https://purchasing-events.us/event-login"

    content = render_event_mobile_quick_start_pdf(event, sub_event, login_url)

    assert content.startswith(b"%PDF")
    assert len(content) > 5_000
    reader = PdfReader(BytesIO(content))
    assert len(reader.pages) == 1
    text = reader.pages[0].extract_text()
    assert "LIVE EVENT MOBILE QUICK START" in text
    assert "2027 Buddy's Leadership Meeting" in text
    assert "2027 Hot Show" in text
    assert login_url in text
    assert "Join event" in text
    assert "Franchise representatives" in text
    assert "Vendor representatives" in text
    assert "MOBILE CHECKLIST" in text
