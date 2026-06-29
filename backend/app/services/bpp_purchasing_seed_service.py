from sqlalchemy.orm import Session

from app.core.workflows import WORKFLOW_REGISTRY, WorkflowCode
from app.models.identity import Permission
from app.schemas.bpp_purchasing import BppPurchasingSeedResponse
from app.services.bpp_purchasing import (
    BPP_PERMISSION_DEFINITIONS,
    BPP_PURCHASING_CONFIGURATION_DEFAULTS,
    BPP_PURCHASING_DEFINITION,
)
from app.services.configuration_service import upsert_config_entry
from app.services.permission_seed_service import seed_permissions_for_roles
from app.services.workflow_engine import upsert_workflow_definition


def seed_bpp_permissions(db: Session) -> dict[str, Permission]:
    permission_codes = set(BPP_PERMISSION_DEFINITIONS)
    return seed_permissions_for_roles(
        db,
        BPP_PERMISSION_DEFINITIONS,
        {
            "SYSTEM_ADMIN": permission_codes,
            "BPP_ADMIN": permission_codes,
        },
    )


def seed_bpp_purchasing(db: Session, actor: str) -> BppPurchasingSeedResponse:
    registration = WORKFLOW_REGISTRY.require(WorkflowCode.BPP_PURCHASING)
    permissions = seed_bpp_permissions(db)
    definition = upsert_workflow_definition(db, BPP_PURCHASING_DEFINITION.model_copy(deep=True))

    for default in BPP_PURCHASING_CONFIGURATION_DEFAULTS:
        payload = default.model_copy(deep=True, update={"updated_by": actor})
        upsert_config_entry(db, payload)

    return BppPurchasingSeedResponse(
        workflow_code=definition.code,
        workflow_version=definition.version,
        permissions_seeded=len(permissions),
        configuration_entries_seeded=len(BPP_PURCHASING_CONFIGURATION_DEFAULTS),
        registry_entry_verified=registration.code == definition.code,
    )
