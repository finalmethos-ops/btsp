import argparse

from app.db.session import SessionLocal
from app.services.store_batch_service import process_store_batch
from app.services.store_workbook_import import load_store_workbook


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the official Buddy's store workbook")
    parser.add_argument("workbook", help="Path to the .xlsx workbook")
    parser.add_argument("--submitted-by", default="local-store-import")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--authoritative",
        action="store_true",
        help="Deactivate active stores that are absent from this workbook",
    )
    args = parser.parse_args()

    payload = load_store_workbook(args.workbook, args.submitted_by)
    entities = sorted({row.entity_code for row in payload.rows if row.entity_code})
    regions = sorted({row.region_code for row in payload.rows})
    programs = sorted({row.purchasing_program for row in payload.rows if row.purchasing_program})
    print(
        f"validated rows={len(payload.rows)} entities={len(entities)} "
        f"regions={len(regions)} programs={','.join(programs)}"
    )
    if args.dry_run:
        return
    with SessionLocal() as db:
        result = process_store_batch(db, payload)
        deactivated = 0
        if args.authoritative and not result.failed_rows:
            from app.services.store_batch_service import deactivate_stores_missing_from_batch

            deactivated = deactivate_stores_missing_from_batch(db, payload)
        print(
            f"imported rows={result.upserted_rows} failed={result.failed_rows} "
            f"deactivated={deactivated} source={result.source_system}"
        )
        if result.errors:
            for error in result.errors:
                print(f"row={error.row_number} store={error.store_number}: {error.message}")


if __name__ == "__main__":
    main()
