from app.services.identity_defaults import CORE_PERMISSION_DEFINITIONS, CORE_ROLE_DEFINITIONS


def test_system_role_includes_core_access() -> None:
    system_role = CORE_ROLE_DEFINITIONS["SYSTEM_ADMIN"]

    assert set(system_role["permissions"]) == set(CORE_PERMISSION_DEFINITIONS.keys())


def test_workflow_roles_have_distinct_codes() -> None:
    bpp_role = CORE_ROLE_DEFINITIONS["BPP_ADMIN"]
    independent_role = CORE_ROLE_DEFINITIONS["INDEPENDENT_ADMIN"]

    assert bpp_role["workflow_code"] == "BPP"
    assert independent_role["workflow_code"] == "INDEPENDENT"
