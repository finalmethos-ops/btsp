from app.services.identity_defaults import CORE_PERMISSION_DEFINITIONS, CORE_ROLE_DEFINITIONS


def test_system_role_includes_core_access() -> None:
    system_role = CORE_ROLE_DEFINITIONS["SYSTEM_ADMIN"]

    assert set(system_role["permissions"]) == set(CORE_PERMISSION_DEFINITIONS.keys())


def test_workflow_roles_have_distinct_codes() -> None:
    bpp_role = CORE_ROLE_DEFINITIONS["BPP_ADMIN"]
    independent_role = CORE_ROLE_DEFINITIONS["INDEPENDENT_ADMIN"]

    assert bpp_role["workflow_code"] == "BPP"
    assert independent_role["workflow_code"] == "INDEPENDENT"


def test_receiving_and_ap_roles_enforce_least_privilege() -> None:
    receiving_operator = set(CORE_ROLE_DEFINITIONS["RECEIVING_OPERATOR"]["permissions"])
    receiving_manager = set(CORE_ROLE_DEFINITIONS["RECEIVING_MANAGER"]["permissions"])
    ap_clerk = set(CORE_ROLE_DEFINITIONS["AP_CLERK"]["permissions"])
    ap_approver = set(CORE_ROLE_DEFINITIONS["AP_APPROVER"]["permissions"])

    assert receiving_operator == {"receiving.read", "receiving.manage"}
    assert "receiving.variances.manage" not in receiving_operator
    assert receiving_operator < receiving_manager
    assert "invoices.manage" in ap_clerk
    assert "reconciliation.manage" not in ap_clerk
    assert "reconciliation.manage" in ap_approver
    assert "invoices.manage" not in ap_approver
