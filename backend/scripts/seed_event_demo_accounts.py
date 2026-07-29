import argparse
import os

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.event_demo_service import seed_event_demo_accounts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Activate local event demo identities and the PERF-001 vendor"
    )
    parser.add_argument(
        "--password",
        default=os.getenv("BTSP_DEMO_PASSWORD", "BTSP-Demo-2026!"),
        help="Shared local demo password (or set BTSP_DEMO_PASSWORD)",
    )
    args = parser.parse_args()
    if settings.environment.lower() == "production":
        raise RuntimeError("Event demo accounts cannot be seeded in production")
    with SessionLocal() as db:
        accounts = seed_event_demo_accounts(db, args.password)
    for account in accounts:
        qualifier = account.vendor_code or account.entity_code or ""
        print(
            f"{account.attendee_category}: {account.email}"
            f"{f' ({qualifier})' if qualifier else ''}"
        )


if __name__ == "__main__":
    main()
