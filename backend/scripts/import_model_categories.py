import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.model_category_service import import_model_categories


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the model category taxonomy")
    parser.add_argument("workbook")
    args = parser.parse_args()
    with SessionLocal() as db:
        created, updated = import_model_categories(db, Path(args.workbook).read_bytes())
        print(f"model categories created={created} updated={updated}")


if __name__ == "__main__":
    main()
