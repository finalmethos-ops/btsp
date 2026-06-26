from app.schemas.event_snapshot import EventSnapshotCreate


def test_snapshot_schema_accepts_payload() -> None:
    snapshot = EventSnapshotCreate(
        event_type="store_batch_processed",
        entity_type="store_batch",
        entity_id="test_1",
        actor="tester",
        payload={"total_rows": 1, "changed_rows": 1},
    )

    assert snapshot.event_type == "store_batch_processed"
    assert snapshot.payload["changed_rows"] == 1
