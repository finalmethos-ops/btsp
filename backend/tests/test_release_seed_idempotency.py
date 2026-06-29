from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.v1.routes.workflow_registry import seed_workflow_registry_defaults
from app.db.session import Base
from app.models.catalog import CatalogVendor  # noqa: F401
from app.models.configuration import ConfigurationEntry
from app.models.event_snapshot import EventSnapshot  # noqa: F401
from app.models.identity import Permission, Role, User
from app.models.notification import NotificationEvent, NotificationTemplate
from app.models.store import Store  # noqa: F401
from app.models.workflow import WorkflowDefinition, WorkflowInstance  # noqa: F401
from app.schemas.admin_bootstrap import AdminBootstrapRequest
from app.services.admin_bootstrap_service import bootstrap_admin_user
from app.services.approval_policy_defaults import BPP_APPROVAL_CONFIGURATION_DEFAULTS
from app.services.approval_policy_service import seed_bpp_approval_defaults
from app.services.bpp_purchasing import BPP_PURCHASING_CONFIGURATION_DEFAULTS
from app.services.bpp_purchasing_seed_service import seed_bpp_purchasing
from app.services.configuration_defaults import DEFAULT_CONFIGURATION_ENTRIES
from app.services.configuration_seed_service import seed_default_configuration
from app.services.identity_defaults import CORE_PERMISSION_DEFINITIONS, CORE_ROLE_DEFINITIONS
from app.services.independent_defaults import (
    INDEPENDENT_APPROVAL_DEFAULTS,
    INDEPENDENT_NOTIFICATION_TEMPLATES,
)
from app.services.independent_purchasing import INDEPENDENT_CONFIGURATION_DEFAULTS
from app.services.independent_seed_service import seed_independent_purchasing
from app.services.notification_defaults import (
    BPP_NOTIFICATION_CONFIGURATION_DEFAULTS,
    BPP_NOTIFICATION_TEMPLATES,
)
from app.services.notification_service import seed_bpp_notification_defaults
from app.services.purchase_order_service import GENERATION_DEFAULTS, seed_purchase_order_defaults
from app.services.purchasing_defaults import PURCHASING_RULE_DEFAULTS
from app.services.purchasing_rule_service import seed_purchasing_defaults


def test_complete_release_seed_sequence_is_idempotent() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    bootstrap = AdminBootstrapRequest(
        email="release-admin@example.com",
        display_name="Release Administrator",
        password="temporary-release-password",
    )

    with Session(engine) as db:
        first_bootstrap = bootstrap_admin_user(db, bootstrap)
        second_bootstrap = bootstrap_admin_user(db, bootstrap)

        counts: list[tuple[int, ...]] = []
        for _ in range(2):
            seed_default_configuration(db)
            assert seed_workflow_registry_defaults(SimpleNamespace()) == {"seeded_count": 4}
            seed_bpp_purchasing(db, actor=bootstrap.email)
            seed_bpp_approval_defaults(db, actor=bootstrap.email)
            seed_bpp_notification_defaults(db, actor=bootstrap.email)
            seed_independent_purchasing(db, actor=bootstrap.email)
            seed_purchasing_defaults(db, actor=bootstrap.email)
            seed_purchase_order_defaults(db, actor=bootstrap.email)
            counts.append(
                tuple(
                    int(db.scalar(select(func.count()).select_from(model)) or 0)
                    for model in (
                        User,
                        Role,
                        Permission,
                        WorkflowDefinition,
                        NotificationTemplate,
                        NotificationEvent,
                        ConfigurationEntry,
                    )
                )
            )

        assert counts[0] == counts[1]

        assert first_bootstrap.created is True
        assert second_bootstrap.created is False
        assert db.scalar(select(func.count()).select_from(User)) == 1
        assert db.scalar(select(func.count()).select_from(Role)) == len(CORE_ROLE_DEFINITIONS)
        assert db.scalar(select(func.count()).select_from(Permission)) == len(
            CORE_PERMISSION_DEFINITIONS
        )
        assert db.scalar(select(func.count()).select_from(WorkflowDefinition)) == 2
        assert db.scalar(select(func.count()).select_from(NotificationTemplate)) == len(
            BPP_NOTIFICATION_TEMPLATES
        ) + len(INDEPENDENT_NOTIFICATION_TEMPLATES)
        assert db.scalar(select(func.count()).select_from(NotificationEvent)) == 0

        configuration_count = db.scalar(select(func.count()).select_from(ConfigurationEntry))
        assert configuration_count == sum(
            (
                len(DEFAULT_CONFIGURATION_ENTRIES),
                len(BPP_PURCHASING_CONFIGURATION_DEFAULTS),
                len(BPP_APPROVAL_CONFIGURATION_DEFAULTS),
                len(BPP_NOTIFICATION_CONFIGURATION_DEFAULTS),
                len(INDEPENDENT_CONFIGURATION_DEFAULTS),
                len(INDEPENDENT_APPROVAL_DEFAULTS),
                2 * len(PURCHASING_RULE_DEFAULTS),
                len(GENERATION_DEFAULTS),
            )
        )
