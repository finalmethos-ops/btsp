from app.schemas.configuration_entry import ConfigEntryWrite

DEFAULT_CONFIGURATION_ENTRIES: list[ConfigEntryWrite] = [
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP",
        key="ordering.enabled",
        value={"enabled": True},
        description="Enable BPP ordering workflow.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="workflow",
        scope_key="INDEPENDENT",
        key="ordering.enabled",
        value={"enabled": True},
        description="Enable Independent ordering workflow.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="global",
        scope_key="default",
        key="multi_store.region_lock.enabled",
        value={"enabled": True},
        description="Require multi-store orders to stay within allowed region scope.",
        updated_by="system",
    ),
    ConfigEntryWrite(
        scope_type="global",
        scope_key="default",
        key="event_snapshots.enabled",
        value={"enabled": True},
        description="Enable append-only snapshot recording.",
        updated_by="system",
    ),
]
