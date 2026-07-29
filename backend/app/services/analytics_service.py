from datetime import UTC, datetime
from decimal import Decimal
from math import ceil
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogProduct, CatalogVendor
from app.models.event_snapshot import EventSnapshot
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.receiving import (
    InvoiceLineMatch,
    InvoiceReconciliation,
    PurchaseBackorder,
    PurchaseReceipt,
    PurchaseReceiptLine,
    ReceiptVariance,
    ReconciliationException,
    VendorInvoice,
    VendorInvoiceLine,
)
from app.models.store import Store
from app.models.vendor_integration import (
    VendorPurchaseOrderAcknowledgement,
    VendorShipment,
)
from app.models.workflow import WorkflowInstance
from app.schemas.analytics import (
    ApprovalActorMetric,
    CurrencyMetric,
    ExecutiveBestSellerMetric,
    ExecutiveEntitySpendMetric,
    ExecutiveSpendDashboardResponse,
    InventoryPositionMetric,
    InventoryPositionResponse,
    InvoiceKPIs,
    OperationalDashboardResponse,
    PurchasingKPIs,
    ReceivingKPIs,
    ReconciliationKPIs,
    SpendAnalysisResponse,
    SpendDimension,
    SpendMetric,
    StatusMetric,
    VendorScorecard,
    VendorScorecardResponse,
    WorkflowAnalyticsResponse,
    WorkflowMetric,
)


def _count(db: Session, model: type) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def _status_metrics(db: Session, model: type) -> list[StatusMetric]:
    status_column = model.status
    rows = db.execute(
        select(status_column, func.count()).group_by(status_column).order_by(status_column)
    ).all()
    return [StatusMetric(status=status, count=count) for status, count in rows]


def _currency_metrics(db: Session, model: type) -> list[CurrencyMetric]:
    rows = db.execute(
        select(model.currency, func.sum(model.total))
        .group_by(model.currency)
        .order_by(model.currency)
    ).all()
    return [CurrencyMetric(currency=currency, amount=amount) for currency, amount in rows]


def operational_dashboard(db: Session) -> OperationalDashboardResponse:
    receipt_quantities = db.execute(
        select(
            func.coalesce(func.sum(PurchaseReceiptLine.accepted_quantity), 0),
            func.coalesce(func.sum(PurchaseReceiptLine.rejected_quantity), 0),
        ).join(PurchaseReceipt)
    ).one()
    outstanding_backorders = db.execute(
        select(
            func.count(),
            func.coalesce(func.sum(PurchaseBackorder.outstanding_quantity), 0),
        ).where(PurchaseBackorder.status.in_(("open", "partially_fulfilled")))
    ).one()
    open_variances = (
        db.scalar(
            select(func.count())
            .select_from(ReceiptVariance)
            .where(ReceiptVariance.status == "open")
        )
        or 0
    )
    line_match_exceptions = (
        db.scalar(
            select(func.count())
            .select_from(InvoiceLineMatch)
            .where(InvoiceLineMatch.status == "exception")
        )
        or 0
    )
    open_reconciliation_exceptions = (
        db.scalar(
            select(func.count())
            .select_from(ReconciliationException)
            .where(ReconciliationException.status == "open")
        )
        or 0
    )

    return OperationalDashboardResponse(
        purchasing=PurchasingKPIs(
            purchase_order_count=_count(db, PurchaseOrder),
            purchase_order_statuses=_status_metrics(db, PurchaseOrder),
            ordered_spend=_currency_metrics(db, PurchaseOrder),
        ),
        receiving=ReceivingKPIs(
            receipt_count=_count(db, PurchaseReceipt),
            accepted_quantity=Decimal(receipt_quantities[0]),
            rejected_quantity=Decimal(receipt_quantities[1]),
            open_variance_count=int(open_variances),
            open_backorder_count=int(outstanding_backorders[0]),
            outstanding_backorder_quantity=Decimal(outstanding_backorders[1]),
        ),
        invoices=InvoiceKPIs(
            invoice_count=_count(db, VendorInvoice),
            invoice_statuses=_status_metrics(db, VendorInvoice),
            invoiced_amount=_currency_metrics(db, VendorInvoice),
            line_match_exception_count=int(line_match_exceptions),
        ),
        reconciliation=ReconciliationKPIs(
            case_count=_count(db, InvoiceReconciliation),
            case_statuses=_status_metrics(db, InvoiceReconciliation),
            open_exception_count=int(open_reconciliation_exceptions),
        ),
    )


