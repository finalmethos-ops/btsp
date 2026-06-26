CORE_PERMISSION_DEFINITIONS: dict[str, str] = {
    "system.admin": "Full system administration access.",
    "configuration.manage": "Manage BTSP configuration entries.",
    "stores.manage": "Manage store authority records.",
    "snapshots.read": "Read snapshot audit records.",
    "workflows.read": "Read available workflow routing.",
    "orders.bpp.manage": "Manage BPP ordering workflow.",
    "orders.independent.manage": "Manage Independent ordering workflow.",
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
        "permissions": ["workflows.read", "orders.bpp.manage", "snapshots.read"],
    },
    "INDEPENDENT_ADMIN": {
        "name": "Independent Administrator",
        "workflow_code": "INDEPENDENT",
        "permissions": ["workflows.read", "orders.independent.manage", "snapshots.read"],
    },
}
