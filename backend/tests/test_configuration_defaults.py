from app.services.configuration_defaults import DEFAULT_CONFIGURATION_ENTRIES


def test_default_configuration_includes_separate_workflows() -> None:
    workflow_keys = {
        (entry.scope_type, entry.scope_key, entry.key)
        for entry in DEFAULT_CONFIGURATION_ENTRIES
    }

    assert ("workflow", "BPP", "ordering.enabled") in workflow_keys
    assert ("workflow", "INDEPENDENT", "ordering.enabled") in workflow_keys


def test_default_configuration_enables_region_lock() -> None:
    matching_entries = [
        entry
        for entry in DEFAULT_CONFIGURATION_ENTRIES
        if entry.key == "multi_store.region_lock.enabled"
    ]

    assert matching_entries[0].value == {"enabled": True}
