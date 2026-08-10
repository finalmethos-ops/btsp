import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from app.schemas.event_order_review import (
    EventOrderReviewItem,
    EventOrderReviewSummary,
    EventOrderVariantLine,
)
from app.services import event_order_review_service


def test_review_csv_preserves_single_selected_model_from_combined_offer(monkeypatch) -> None:
    summary = EventOrderReviewSummary(
        event_id="event-1",
        event_name="Leadership Meeting",
        pending=1,
        approved=0,
        rejected=0,
        released=0,
        approved_units=0,
        approved_spend=Decimal("0"),
        items=[
            EventOrderReviewItem(
                order_id="order-1",
                sub_event_name="Hot Show",
                entity_code="BHF",
                vendor_code="VENDOR",
                model_number="COMBINED-OFFER",
                product_name="Three-product offer",
                quantity=4,
                unit_cost=Decimal("25.00"),
                total_cost=Decimal("100.00"),
                requested_delivery_start=date(2027, 8, 1),
                requested_delivery_end=date(2027, 8, 31),
                live_status="confirmed",
                review_status="pending",
                reviewed_by=None,
                reviewed_at=None,
                is_combined_offer=True,
                variant_lines=[
                    EventOrderVariantLine(
                        model_number="MODEL-B",
                        product_name="Selected product",
                        quantity=4,
                        unit_cost=Decimal("25.00"),
                        total_cost=Decimal("100.00"),
                    )
                ],
            )
        ],
    )
    monkeypatch.setattr(
        event_order_review_service,
        "review_summary",
        lambda _db, _event_id: summary,
    )

    content = event_order_review_service.export_review_csv(None, summary.event_id)

    assert content is not None
    rows = list(csv.reader(StringIO(content)))
    assert len(rows) == 2
    assert rows[1][3:8] == [
        "MODEL-B",
        "Selected product",
        "4",
        "25.00",
        "100.00",
    ]
