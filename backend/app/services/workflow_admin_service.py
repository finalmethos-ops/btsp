from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.workflows import WORKFLOW_REGISTRY, WorkflowRegistryError
from app.models.event_snapshot import EventSnapshot
from app.models.workflow import WorkflowDefinition, WorkflowInstance
from app.schemas.workflow_admin import WorkflowDefinitionAdminResponse


class WorkflowAdminError(ValueError):
    pass


def _counts(db: Session) -> dict[tuple[str, int], tuple[int, int]]:
    rows = db.execute(
        select(
            WorkflowInstance.workflow_code,
            WorkflowInstance.workflow_version,
            func.count(WorkflowInstance.id),
            func.count(WorkflowInstance.id).filter(WorkflowInstance.status == "active"),
        ).group_by(WorkflowInstance.workflow_code, WorkflowInstance.workflow_version)
    ).all()
    return {(code, version): (int(total), int(active)) for code, version, total, active in rows}


def _response(
    definition: WorkflowDefinition, counts: tuple[int, int] = (0, 0)
) -> WorkflowDefinitionAdminResponse:
    total, active = counts
    return WorkflowDefinitionAdminResponse(
        id=definition.id,
        code=definition.code,
        name=definition.name,
        version=definition.version,
        business_area=definition.business_area,
        category=definition.category,
        configuration_namespace=definition.configuration_namespace,
        states=definition.states,
        initial_state=definition.initial_state,
        terminal_states=definition.terminal_states,
        transitions=definition.transitions,
        is_active=definition.is_active,
        active_instance_count=active,
        total_instance_count=total,
        created_at=definition.created_at,
        updated_at=definition.updated_at,
    )


def list_workflow_definitions(db: Session) -> list[WorkflowDefinitionAdminResponse]:
    definitions = db.scalars(
        select(WorkflowDefinition).order_by(
            WorkflowDefinition.code, WorkflowDefinition.version.desc()
        )
    ).all()
    counts = _counts(db)
    return [_response(item, counts.get((item.code, item.version), (0, 0))) for item in definitions]


def set_workflow_activation(
    db: Session,
    workflow_code: str,
    version: int,
    is_active: bool,
    actor: str,
) -> WorkflowDefinitionAdminResponse | None:
    try:
        WORKFLOW_REGISTRY.require(workflow_code)
    except WorkflowRegistryError as exc:
        raise WorkflowAdminError(str(exc)) from exc
    definition = db.scalar(
        select(WorkflowDefinition)
        .where(
            WorkflowDefinition.code == workflow_code,
            WorkflowDefinition.version == version,
        )
        .with_for_update()
    )
    if definition is None:
        return None
    previous_active = definition.is_active
    superseded_versions: list[int] = []
    if is_active:
        active_definitions = db.scalars(
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.code == workflow_code,
                WorkflowDefinition.is_active.is_(True),
                WorkflowDefinition.id != definition.id,
            )
            .with_for_update()
        ).all()
        for item in active_definitions:
            item.is_active = False
            superseded_versions.append(item.version)
    definition.is_active = is_active
    db.add(
        EventSnapshot(
            event_type="admin.workflow.activation_changed",
            entity_type="workflow_definition",
            entity_id=f"{workflow_code}:{version}",
            actor=actor,
            payload={
                "is_active": is_active,
                "previous_is_active": previous_active,
                "superseded_versions": sorted(superseded_versions),
            },
        )
    )
    db.commit()
    db.refresh(definition)
    counts = _counts(db).get((workflow_code, version), (0, 0))
    return _response(definition, counts)
