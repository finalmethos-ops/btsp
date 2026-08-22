from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PRESENTATION_PIXELS = 40_000_000
PRESENTATION_IMAGE_SIZE = (3840, 2160)
VENDOR_LOGO_SIZE = (1200, 600)


class PresentationImageError(ValueError):
    pass


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in {"RGBA", "LA"} or (image.mode == "P" and "transparency" in image.info)


def normalize_presentation_image(
    content: bytes,
    content_type: str,
    *,
    max_size: tuple[int, int] = PRESENTATION_IMAGE_SIZE,
    lossless: bool = False,
) -> tuple[str, bytes]:
    """Fully validate and create a browser-efficient presentation asset."""

    expected_format = {
        "image/jpeg": "JPEG",
        "image/png": "PNG",
        "image/webp": "WEBP",
    }.get(content_type)
    if expected_format is None:
        raise PresentationImageError("Presentation image must be PNG, JPEG, or WebP")
    try:
        with Image.open(BytesIO(content)) as source:
            if source.format != expected_format:
                raise PresentationImageError(
                    "Presentation image content does not match its declared type"
                )
            if source.width * source.height > MAX_PRESENTATION_PIXELS:
                raise PresentationImageError(
                    "Presentation image exceeds the 40-megapixel safety limit"
                )
            if getattr(source, "is_animated", False):
                raise PresentationImageError("Animated presentation images are not supported")
            original_size = source.size
            image = ImageOps.exif_transpose(source)
            image.load()
    except PresentationImageError:
        raise
    except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError) as exc:
        raise PresentationImageError("Presentation image could not be decoded") from exc

    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    resized = image.size != original_size
    if content_type == "image/webp" and not resized:
        return content_type, content
    image = image.convert("RGBA" if _has_alpha(image) else "RGB")
    output = BytesIO()
    save_options: dict[str, object] = {
        "format": "WEBP",
        "method": 6,
        "exact": True,
    }
    if lossless:
        save_options["lossless"] = True
    else:
        save_options["quality"] = 96
    try:
        image.save(output, **save_options)
    except (OSError, ValueError) as exc:
        raise PresentationImageError("Presentation image could not be normalized") from exc
    normalized = output.getvalue()
    if not resized and len(normalized) >= len(content):
        return content_type, content
    return "image/webp", normalized


def normalized_image_filename(filename: str, content_type: str) -> str:
    safe_name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if content_type != "image/webp":
        return safe_name[:255]
    stem = safe_name.rsplit(".", 1)[0] or "presentation-image"
    return f"{stem[:250]}.webp"