def executive_spend_dashboard(
    db: Session, as_of: datetime | None = None
) -> ExecutiveSpendDashboardResponse:
    current = as_of or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    else:
        current = current.astimezone(UTC)
    month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = current.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    amount = (
        PurchaseOrderLine.extended_amount
        + PurchaseOrderLine.freight_amount
        + PurchaseOrderLine.tax_amount
    )

    def entity_spend(period_start: datetime) -> list[ExecutiveEntitySpendMetric]:
        entity = func.coalesce(Store.entity_code, "Unassigned")
        rows = db.execute(
            select(
                entity,
                PurchaseOrder.currency,
                func.coalesce(func.sum(amount), 0),
            )
            .join(
                PurchaseOrderLine,
                PurchaseOrderLine.purchase_order_id == PurchaseOrder.id,
            )
            .outerjoin(Store, Store.store_number == PurchaseOrderLine.store_number)
            .where(
                PurchaseOrder.created_at >= period_start,
                PurchaseOrder.created_at <= current,
            )
            .group_by(entity, PurchaseOrder.currency)
            .order_by(
                PurchaseOrder.currency,
                func.sum(amount).desc(),
                entity,
            )
        ).all()
        return [
            ExecutiveEntitySpendMetric(
                entity_code=str(entity_code),
                currency=currency,
                amount=Decimal(total),
            )
            for entity_code, currency, total in rows
        ]

    seller_rows = db.execute(
        select(
            PurchaseOrderLine.product_code,
            PurchaseOrderLine.product_name,
            PurchaseOrder.currency,
            func.coalesce(func.sum(PurchaseOrderLine.quantity), 0),
            func.coalesce(func.sum(amount), 0),
        )
        .join(
            PurchaseOrderLine,
            PurchaseOrderLine.purchase_order_id == PurchaseOrder.id,
        )
        .where(
            PurchaseOrder.created_at >= month_start,
            PurchaseOrder.created_at <= current,
        )
        .group_by(
            PurchaseOrderLine.product_code,
            PurchaseOrderLine.product_name,
            PurchaseOrder.currency,
        )
        .order_by(
            PurchaseOrder.currency,
            func.sum(PurchaseOrderLine.quantity).desc(),
            func.sum(amount).desc(),
            PurchaseOrderLine.product_code,
        )
    ).all()
    sellers_by_currency: dict[str, list[tuple[object, ...]]] = {}
    for row in seller_rows:
        sellers_by_currency.setdefault(str(row[2]), []).append(row)
    top_sellers = [
        ExecutiveBestSellerMetric(
            rank=rank,
            product_code=str(row[0]),
            product_name=str(row[1]),
            currency=currency,
            quantity=Decimal(row[3]),
            amount=Decimal(row[4]),
        )
        for currency, currency_rows in sellers_by_currency.items()
        for rank, row in enumerate(currency_rows[:10], start=1)
    ]
    return ExecutiveSpendDashboardResponse(
        as_of=current,
        month_start=month_start,
        year_start=year_start,
        mtd_by_entity=entity_spend(month_start),
        ytd_by_entity=entity_spend(year_start),
        top_sellers_mtd=top_sellers,
    )


