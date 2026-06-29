from app.services.bpp_purchasing import BPP_PERMISSION_DEFINITIONS
from app.services.independent_purchasing import INDEPENDENT_PERMISSION_DEFINITIONS
from app.services.notification_defaults import GLOBAL_NOTIFICATION_PERMISSION_DEFINITIONS

CORE_PERMISSION_DEFINITIONS: dict[str, str] = {
    "system.admin": "Full system administration access.",
    "system.health.read": "Read protected system health and operational diagnostics.",
    "roles.manage": "Manage custom roles and their permission assignments.",
    "configuration.manage": "Manage BTSP configuration entries.",
    "stores.manage": "Manage store authority records.",
    "snapshots.read": "Read snapshot audit records.",
    "audit.export": "Export filtered immutable audit records.",
    "workflows.read": "Read available workflow routing.",
    "workflows.manage": "Inspect and activate versioned workflow definitions.",
    "orders.bpp.manage": "Manage BPP ordering workflow.",
    "orders.independent.manage": "Manage Independent ordering workflow.",
    "vendor.integrations.manage": "Manage vendor integration endpoints.",
    "vendor.integrations.read": "Read vendor integration endpoints and inbound events.",
    "vendor.integrations.ingest": "Record authenticated inbound vendor events.",
    "vendor.acknowledgements.process": "Process inbound vendor PO acknowledgements.",
    "vendor.logistics.process": "Process inbound vendor shipment updates and ASNs.",
    "vendor.connectors.operate": "Manage connector schedules, retries, and dead letters.",
    "vendor.connectors.work": "Claim and complete connector execution jobs.",
    "receiving.read": "Read purchase receipts within assigned store authority.",
    "receiving.manage": "Post purchase receipts within assigned store authority.",
    "receiving.variances.manage": "Resolve or waive receipt variances within store authority.",
    "receiving.backorders.manage": "Create and resolve backorders within store authority.",
    "invoices.read": "Read vendor invoices and deterministic line matches.",
    "invoices.manage": "Ingest vendor invoices for purchase-order matching.",
    "reconciliation.read": "Read invoice reconciliation cases and exceptions.",
    "reconciliation.manage": "Resolve reconciliation exceptions and record final decisions.",
    "analytics.read": "Read operational purchasing and reconciliation analytics.",
    "analytics.reports.manage": "Manage and generate scheduled analytics reports.",
    **BPP_PERMISSION_DEFINITIONS,
    **GLOBAL_NOTIFICATION_PERMISSION_DEFINITIONS,
    **INDEPENDENT_PERMISSION_DEFINITIONS,
}

CORE_ROLE_DEFINITIONS: dict[str, dict[str, object]] = {
    "SYSTEM_ADMIN": {
        "name": "System Administrator",
        "workflow_code": None,
        "permissions": list(CORE_PERMISSION_DEFINITIONS.keys()),
    },
    "BPP_ADMIN": {
        "name": "BPP Administrator",
        "workflow_code": "BPP",
        "permissions": [
            "workflows.read",
            "orders.bpp.manage",
            "snapshots.read",
            "notifications.read",
            "notifications.send",
            *BPP_PERMISSION_DEFINITIONS.keys(),
        ],
    },
    "INDEPENDENT_ADMIN": {
        "name": "Independent Administrator",
        "workflow_code": "INDEPENDENT",
        "permissions": [
            "workflows.read",
            "orders.independent.manage",
            "snapshots.read",
            "notifications.read",
            "notifications.send",
            *INDEPENDENT_PERMISSION_DEFINITIONS.keys(),
        ],
    },
    "RECEIVING_OPERATOR": {
        "name": "Receiving Operator",
        "workflow_code": None,
        "permissions": ["receiving.read", "receiving.manage"],
    },
    "RECEIVING_MANAGER": {
        "name": "Receiving Manager",
        "workflow_code": None,
        "permissions": [
            "receiving.read",
            "receiving.manage",
            "receiving.variances.manage",
            "receiving.backorders.manage",
        ],
    },
    "AP_CLERK": {
        "name": "Accounts Payable Clerk",
        "workflow_code": None,
        "permissions": ["invoices.read", "invoices.manage", "reconciliation.read"],
    },
    "AP_APPROVER": {
        "name": "Accounts Payable Approver",
        "workflow_code": None,
        "permissions": ["invoices.read", "reconciliation.read", "reconciliation.manage"],
    },
    "ANALYTICS_VIEWER": {
        "name": "Analytics Viewer",
        "workflow_code": None,
        "permissions": ["analytics.read"],
    },
    "ANALYTICS_MANAGER": {
        "name": "Analytics Manager",
        "workflow_code": None,
        "permissions": ["analytics.read", "analytics.reports.manage"],
    },
}
