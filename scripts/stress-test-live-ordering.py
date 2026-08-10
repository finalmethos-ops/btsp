#!/usr/bin/env python3
"""Exercise authenticated live ordering against an isolated PostgreSQL database."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import mean
from urllib.parse import urlparse
from uuid import uuid4

import httpx2 as httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

VARIANT_DEFINITIONS = (
    ("STRESS-A", "Concurrent Product A", Decimal("99.95"), 1),
    ("STRESS-B", "Concurrent Product B", Decimal("149.50"), 2),
    ("STRESS-C", "Concurrent Product C", Decimal("12.25"), 3),
)


def _variant_quantities(user_number: int, quantity: int) -> dict[str, int]:
    """Create intentionally different per-product quantities for one entity."""
    values = {"STRESS-A": quantity}
    if user_number % 3 != 1:
        values["STRESS-B"] = quantity * 2
    if user_number % 4 == 0:
        values["STRESS-C"] = quantity * 3
    return values


def _variant_total(quantities: dict[str, int]) -> Decimal:
    prices = {model: price for model, _name, price, _minimum in VARIANT_DEFINITIONS}
    return sum(
        (prices[model] * item_quantity for model, item_quantity in quantities.items()),
        start=Decimal("0.00"),
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Send concurrent authenticated orders and reconcile every committed "
            "order and revision afterward. DATABASE_URL must name an isolated "
            "PostgreSQL database containing 'stress'."
        )
    )
    parser.add_argument("--users", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=40)
    parser.add_argument("--display-readers", type=int, default=8)
    parser.add_argument("--quantity", type=int, default=1)
    parser.add_argument("--max-order-p95-ms", type=float, default=0)
    parser.add_argument("--max-display-p95-ms", type=float, default=0)
    parser.add_argument("--min-orders-per-second", type=float, default=0)
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()
    if min(args.users, args.concurrency, args.quantity) < 1 or args.display_readers < 0:
        parser.error("users, concurrency, and quantity must be positive")
    if (
        min(
            args.max_order_p95_ms,
            args.max_display_p95_ms,
            args.min_orders_per_second,
        )
        < 0
    ):
        parser.error("performance thresholds cannot be negative")
    return args


def _require_isolated_database() -> str:
    database_url = os.environ.get("DATABASE_URL", "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.scheme not in {"postgres", "postgresql", "postgresql+psycopg"}:
        raise SystemExit("DATABASE_URL must use PostgreSQL for the concurrency test")
    if "stress" not in database_name:
        raise SystemExit(
            "Refusing to reset a database whose name does not contain the word 'stress'"
        )
    return database_url


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(round((len(ordered) - 1) * percentile), len(ordered) - 1)
    return ordered[index]


def main() -> int:
    args = _arguments()
    _require_isolated_database()
    repository = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repository / "backend"))

    # Import the complete model graph only after the database safety check.
    from app.auth.security import create_access_token, create_projector_token
    from app.db.session import Base, engine
    from app.main import app
    from app.models import (  # noqa: F401
        analytics,
        attachment,
        catalog,
        communication,
        configuration,
        event_management,
        event_snapshot,
        identity,
        inventory,
        invoice_intake,
        notification,
        purchase_order,
        purchasing,
        receiving,
        store,
        vendor_integration,
        workflow,
    )
    from app.models.catalog import CatalogVendor
    from app.models.event_management import (
        EventEntityOrder,
        EventEntityOrderRevision,
        EventMembership,
        EventPresentationState,
        EventProductSlide,
        ManagedEvent,
        ManagedSubEvent,
    )
    from app.models.identity import User
    from app.services.event_realtime_service import event_realtime_hub

    logging.getLogger("btsp.access").setLevel(logging.WARNING)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    event = ManagedEvent(
        id=str(uuid4()),
        slug="isolated-live-order-stress",
        name="Isolated Live Order Stress Test",
        status="published",
        starts_at=now - timedelta(hours=1),
        ends_at=now + timedelta(hours=4),
        venue_name="Isolated Test Venue",
        address_line1="1 Test Way",
        city="Orlando",
        state_code="FL",
        postal_code="32801",
        created_by="stress-test@local.invalid",
    )
    sub_event = ManagedSubEvent(
        id=str(uuid4()),
        event=event,
        name="Concurrent Ordering Test",
        starts_at=now - timedelta(minutes=30),
        ends_at=now + timedelta(hours=2),
        location="Load Lab",
        status="published",
        module_codes=["live-display", "ordering", "product-slides"],
    )
    workloads = [
        {
            "email": f"stress-user-{number:04d}@local.invalid",
            "entity_code": f"STRESS-{number:04d}",
            "variant_quantities": _variant_quantities(number, args.quantity),
        }
        for number in range(args.users)
    ]
    expected_variant_totals = {
        model: sum(dict(workload["variant_quantities"]).get(model, 0) for workload in workloads)
        for model, _name, _price, _minimum in VARIANT_DEFINITIONS
    }
    product_variants = [
        {
            "model_number": model,
            "name": name,
            "event_unit_cost": str(price),
            "standard_cost": str(price + Decimal("30.00")),
            "minimum_order_quantity": minimum,
            "available_inventory": expected_variant_totals[model],
            "max_event_units": expected_variant_totals[model],
        }
        for model, name, price, minimum in VARIANT_DEFINITIONS
    ]
    slide = EventProductSlide(
        id=str(uuid4()),
        event_id=event.id,
        sub_event=sub_event,
        position=1,
        slide_type="product",
        model_number="STRESS-COMBINED",
        name="Concurrent Combined Product Offer",
        vendor_code="STRESS-VENDOR",
        category="Test",
        event_unit_cost=Decimal("99.95"),
        standard_cost=Decimal("129.95"),
        minimum_order_quantity=1,
        available_inventory=None,
        max_event_units=None,
        allow_waitlist=False,
        delivery_window_start=date.today() + timedelta(days=1),
        delivery_window_end=date.today() + timedelta(days=30),
        product_variants=product_variants,
        status="ready",
        created_by="stress-test@local.invalid",
    )
    tokens: list[tuple[str, dict[str, object]]] = []
    with Session(engine) as db:
        db.add(
            CatalogVendor(
                vendor_code="STRESS-VENDOR",
                name="Isolated Stress Vendor",
                source_file="stress-test",
                is_active=True,
            )
        )
        db.add(event)
        db.flush()
        db.add(slide)
        db.flush()
        db.add(
            EventPresentationState(
                sub_event_id=sub_event.id,
                event_id=event.id,
                current_slide_id=slide.id,
                status="live",
                ordering_status="open",
                ordering_opened_at=now,
                updated_by="stress-test@local.invalid",
            )
        )
        for number, workload in enumerate(workloads):
            email = str(workload["email"])
            user = User(
                email=email,
                display_name=f"Stress User {number:04d}",
                password_hash="not-used-by-token-test",
                entity_code=str(workload["entity_code"]),
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(
                EventMembership(
                    event_id=event.id,
                    user_id=user.id,
                    membership_type="franchise_representative",
                    entity_code=user.entity_code,
                    is_active=True,
                )
            )
            tokens.append((create_access_token(email, login_context="event"), workload))
        db.commit()
        event_id = event.id
        sub_event_id = sub_event.id
        slide_id = slide.id

    projector_token, _expires_at = create_projector_token(sub_event_id)

    async def execute() -> (
        tuple[list[tuple[int, float, str]], list[tuple[int, float]], dict[str, object], int]
    ):
        transport = httpx.ASGITransport(app=app)
        semaphore = asyncio.Semaphore(args.concurrency)
        start_gate = asyncio.Event()
        writers_done = asyncio.Event()
        order_results: list[tuple[int, float, str]] = []
        display_results: list[tuple[int, float]] = []

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://isolated-stress.local",
            timeout=30,
        ) as client:

            async def order(token: str, workload: dict[str, object]) -> None:
                await start_gate.wait()
                async with semaphore:
                    started = time.perf_counter()
                    response = await client.put(
                        f"/api/v1/event-ordering/{sub_event_id}/order",
                        headers={"Authorization": f"Bearer {token}"},
                        json={
                            "quantity": sum(dict(workload["variant_quantities"]).values()),
                            "variant_quantities": workload["variant_quantities"],
                        },
                    )
                    order_results.append(
                        (
                            response.status_code,
                            (time.perf_counter() - started) * 1000,
                            response.text[:300] if response.status_code >= 400 else "",
                        )
                    )

            async def display_reader() -> None:
                await start_gate.wait()
                while not writers_done.is_set():
                    started = time.perf_counter()
                    response = await client.get(
                        f"/api/v1/public-event-presentations/{sub_event_id}",
                        headers={"X-BTSP-Projector-Token": projector_token},
                    )
                    display_results.append(
                        (response.status_code, (time.perf_counter() - started) * 1000)
                    )
                    await asyncio.sleep(0.05)

            readers = [asyncio.create_task(display_reader()) for _ in range(args.display_readers)]
            writers = [asyncio.create_task(order(token, workload)) for token, workload in tokens]
            started = time.perf_counter()
            start_gate.set()
            await asyncio.gather(*writers)
            elapsed = time.perf_counter() - started
            writers_done.set()
            await asyncio.gather(*readers)
            final_display = await client.get(
                f"/api/v1/public-event-presentations/{sub_event_id}",
                headers={"X-BTSP-Projector-Token": projector_token},
            )
            # Each product is now exactly at capacity. An update that adds one
            # more unit must fail without overwriting the committed order.
            probe_token, probe_workload = tokens[0]
            probe_quantities = dict(probe_workload["variant_quantities"])
            probe_quantities["STRESS-A"] += 1
            capacity_probe = await client.put(
                f"/api/v1/event-ordering/{sub_event_id}/order",
                headers={"Authorization": f"Bearer {probe_token}"},
                json={
                    "quantity": sum(probe_quantities.values()),
                    "variant_quantities": probe_quantities,
                },
            )
            await event_realtime_hub.close()
        execute.elapsed = elapsed  # type: ignore[attr-defined]
        return (
            order_results,
            display_results,
            final_display.json() if final_display.status_code == 200 else {},
            capacity_probe.status_code,
        )

    try:
        order_results, display_results, final_display, capacity_probe_status = asyncio.run(
            execute()
        )
        elapsed = float(execute.elapsed)  # type: ignore[attr-defined]
        order_latencies = [latency for status, latency, _detail in order_results if status == 200]
        display_latencies = [latency for status, latency in display_results if status == 200]
        errors = [
            {"status": status, "detail": detail}
            for status, _latency, detail in order_results
            if status != 200
        ]
        with Session(engine) as db:
            order_count, distinct_entities, total_quantity, total_cost = db.execute(
                select(
                    func.count(EventEntityOrder.id),
                    func.count(func.distinct(EventEntityOrder.entity_code)),
                    func.coalesce(func.sum(EventEntityOrder.quantity), 0),
                    func.coalesce(func.sum(EventEntityOrder.total_cost), 0),
                ).where(
                    EventEntityOrder.event_id == event_id,
                    EventEntityOrder.sub_event_id == sub_event_id,
                    EventEntityOrder.slide_id == slide_id,
                )
            ).one()
            revision_count = db.scalar(select(func.count(EventEntityOrderRevision.id))) or 0
            saved_orders = list(
                db.scalars(
                    select(EventEntityOrder).where(
                        EventEntityOrder.event_id == event_id,
                        EventEntityOrder.sub_event_id == sub_event_id,
                        EventEntityOrder.slide_id == slide_id,
                    )
                ).all()
            )
            saved_revisions = list(db.scalars(select(EventEntityOrderRevision)).all())
        expected_by_entity = {
            str(workload["entity_code"]): dict(workload["variant_quantities"])
            for workload in workloads
        }
        expected_quantity = sum(
            sum(quantities.values()) for quantities in expected_by_entity.values()
        )
        expected_total_cost = sum(
            (_variant_total(quantities) for quantities in expected_by_entity.values()),
            start=Decimal("0.00"),
        )
        persisted_orders_match = all(
            order.variant_quantities == expected_by_entity.get(order.entity_code)
            and order.quantity == sum(order.variant_quantities.values())
            and order.total_cost == _variant_total(order.variant_quantities)
            and order.status == "confirmed"
            for order in saved_orders
        )
        order_by_id = {order.id: order for order in saved_orders}
        revisions_match = all(
            revision.order_id in order_by_id
            and revision.variant_quantities == order_by_id[revision.order_id].variant_quantities
            and revision.quantity == order_by_id[revision.order_id].quantity
            for revision in saved_revisions
        )
        displayed_variant_totals = final_display.get("variant_units_ordered", {})
        reconciled = (
            len(order_results) == args.users
            and not errors
            and order_count == args.users
            and distinct_entities == args.users
            and total_quantity == expected_quantity
            and total_cost == expected_total_cost
            and revision_count == args.users
            and persisted_orders_match
            and revisions_match
            and displayed_variant_totals == expected_variant_totals
            and int(final_display.get("total_units_ordered", -1)) == expected_quantity
            and Decimal(str(final_display.get("total_combined_spend", "-1"))) == expected_total_cost
            and capacity_probe_status in {400, 409, 422}
            and all(status == 200 for status, _latency in display_results)
        )
        order_p95 = _percentile(order_latencies, 0.95)
        display_p95 = _percentile(display_latencies, 0.95)
        orders_per_second = args.users / elapsed
        performance_regressions = []
        if args.max_order_p95_ms and order_p95 > args.max_order_p95_ms:
            performance_regressions.append("order p95 exceeded its limit")
        if args.max_display_p95_ms and display_p95 > args.max_display_p95_ms:
            performance_regressions.append("display p95 exceeded its limit")
        if args.min_orders_per_second and orders_per_second < args.min_orders_per_second:
            performance_regressions.append("order throughput fell below its limit")
        summary = {
            "database": "isolated PostgreSQL",
            "authenticated_users": args.users,
            "concurrency": args.concurrency,
            "display_readers": args.display_readers,
            "elapsed_seconds": round(elapsed, 3),
            "orders_per_second": round(orders_per_second, 2),
            "order_latency_ms": {
                "average": round(mean(order_latencies), 2) if order_latencies else 0,
                "p50": round(_percentile(order_latencies, 0.50), 2),
                "p95": round(order_p95, 2),
                "p99": round(_percentile(order_latencies, 0.99), 2),
                "maximum": round(max(order_latencies), 2) if order_latencies else 0,
            },
            "display_reads": len(display_results),
            "display_latency_p95_ms": round(display_p95, 2),
            "performance_thresholds": {
                "max_order_p95_ms": args.max_order_p95_ms or None,
                "max_display_p95_ms": args.max_display_p95_ms or None,
                "min_orders_per_second": args.min_orders_per_second or None,
            },
            "performance_regressions": performance_regressions,
            "http_errors": errors[:5],
            "persisted_orders": int(order_count),
            "distinct_entities": int(distinct_entities),
            "persisted_quantity": int(total_quantity),
            "persisted_total_cost": str(total_cost),
            "expected_variant_quantities": expected_variant_totals,
            "displayed_variant_quantities": displayed_variant_totals,
            "order_revisions": int(revision_count),
            "capacity_probe_status": capacity_probe_status,
            "capacity_probe_preserved_orders": persisted_orders_match,
            "reconciled_without_loss": reconciled,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if reconciled and not performance_regressions else 1
    finally:
        if not args.keep_data:
            Base.metadata.drop_all(engine)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
