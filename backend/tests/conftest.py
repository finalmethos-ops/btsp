"""Register the complete SQLAlchemy model graph for isolated test modules."""

# Some domain tests construct ``Base.metadata`` directly. Import every model
# module here so foreign-key targets are registered regardless of test order.
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
