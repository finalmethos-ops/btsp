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

    shared_communications = {"communications.read", "communications.send"}
    assert receiving_operator == {
        "receiving.read",
        "receiving.manage",
        *shared_communications,
    }
    assert "receiving.variances.manage" not in receiving_operator
    assert receiving_operator < receiving_manager
    assert "invoices.manage" in ap_clerk
    assert "reconciliation.manage" not in ap_clerk
    assert "reconciliation.manage" in ap_approver
    assert "invoices.manage" not in ap_approver


def test_purchasing_can_review_handoff_without_managing_invoices() -> None:
    permissions = set(CORE_ROLE_DEFINITIONS["PURCHASING"]["permissions"])

    assert "purchase_orders.handoff" in permissions
    assert {
        "vendor_hall.read",
        "vendor_hall.manage",
        "vendor_hall.staff.checkin",
        "vendor_hall.export",
        "vendor_hall.map.manage",
    } <= permissions
    assert "invoices.read" not in permissions
    assert "invoices.manage" not in permissions
    assert "reconciliation.read" in permissions
    assert "reconciliation.manage" not in permissions


def test_vendor_hall_permissions_are_assigned_to_event_roles() -> None:
    vendor_permissions = set(CORE_ROLE_DEFINITIONS["VENDOR"]["permissions"])
    franchise_permissions = set(CORE_ROLE_DEFINITIONS["FRANCHISE_OPERATOR"]["permissions"])
    admin_permissions = set(CORE_ROLE_DEFINITIONS["ADMIN"]["permissions"])

    vendor_hall_permissions = {
        "vendor_hall.read",
        "vendor_hall.manage",
        "vendor_hall.vendor.manage",
        "vendor_hall.staff.checkin",
        "vendor_hall.export",
        "vendor_hall.map.manage",
    }

    assert vendor_hall_permissions <= set(CORE_PERMISSION_DEFINITIONS)
    assert {"vendor_hall.read", "vendor_hall.vendor.manage"} <= vendor_permissions
    assert "vendor_hall.manage" not in vendor_permissions
    assert "vendor_hall.read" in franchise_permissions
    assert vendor_hall_permissions <= admin_permissions


def test_event_staff_role_is_limited_to_onsite_event_work() -> None:
    permissions = set(CORE_ROLE_DEFINITIONS["EVENT_STAFF"]["permissions"])

    assert {
        "events.read",
        "vendor_hall.staff.checkin",
        "store_loadout.store.checkin",
    } <= permissions
    assert "events.manage" not in permissions
    assert "vendor_hall.manage" not in permissions
    assert "store_loadout.manage" not in permissions
    assert "system.admin" not in permissions


def test_reconciliation_has_read_only_store_directory_access() -> None:
    permissions = set(CORE_ROLE_DEFINITIONS["RECONCILIATION"]["permissions"])

    assert "stores.read" in permissions
    assert "stores.manage" not in permissions
