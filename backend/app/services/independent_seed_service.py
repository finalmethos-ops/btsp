from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.workflows import WORKFLOW_REGISTRY, WorkflowCode
from app.models.notification import NotificationTemplate
from app.schemas.independent_purchasing import IndependentPurchasingSeedResponse
from app.schemas.notification import NotificationTemplateUpdate
from app.services.configuration_service import upsert_config_entry
from app.services.independent_defaults import (
    INDEPENDENT_APPROVAL_DEFAULTS,
    INDEPENDENT_NOTIFICATION_TEMPLATES,
)
from app.services.independent_purchasing import (
    INDEPENDENT_CONFIGURATION_DEFAULTS,
    INDEPENDENT_PERMISSION_DEFINITIONS,
    INDEPENDENT_PURCHASING_DEFINITION,
)
from app.services.notification_defaults import GLOBAL_NOTIFICATION_PERMISSION_DEFINITIONS
from app.services.notification_service import (
    create_notification_template,
    update_notification_template,
)
from app.services.permission_seed_service import seed_permissions_for_roles
from app.services.workflow_engine import upsert_workflow_definition


def seed_independent_purchasing(
    db: Session,
    actor: str,
) -> IndependentPurchasingSeedResponse:
    registration = WORKFLOW_REGISTRY.require_active(WorkflowCode.IND_PURCHASING)
    permission_definitions = {
        **INDEPENDENT_PERMISSION_DEFINITIONS,
        "notifications.read": GLOBAL_NOTIFICATION_PERMISSION_DEFINITIONS["notifications.read"],
        "notifications.send": GLOBAL_NOTIFICATION_PERMISSION_DEFINITIONS["notifications.send"],
    }
    permission_codes = set(permission_definitions)
    permissions = seed_permissions_for_roles(
        db,
        permission_definitions,
        {
            "SYSTEM_ADMIN": permission_codes,
            "INDEPENDENT_ADMIN": permission_codes,
        },
    )
    definition = upsert_workflow_definition(
        db,
        INDEPENDENT_PURCHASING_DEFINITION.model_copy(deep=True),
    )

    for default in (*INDEPENDENT_CONFIGURATION_DEFAULTS, *INDEPENDENT_APPROVAL_DEFAULTS):
        upsert_config_entry(
            db,
            default.model_copy(deep=True, update={"updated_by": actor}),
        )

    for default in INDEPENDENT_NOTIFICATION_TEMPLATES:
        existing = db.scalar(
            select(NotificationTemplate).where(
                NotificationTemplate.template_code == default.template_code
            )
        )
        if existing is None:
            create_notification_template(db, default.model_copy(deep=True))
        else:
            update_notification_template(
                db,
                default.template_code,
                NotificationTemplateUpdate(**default.model_dump(exclude={"template_code"})),
            )

    return IndependentPurchasingSeedResponse(
        workflow_code=definition.code,
        workflow_version=definition.version,
        permissions_seeded=len(permissions),
        configuration_entries_seeded=len(INDEPENDENT_CONFIGURATION_DEFAULTS),
        approval_entries_seeded=len(INDEPENDENT_APPROVAL_DEFAULTS),
        notification_templates_seeded=len(INDEPENDENT_NOTIFICATION_TEMPLATES),
        registry_entry_verified=registration.code == definition.code,
    )
