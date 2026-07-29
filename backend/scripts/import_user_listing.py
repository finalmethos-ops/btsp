import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.user_listing_import import import_user_listing


def main() -> None:
    parser = argparse.ArgumentParser(description="Import approved BTSP user listing workbook")
    parser.add_argument("workbook")
    args = parser.parse_args()
    with SessionLocal() as db:
        created, skipped = import_user_listing(Path(args.workbook).read_bytes(), db)
        print(f"users created={created} existing skipped={skipped}")


if __name__ == "__main__":
    main()
