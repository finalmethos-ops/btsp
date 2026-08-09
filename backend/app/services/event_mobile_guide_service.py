from __future__ import annotations

import warnings
from datetime import UTC, datetime
from io import BytesIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    import pymupdf  # noqa: E402

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph

from app.models.event_management import EventBrandingAsset, ManagedEvent, ManagedSubEvent


def _color(value: str | None, fallback: str) -> colors.Color:
    try:
        return colors.HexColor(value or fallback)
    except (TypeError, ValueError):
        return colors.HexColor(fallback)


def _readable_text(background: colors.Color) -> colors.Color:
    luminance = (0.299 * background.red) + (0.587 * background.green) + (0.114 * background.blue)
    return colors.HexColor("#07142c") if luminance > 0.58 else colors.white


def _event_datetime(value: datetime, timezone_name: str) -> datetime:
    try:
        timezone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        timezone = UTC
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(timezone)


def _friendly_date(value: datetime) -> str:
    return f"{value.strftime('%A, %B')} {value.day}"


def _friendly_time(value: datetime) -> str:
    return value.strftime("%I:%M %p").lstrip("0")


def _draw_paragraph(
    canvas: Canvas,
    text: str,
    *,
    x: float,
    top: float,
    width: float,
    style: ParagraphStyle,
) -> float:
    paragraph = Paragraph(text, style)
    _, height = paragraph.wrap(width, 500)
    paragraph.drawOn(canvas, x, top - height)
    return top - height


def _draw_branding(
    canvas: Canvas,
    asset: EventBrandingAsset | None,
    *,
    x: float,
    y: float,
    max_width: float,
    max_height: float,
) -> None:
    if asset is None or not asset.content_type.startswith("image/"):
        return
    try:
        image = ImageReader(BytesIO(asset.content))
        width, height = image.getSize()
        scale = min(max_width / width, max_height / height)
        draw_width = width * scale
        draw_height = height * scale
        canvas.drawImage(
            image,
            x + max_width - draw_width,
            y + (max_height - draw_height) / 2,
            width=draw_width,
            height=draw_height,
            preserveAspectRatio=True,
            mask="auto",
        )
    except Exception:  # A guide must remain available when an old asset is malformed.
        return


def _draw_qr(canvas: Canvas, value: str, *, x: float, y: float, size: float) -> None:
    widget = QrCodeWidget(value)
    left, bottom, right, top = widget.getBounds()
    source_width = right - left
    source_height = top - bottom
    scale = min(size / source_width, size / source_height)
    drawing = Drawing(
        size,
        size,
        transform=[scale, 0, 0, scale, -left * scale, -bottom * scale],
    )
    drawing.add(widget)
    renderPDF.draw(drawing, canvas, x, y)


