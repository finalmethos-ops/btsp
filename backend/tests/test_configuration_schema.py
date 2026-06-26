from app.schemas.configuration_entry import ConfigEntryWrite


def test_config_entry_write_supports_json_value() -> None:
    entry = ConfigEntryWrite(
        scope_type="workflow",
        scope_key="BPP",
        key="ordering.enabled",
        value={"enabled": True},
        updated_by="tester",
    )

    assert entry.value["enabled"] is True
    assert entry.scope_key == "BPP"
