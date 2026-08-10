from io import BytesIO

import pytest
from PIL import Image

from app.services.presentation_image_service import (
    MAX_PRESENTATION_PIXELS,
    PresentationImageError,
    normalize_presentation_image,
    normalized_image_filename,
)


def _image_bytes(
    size: tuple[int, int],
    *,
    image_format: str = "PNG",
    mode: str = "RGB",
) -> bytes:
    output = BytesIO()
    color = (25, 75, 125, 160) if mode == "RGBA" else (25, 75, 125)
    Image.new(mode, size, color).save(output, image_format)
    return output.getvalue()


def test_presentation_image_is_resized_and_converted_to_webp() -> None:
    source = _image_bytes((3000, 2000))

    content_type, content = normalize_presentation_image(source, "image/png")

    assert content_type == "image/webp"
    assert len(content) < len(source)
    with Image.open(BytesIO(content)) as image:
        assert image.format == "WEBP"
        assert image.width <= 1920
        assert image.height <= 1080


def test_lossless_logo_preserves_alpha_channel() -> None:
    source = _image_bytes((1600, 800), mode="RGBA")

    content_type, content = normalize_presentation_image(
        source,
        "image/png",
        max_size=(1200, 600),
        lossless=True,
    )

    assert content_type == "image/webp"
    with Image.open(BytesIO(content)) as image:
        assert image.mode == "RGBA"
        assert image.size == (1200, 600)
        assert image.getpixel((0, 0))[3] == 160


def test_corrupt_or_mismatched_image_is_rejected() -> None:
    with pytest.raises(PresentationImageError, match="could not be decoded"):
        normalize_presentation_image(b"\x89PNG\r\n\x1a\ncorrupt", "image/png")

    with pytest.raises(PresentationImageError, match="declared type"):
        normalize_presentation_image(_image_bytes((10, 10)), "image/jpeg")


def test_excessive_pixel_dimensions_are_rejected_before_decode() -> None:
    width = 8001
    height = MAX_PRESENTATION_PIXELS // width + 1
    output = BytesIO()
    Image.new("1", (width, height), 0).save(output, "PNG")

    with pytest.raises(PresentationImageError, match="40-megapixel"):
        normalize_presentation_image(output.getvalue(), "image/png")


def test_normalized_filename_removes_paths_and_updates_extension() -> None:
    assert (
        normalized_image_filename("../../unsafe/product.photo.png", "image/webp")
        == "product.photo.webp"
    )


def test_normalized_webp_is_idempotent() -> None:
    source = _image_bytes((640, 480), image_format="WEBP")

    content_type, content = normalize_presentation_image(source, "image/webp")

    assert content_type == "image/webp"
    assert content == source