def render_event_mobile_quick_start_pdf(
    event: ManagedEvent,
    sub_event: ManagedSubEvent,
    login_url: str,
    branding: EventBrandingAsset | None = None,
) -> bytes:
    """Render a one-page guide suitable for printing or full-screen projection."""

    buffer = BytesIO()
    page_width, page_height = landscape(letter)
    canvas = Canvas(buffer, pagesize=(page_width, page_height), invariant=1)
    canvas.setTitle(f"{event.name} mobile live event quick start")
    canvas.setAuthor("BTSP Event Management")

    primary = _color(event.theme_primary_color, "#07142c")
    accent = _color(event.theme_accent_color, "#ffd400")
    primary_text = _readable_text(primary)
    accent_text = _readable_text(accent)
    ink = colors.HexColor("#07142c")
    muted = colors.HexColor("#50627a")

    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, page_width, page_height, stroke=0, fill=1)
    canvas.setFillColor(primary)
    canvas.rect(0, page_height - 96, page_width, 96, stroke=0, fill=1)
    canvas.setFillColor(accent)
    canvas.rect(0, page_height - 102, page_width, 6, stroke=0, fill=1)

    canvas.setFillColor(primary_text)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(34, page_height - 31, "LIVE EVENT MOBILE QUICK START")
    canvas.setFont("Helvetica-Bold", 24)
    event_title = event.name
    while stringWidth(event_title, "Helvetica-Bold", 24) > 535 and len(event_title) > 20:
        event_title = f"{event_title[:-4].rstrip()}..."
    canvas.drawString(34, page_height - 61, event_title)
    canvas.setFont("Helvetica", 12)
    canvas.drawString(34, page_height - 82, sub_event.name)
    _draw_branding(
        canvas,
        branding,
        x=620,
        y=page_height - 88,
        max_width=138,
        max_height=72,
    )

    section_style = ParagraphStyle(
        "guide-section",
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=ink,
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "guide-body",
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=ink,
        spaceAfter=5,
    )
    small_center = ParagraphStyle(
        "guide-url",
        parent=body_style,
        fontSize=8.5,
        leading=11,
        alignment=TA_CENTER,
        textColor=muted,
    )

    # QR sign-in card.
    canvas.setFillColor(colors.HexColor("#f5f8fc"))
    canvas.setStrokeColor(colors.HexColor("#c9d5e5"))
    canvas.roundRect(34, 207, 224, 286, 14, stroke=1, fill=1)
    canvas.setFillColor(ink)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawCentredString(146, 465, "SCAN TO SIGN IN")
    canvas.setFillColor(colors.white)
    canvas.roundRect(55, 248, 182, 198, 10, stroke=0, fill=1)
    _draw_qr(canvas, login_url, x=60, y=258, size=172)
    _draw_paragraph(
        canvas,
        f"<b>Event login:</b><br/>{login_url}",
        x=48,
        top=239,
        width=196,
        style=small_center,
    )

    start = _event_datetime(sub_event.starts_at, event.timezone)
    end = _event_datetime(sub_event.ends_at, event.timezone)
    date_line = (
        f"{_friendly_date(start)} &middot; " f"{_friendly_time(start)} - {_friendly_time(end)}"
    )
    location_line = sub_event.location or event.venue_name

    right_x = 282
    right_width = 476
    top = 492
    top = _draw_paragraph(
        canvas,
        "How to join on your phone",
        x=right_x,
        top=top,
        width=right_width,
        style=section_style,
    )
    top = _draw_paragraph(
        canvas,
        f"<b>{date_line}</b><br/>{location_line}",
        x=right_x,
        top=top - 2,
        width=right_width,
        style=body_style,
    )
    steps = (
        "<b>1. Sign in.</b> Scan the QR code and use your registered event email and "
        "password. Complete a temporary-password change if prompted.<br/>"
        "<b>2. Open the event.</b> Choose this event if an event list appears. Your event "
        "calendar opens automatically.<br/>"
        f"<b>3. Join the live module.</b> Find <b>{sub_event.name}</b> on the calendar and "
        "tap <b>Join event</b> when access is available.<br/>"
        "<b>4. Participate.</b> Keep the event page open while the presentation is running. "
        "The projector presentation is intentionally visible only in the room."
    )
    top = _draw_paragraph(
        canvas,
        steps,
        x=right_x,
        top=top - 5,
        width=right_width,
        style=body_style,
    )

    canvas.setFillColor(primary)
    canvas.roundRect(right_x, 207, right_width, 118, 12, stroke=0, fill=1)
    canvas.setFillColor(primary_text)
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(right_x + 15, 303, "WHAT YOU WILL SEE")
    role_style = ParagraphStyle(
        "guide-roles",
        fontName="Helvetica",
        fontSize=9.2,
        leading=12.2,
        textColor=primary_text,
    )
    _draw_paragraph(
        canvas,
        "<b>Franchise representatives:</b> Select the permitted store, choose a product and "
        "quantity while ordering is open, then submit and confirm the order.<br/>"
        "<b>Vendor representatives:</b> Follow live totals for your products and see when your "
        "next product is coming up.<br/>"
        "<b>Executives:</b> View live event performance. <b>Admins/staff:</b> Open only the "
        "controls assigned to your event role.",
        x=right_x + 15,
        top=288,
        width=right_width - 30,
        style=role_style,
    )

    # A low-ink footer remains readable when projected or printed in grayscale.
    canvas.setFillColor(accent)
    canvas.roundRect(34, 38, page_width - 68, 142, 14, stroke=0, fill=1)
    canvas.setFillColor(accent_text)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(52, 153, "MOBILE CHECKLIST")
    checklist_style = ParagraphStyle(
        "guide-checklist",
        fontName="Helvetica",
        fontSize=10.5,
        leading=14,
        textColor=accent_text,
    )
    _draw_paragraph(
        canvas,
        "&bull; Use the venue Wi-Fi or a reliable mobile connection.<br/>"
        "&bull; Allow event alerts when prompted and keep your phone available.<br/>"
        "&bull; Confirm the selected store, product, and quantity before submitting.<br/>"
        "&bull; If a page is interrupted, reopen the event calendar and tap "
        "<b>Join event</b> again.",
        x=52,
        top=137,
        width=438,
        style=checklist_style,
    )
    canvas.setStrokeColor(accent_text)
    canvas.setLineWidth(1)
    canvas.line(514, 55, 514, 156)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(534, 139, "NEED HELP?")
    canvas.setFont("Helvetica", 10.5)
    help_text = (
        "Ask an onsite event staff member. Do not share your password or QR-enabled "
        "account access with another attendee."
    )
    _draw_paragraph(
        canvas,
        help_text,
        x=534,
        top=124,
        width=210,
        style=checklist_style,
    )

    canvas.setFillColor(muted)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(page_width - 34, 18, "Generated by BTSP Event Management")
    canvas.showPage()
    canvas.save()
    return buffer.getvalue()


def render_event_mobile_quick_start_image(
    event: ManagedEvent,
    sub_event: ManagedSubEvent,
    login_url: str,
    branding: EventBrandingAsset | None = None,
) -> bytes:
    """Render the printable guide as a projector-ready full-screen slide image."""

    pdf = render_event_mobile_quick_start_pdf(event, sub_event, login_url, branding)
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        page = document[0]
        image = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        return image.tobytes("png")
