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
    parser.add_argument("--keep-data", action="store_true")
    args = parser.parse_args()
    if min(args.users, args.concurrency, args.quantity) < 1 or args.display_readers < 0:
        parser.error("users, concurrency, and quantity must be positive")
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
    slide = EventProductSlide(
        id=str(uuid4()),
        event_id=event.id,
        sub_event=sub_event,
        position=1,
        slide_type="product",
        model_number="STRESS-001",
        name="Concurrency Test Product",
        vendor_code="STRESS-VENDOR",
        category="Test",
        event_unit_cost=Decimal("99.95"),
        standard_cost=Decimal("129.95"),
        minimum_order_quantity=1,
        available_inventory=args.users * args.quantity + 100,
        max_event_units=args.users * args.quantity + 100,
        allow_waitlist=False,
        delivery_window_start=date.today() + timedelta(days=1),
        delivery_window_end=date.today() + timedelta(days=30),
        status="ready",
        created_by="stress-test@local.invalid",
    )
    tokens: list[str] = []
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
        for number in range(args.users):
            email = f"stress-user-{number:04d}@local.invalid"
            user = User(
                email=email,
                display_name=f"Stress User {number:04d}",
                password_hash="not-used-by-token-test",
                entity_code=f"STRESS-{number:04d}",
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
            tokens.append(create_access_token(email, login_context="event"))
        db.commit()
        event_id = event.id
        sub_event_id = sub_event.id
        slide_id = slide.id

    projector_token, _expires_at = create_projector_token(sub_event_id)

    async def execute() -> tuple[list[tuple[int, float, str]], list[tuple[int, float]]]:
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

            async def order(token: str) -> None:
                await start_gate.wait()
                async with semaphore:
                    started = time.perf_counter()
                    response = await client.put(
                        f"/api/v1/event-ordering/{sub_event_id}/order",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"quantity": args.quantity, "variant_quantities": {}},
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

            readers = [
                asyncio.create_task(display_reader())
                for _ in range(args.display_readers)
            ]
            writers = [asyncio.create_task(order(token)) for token in tokens]
            started = time.perf_counter()
            start_gate.set()
            await asyncio.gather(*writers)
            elapsed = time.perf_counter() - started
            writers_done.set()
            await asyncio.gather(*readers)
            await event_realtime_hub.close()
        execute.elapsed = elapsed  # type: ignore[attr-defined]
        return order_results, display_results

    try:
        order_results, display_results = asyncio.run(execute())
        elapsed = float(execute.elapsed)  # type: ignore[attr-defined]
        order_latencies = [
            latency for status, latency, _detail in order_results if status == 200
        ]
        display_latencies = [
            latency for status, latency in display_results if status == 200
        ]
        errors = [
            {"status": status, "detail": detail}
            for status, _latency, detail in order_results
            if status != 200
        ]
        with Session(engine) as db:
            order_count, distinct_entities, total_quantity = db.execute(
                select(
                    func.count(EventEntityOrder.id),
                    func.count(func.distinct(EventEntityOrder.entity_code)),
                    func.coalesce(func.sum(EventEntityOrder.quantity), 0),
                ).where(
                    EventEntityOrder.event_id == event_id,
                    EventEntityOrder.sub_event_id == sub_event_id,
                    EventEntityOrder.slide_id == slide_id,
                )
            ).one()
            revision_count = (
                db.scalar(select(func.count(EventEntityOrderRevision.id))) or 0
            )
        expected_quantity = args.users * args.quantity
        reconciled = (
            len(order_results) == args.users
            and not errors
            and order_count == args.users
            and distinct_entities == args.users
            and total_quantity == expected_quantity
            and revision_count == args.users
            and all(status == 200 for status, _latency in display_results)
        )
        summary = {
            "database": "isolated PostgreSQL",
            "authenticated_users": args.users,
            "concurrency": args.concurrency,
            "display_readers": args.display_readers,
            "elapsed_seconds": round(elapsed, 3),
            "orders_per_second": round(args.users / elapsed, 2),
            "order_latency_ms": {
                "average": round(mean(order_latencies), 2) if order_latencies else 0,
                "p50": round(_percentile(order_latencies, 0.50), 2),
                "p95": round(_percentile(order_latencies, 0.95), 2),
                "p99": round(_percentile(order_latencies, 0.99), 2),
                "maximum": round(max(order_latencies), 2) if order_latencies else 0,
            },
            "display_reads": len(display_results),
            "display_latency_p95_ms": round(_percentile(display_latencies, 0.95), 2),
            "http_errors": errors[:5],
            "persisted_orders": int(order_count),
            "distinct_entities": int(distinct_entities),
            "persisted_quantity": int(total_quantity),
            "order_revisions": int(revision_count),
            "reconciled_without_loss": reconciled,
        }
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if reconciled else 1
    finally:
        if not args.keep_data:
            Base.metadata.drop_all(engine)
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
