from hashlib import sha256
from typing import Any

from sqlalchemy.orm import Session

from app.models.event_snapshot import EventSnapshot
from app.models.identity import User


def _opaque_value(value: str) -> str:
    return sha256(value.strip().casefold().encode("utf-8")).hexdigest()[:32]


def record_login_event(
    db: Session,
    *,
    submitted_email: str,
    login_context: str,
    outcome: str,
    request_id: str,
    client_address: str,
    user: User | None = None,
    reason: str | None = None,
) -> None:
    """Stage a privacy-conscious login event in the caller's transaction."""
    payload: dict[str, Any] = {
        "client_address_hash": _opaque_value(client_address),
        "login_context": login_context,
        "outcome": outcome,
        "request_id": request_id,
    }
    if reason:
        payload["reason"] = reason
    db.add(
        EventSnapshot(
            event_type="user.login",
            entity_type="user",
            entity_id=str(user.id)
            if user is not None
            else f"attempt:{_opaque_value(submitted_email)}",
            actor=user.email if user is not None else "anonymous",
            payload=payload,
        )
    )


def record_administrative_action(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        EventSnapshot(
            event_type="administrative.action",
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            payload={"action": action, **(details or {})},
        )
    )


def record_permission_change(
    db: Session,
    *,
    actor: str,
    entity_type: str,
    entity_id: str,
    action: str,
    previous_roles: list[str] | None = None,
    new_roles: list[str] | None = None,
    previous_permissions: list[str] | None = None,
    new_permissions: list[str] | None = None,
    previous_vendor_codes: list[str] | None = None,
    new_vendor_codes: list[str] | None = None,
) -> None:
    db.add(
        EventSnapshot(
            event_type="permission.changed",
            entity_type=entity_type,
            entity_id=entity_id,
            actor=actor,
            payload={
                "action": action,
                "new_permissions": sorted(new_permissions or []),
                "new_roles": sorted(new_roles or []),
                "new_vendor_codes": sorted(new_vendor_codes or []),
                "previous_permissions": sorted(previous_permissions or []),
                "previous_roles": sorted(previous_roles or []),
                "previous_vendor_codes": sorted(previous_vendor_codes or []),
            },
        )
    )
