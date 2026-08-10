"""Dry-run or normalize existing live-presentation media in place."""

from __future__ import annotations

import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import identity  # noqa: F401
from app.models.event_management import (
    EventProductSlideImage,
    EventProductSlideVendorLogo,
)
from app.services.presentation_image_service import (
    VENDOR_LOGO_SIZE,
    normalize_presentation_image,
    normalized_image_filename,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if args.apply and args.confirm != "OPTIMIZE_PRESENTATION_IMAGES":
        parser.error("--apply requires --confirm OPTIMIZE_PRESENTATION_IMAGES")
    return args


def main() -> int:
    args = _arguments()
    with SessionLocal() as db:
        images = list(db.scalars(select(EventProductSlideImage)).all())
        logos = list(db.scalars(select(EventProductSlideVendorLogo)).all())
        before_bytes = sum(len(asset.content) for asset in [*images, *logos])
        changed = 0
        for asset in images:
            content_type, content = normalize_presentation_image(
                asset.content,
                asset.content_type,
            )
            if content != asset.content or content_type != asset.content_type:
                changed += 1
                asset.content = content
                asset.content_type = content_type
                asset.filename = normalized_image_filename(asset.filename, content_type)
        for asset in logos:
            content_type, content = normalize_presentation_image(
                asset.content,
                asset.content_type,
                max_size=VENDOR_LOGO_SIZE,
                lossless=True,
            )
            if content != asset.content or content_type != asset.content_type:
                changed += 1
                asset.content = content
                asset.content_type = content_type
                asset.filename = normalized_image_filename(asset.filename, content_type)
        after_bytes = sum(len(asset.content) for asset in [*images, *logos])
        if args.apply:
            db.commit()
        else:
            db.rollback()
        print(
            {
                "mode": "apply" if args.apply else "dry-run",
                "slide_images": len(images),
                "vendor_logos": len(logos),
                "assets_changed": changed,
                "before_mb": round(before_bytes / 1_048_576, 2),
                "after_mb": round(after_bytes / 1_048_576, 2),
                "reduction_percent": (
                    round((1 - after_bytes / before_bytes) * 100, 1) if before_bytes else 0
                ),
            }
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