def spend_analysis(
    db: Session,
    group_by: SpendDimension,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    vendor_code: str | None = None,
    store_number: str | None = None,
    workflow_code: str | None = None,
) -> SpendAnalysisResponse:
    if group_by is SpendDimension.VENDOR:
        dimension = PurchaseOrder.vendor_code
    elif group_by is SpendDimension.STORE:
        dimension = PurchaseOrderLine.store_number
    elif group_by is SpendDimension.WORKFLOW:
        dimension = PurchaseOrder.workflow_code
    elif group_by is SpendDimension.DEPARTMENT:
        dimension = func.coalesce(CatalogProduct.department, "Unassigned")
    elif group_by is SpendDimension.PRODUCT_CODE:
        dimension = PurchaseOrderLine.product_code
    elif db.bind is not None and db.bind.dialect.name == "postgresql":
        dimension = func.to_char(PurchaseOrder.created_at, "YYYY-MM")
    else:
        dimension = func.strftime("%Y-%m", PurchaseOrder.created_at)

    amount = (
        PurchaseOrderLine.extended_amount
        + PurchaseOrderLine.freight_amount
        + PurchaseOrderLine.tax_amount
    )
    statement = (
        select(
            dimension.label("dimension_key"),
            PurchaseOrder.currency,
            func.count(func.distinct(PurchaseOrder.id)),
            func.count(PurchaseOrderLine.id),
            func.sum(PurchaseOrderLine.quantity),
            func.sum(amount),
        )
        .join(PurchaseOrderLine, PurchaseOrderLine.purchase_order_id == PurchaseOrder.id)
        .outerjoin(CatalogProduct, CatalogProduct.product_code == PurchaseOrderLine.product_code)
    )
    if date_from is not None:
        statement = statement.where(PurchaseOrder.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(PurchaseOrder.created_at < date_to)
    if vendor_code is not None:
        statement = statement.where(PurchaseOrder.vendor_code == vendor_code)
    if store_number is not None:
        statement = statement.where(PurchaseOrderLine.store_number == store_number)
    if workflow_code is not None:
        statement = statement.where(PurchaseOrder.workflow_code == workflow_code)
    statement = statement.group_by(dimension, PurchaseOrder.currency).order_by(
        func.sum(amount).desc(),
        dimension,
        PurchaseOrder.currency,
    )
    metrics = [
        SpendMetric(
            dimension_key=str(row[0]),
            currency=row[1],
            purchase_order_count=row[2],
            line_count=row[3],
            quantity=row[4],
            amount=row[5],
        )
        for row in db.execute(statement).all()
    ]
    return SpendAnalysisResponse(
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        metrics=metrics,
    )


def _rate(numerator: Decimal | int, denominator: Decimal | int) -> Decimal | None:
    if denominator == 0:
        return None
    return (Decimal(numerator) * 100 / Decimal(denominator)).quantize(Decimal("0.01"))


def vendor_scorecards(
    db: Session,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    minimum_orders: int = 1,
) -> VendorScorecardResponse:
    order_statement = select(PurchaseOrder)
    if date_from is not None:
        order_statement = order_statement.where(PurchaseOrder.created_at >= date_from)
    if date_to is not None:
        order_statement = order_statement.where(PurchaseOrder.created_at < date_to)
    orders = list(db.scalars(order_statement).all())
    by_vendor: dict[str, list[PurchaseOrder]] = {}
    for order in orders:
        by_vendor.setdefault(order.vendor_code, []).append(order)
    names = dict(db.execute(select(CatalogVendor.vendor_code, CatalogVendor.name)).all())
    results: list[VendorScorecard] = []
    for vendor_code, vendor_orders in sorted(by_vendor.items()):
        if len(vendor_orders) < minimum_orders:
            continue
        order_ids = [order.id for order in vendor_orders]
        acknowledgements = list(
            db.scalars(
                select(VendorPurchaseOrderAcknowledgement).where(
                    VendorPurchaseOrderAcknowledgement.purchase_order_id.in_(order_ids)
                )
            ).all()
        )
        shipments = list(
            db.scalars(
                select(VendorShipment).where(VendorShipment.purchase_order_id.in_(order_ids))
            ).all()
        )
        measured = [
            shipment
            for shipment in shipments
            if shipment.status == "delivered"
            and shipment.delivered_at is not None
            and shipment.estimated_delivery_at is not None
        ]
        on_time = sum(
            shipment.delivered_at <= shipment.estimated_delivery_at for shipment in measured
        )
        receipt_totals = db.execute(
            select(
                func.coalesce(func.sum(PurchaseReceiptLine.accepted_quantity), 0),
                func.coalesce(func.sum(PurchaseReceiptLine.rejected_quantity), 0),
            )
            .join(PurchaseReceipt)
            .where(PurchaseReceipt.purchase_order_id.in_(order_ids))
        ).one()
        invoices = list(
            db.scalars(
                select(VendorInvoice).where(VendorInvoice.purchase_order_id.in_(order_ids))
            ).all()
        )
        invoice_ids = [invoice.id for invoice in invoices]
        match_statuses = (
            list(
                db.scalars(
                    select(InvoiceLineMatch.status)
                    .join(VendorInvoiceLine)
                    .where(VendorInvoiceLine.invoice_id.in_(invoice_ids))
                ).all()
            )
            if invoice_ids
            else []
        )
        reconciliation_statuses = (
            list(
                db.scalars(
                    select(InvoiceReconciliation.status).where(
                        InvoiceReconciliation.invoice_id.in_(invoice_ids)
                    )
                ).all()
            )
            if invoice_ids
            else []
        )
        performance_statement = select(EventSnapshot.event_type).where(
            EventSnapshot.entity_id.in_(order_ids),
            EventSnapshot.event_type.in_(
                {
                    "vendor.fulfillment.delay_reported",
                    "vendor.fulfillment.backorder_reported",
                    "vendor.fulfillment.out_of_stock_reported",
                    "vendor.fulfillment.substitution_proposed",
                    "purchase_order.vendor_change_confirmed",
                }
            ),
        )
        if date_from is not None:
            performance_statement = performance_statement.where(
                EventSnapshot.created_at >= date_from
            )
        if date_to is not None:
            performance_statement = performance_statement.where(EventSnapshot.created_at < date_to)
        performance_events = list(db.scalars(performance_statement).all())
        fulfillment_event_count = sum(
            event_type.startswith("vendor.fulfillment.") for event_type in performance_events
        )
        spend_by_currency: dict[str, Decimal] = {}
        for order in vendor_orders:
            spend_by_currency[order.currency] = (
                spend_by_currency.get(order.currency, Decimal("0")) + order.total
            )
        accepted = Decimal(receipt_totals[0])
        rejected = Decimal(receipt_totals[1])
        results.append(
            VendorScorecard(
                vendor_code=vendor_code,
                vendor_name=names.get(vendor_code, vendor_code),
                purchase_order_count=len(vendor_orders),
                ordered_spend=[
                    CurrencyMetric(currency=currency, amount=amount)
                    for currency, amount in sorted(spend_by_currency.items())
                ],
                acknowledgement_count=len(acknowledgements),
                accepted_acknowledgement_count=sum(
                    item.acknowledgement_status in {"accepted", "accepted_with_changes"}
                    for item in acknowledgements
                ),
                rejected_acknowledgement_count=sum(
                    item.acknowledgement_status == "rejected" for item in acknowledgements
                ),
                acknowledgement_coverage_rate=_rate(len(acknowledgements), len(vendor_orders)),
                measured_delivery_count=len(measured),
                on_time_delivery_count=on_time,
                on_time_delivery_rate=_rate(on_time, len(measured)),
                accepted_quantity=accepted,
                rejected_quantity=rejected,
                receiving_acceptance_rate=_rate(accepted, accepted + rejected),
                invoice_line_count=len(match_statuses),
                matched_invoice_line_count=match_statuses.count("matched"),
                invoice_match_rate=_rate(match_statuses.count("matched"), len(match_statuses)),
                approved_reconciliation_count=reconciliation_statuses.count("approved"),
                rejected_reconciliation_count=reconciliation_statuses.count("rejected"),
                vendor_fulfillment_event_count=fulfillment_event_count,
                delay_event_count=performance_events.count("vendor.fulfillment.delay_reported"),
                backorder_event_count=performance_events.count(
                    "vendor.fulfillment.backorder_reported"
                ),
                out_of_stock_event_count=performance_events.count(
                    "vendor.fulfillment.out_of_stock_reported"
                ),
                substitution_event_count=performance_events.count(
                    "vendor.fulfillment.substitution_proposed"
                ),
                confirmed_po_change_count=performance_events.count(
                    "purchase_order.vendor_change_confirmed"
                ),
            )
        )
    return VendorScorecardResponse(
        date_from=date_from,
        date_to=date_to,
        scorecards=results,
    )


def workflow_analytics(
    db: Session,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    workflow_code: str | None = None,
) -> WorkflowAnalyticsResponse:
    statement = select(WorkflowInstance)
    if date_from is not None:
        statement = statement.where(WorkflowInstance.started_at >= date_from)
    if date_to is not None:
        statement = statement.where(WorkflowInstance.started_at < date_to)
    if workflow_code is not None:
        statement = statement.where(WorkflowInstance.workflow_code == workflow_code)
    instances = list(db.scalars(statement).all())
    by_workflow: dict[str, list[WorkflowInstance]] = {}
    for instance in instances:
        by_workflow.setdefault(instance.workflow_code, []).append(instance)

    snapshots = list(
        db.scalars(
            select(EventSnapshot).where(EventSnapshot.event_type == "workflow.advanced")
        ).all()
    )
    results: list[WorkflowMetric] = []
    for code, cohort in sorted(by_workflow.items()):
        entities = {(item.entity_type, item.entity_id) for item in cohort}
        transitions = [
            snapshot
            for snapshot in snapshots
            if (snapshot.entity_type, snapshot.entity_id) in entities
            and snapshot.payload.get("workflow_code") == code
        ]
        approvals = [
            item for item in transitions if str(item.payload.get("action", "")).endswith("approve")
        ]
        rejections = [item for item in transitions if item.payload.get("action") == "reject"]
        actors: dict[str, list[int]] = {}
        for item in approvals:
            actors.setdefault(item.actor, [0, 0])[0] += 1
        for item in rejections:
            actors.setdefault(item.actor, [0, 0])[1] += 1
        durations = sorted(
            (item.updated_at - item.started_at).total_seconds()
            for item in cohort
            if item.status == "complete"
        )
        state_counts: dict[str, int] = {}
        for item in cohort:
            state_counts[item.current_state] = state_counts.get(item.current_state, 0) + 1

        def duration(value: float) -> Decimal:
            return Decimal(str(value)).quantize(Decimal("0.01"))

        results.append(
            WorkflowMetric(
                workflow_code=code,
                instance_count=len(cohort),
                active_count=sum(item.status == "active" for item in cohort),
                completed_count=len(durations),
                current_states=[
                    StatusMetric(status=state, count=count)
                    for state, count in sorted(state_counts.items())
                ],
                transition_count=len(transitions),
                approval_count=len(approvals),
                rejection_count=len(rejections),
                average_completion_seconds=(
                    duration(sum(durations) / len(durations)) if durations else None
                ),
                median_completion_seconds=(duration(median(durations)) if durations else None),
                p90_completion_seconds=(
                    duration(durations[ceil(len(durations) * 0.9) - 1]) if durations else None
                ),
                approval_actors=[
                    ApprovalActorMetric(
                        actor=actor,
                        approval_count=counts[0],
                        rejection_count=counts[1],
                    )
                    for actor, counts in sorted(actors.items())
                ],
            )
        )
    return WorkflowAnalyticsResponse(
        date_from=date_from,
        date_to=date_to,
        workflows=results,
    )


def inventory_positions(
    db: Session,
    store_number: str | None = None,
    product_code: str | None = None,
) -> InventoryPositionResponse:
    statement = (
        select(
            PurchaseReceipt.store_number,
            PurchaseReceiptLine.product_code,
            PurchaseOrderLine.product_name,
            func.sum(PurchaseReceiptLine.accepted_quantity),
            func.sum(PurchaseReceiptLine.rejected_quantity),
        )
        .join(PurchaseReceiptLine, PurchaseReceiptLine.receipt_id == PurchaseReceipt.id)
        .join(PurchaseOrderLine, PurchaseOrderLine.id == PurchaseReceiptLine.purchase_order_line_id)
        .where(PurchaseReceipt.status.in_(("posted", "posted_with_exceptions")))
    )
    if store_number is not None:
        statement = statement.where(PurchaseReceipt.store_number == store_number)
    if product_code is not None:
        statement = statement.where(PurchaseReceiptLine.product_code == product_code)
    statement = statement.group_by(
        PurchaseReceipt.store_number,
        PurchaseReceiptLine.product_code,
        PurchaseOrderLine.product_name,
    ).order_by(PurchaseReceipt.store_number, PurchaseReceiptLine.product_code)
    backorder_rows = db.execute(
        select(
            PurchaseBackorder.store_number,
            PurchaseBackorder.product_code,
            func.sum(PurchaseBackorder.outstanding_quantity),
        )
        .where(PurchaseBackorder.status.in_(("open", "partially_fulfilled")))
        .group_by(PurchaseBackorder.store_number, PurchaseBackorder.product_code)
    ).all()
    backorders = {(row[0], row[1]): Decimal(row[2]) for row in backorder_rows}
    return InventoryPositionResponse(
        positions=[
            InventoryPositionMetric(
                store_number=row[0],
                product_code=row[1],
                product_name=row[2],
                accepted_quantity=row[3],
                rejected_quantity=row[4],
                outstanding_backorder_quantity=backorders.get((row[0], row[1]), Decimal("0")),
            )
            for row in db.execute(statement).all()
        ]
    )
