"""Import the complete SQLAlchemy model graph for standalone processes."""

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
