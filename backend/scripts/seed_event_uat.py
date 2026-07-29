import argparse
import os

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.event_demo_service import seed_event_demo_event


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the local BTSP full-lifecycle UAT event")
    parser.add_argument(
        "--password",
        default=os.getenv("BTSP_DEMO_PASSWORD", "BTSP-Demo-2026!"),
        help="Shared local demo password (or set BTSP_DEMO_PASSWORD)",
    )
    args = parser.parse_args()
    if settings.environment.lower() == "production":
        raise RuntimeError("Event UAT data cannot be seeded in production")
    with SessionLocal() as db:
        event = seed_event_demo_event(db, args.password)
    print(f"UAT event ready: {event.name} ({event.slug})")


if __name__ == "__main__":
    main()
