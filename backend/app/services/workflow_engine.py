from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workflow import WorkflowDefinition, WorkflowInstance
from app.schemas.event_snapshot import EventSnapshotCreate
from app.schemas.flow import FlowActionRequest, FlowDefinitionWrite, FlowStartRequest
from app.services.snapshot_service import append_snapshot


class WorkflowError(ValueError):
    pass


def upsert_workflow_definition(db: Session, payload: FlowDefinitionWrite) -> WorkflowDefinition:
    definition = db.scalar(
        select(WorkflowDefinition).where(
            WorkflowDefinition.code == payload.code,
            WorkflowDefinition.version == payload.version,
        )
    )
    values = payload.model_dump()
    values["transitions"] = [rule.model_dump() for rule in payload.rules]
    values.pop("rules")

    if definition is None:
        definition = WorkflowDefinition(**values)
        db.add(definition)
    else:
        for field, value in values.items():
            setattr(definition, field, value)

    db.commit()
    db.refresh(definition)
    return definition


def get_active_definition(db: Session, workflow_code: str) -> WorkflowDefinition:
    definition = db.scalar(
        select(WorkflowDefinition)
        .where(WorkflowDefinition.code == workflow_code, WorkflowDefinition.is_active.is_(True))
        .order_by(WorkflowDefinition.version.desc())
    )
    if definition is None:
        raise WorkflowError("Workflow definition not found")
    return definition


def start_workflow(db: Session, payload: FlowStartRequest, actor: str) -> WorkflowInstance:
    definition = get_active_definition(db, payload.workflow_code)
    instance = WorkflowInstance(
        workflow_code=definition.code,
        workflow_version=definition.version,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        current_state=definition.initial_state,
        status="active",
        context=payload.context,
        started_by=actor,
        updated_by=actor,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="workflow.started",
            entity_type=instance.entity_type,
            entity_id=instance.entity_id,
            actor=actor,
            payload={
                "workflow_code": instance.workflow_code,
                "state": instance.current_state,
                "context": instance.context,
            },
        ),
    )
    return instance


def find_rule(
    definition: WorkflowDefinition,
    current_state: str,
    action: str,
) -> dict[str, Any] | None:
    for rule in definition.transitions:
        if rule.get("source") == current_state and rule.get("action") == action:
            return rule
    return None


def advance_workflow(
    db: Session,
    instance_id: int,
    payload: FlowActionRequest,
    permission_codes: set[str],
) -> WorkflowInstance:
    instance = db.get(WorkflowInstance, instance_id)
    if instance is None:
        raise WorkflowError("Workflow instance not found")
    if instance.status != "active":
        raise WorkflowError("Workflow instance is not active")

    definition = get_active_definition(db, instance.workflow_code)
    rule = find_rule(definition, instance.current_state, payload.action)
    if rule is None:
        raise WorkflowError("Workflow action is not valid for current state")

    required_permission = rule.get("permission")
    if required_permission and required_permission not in permission_codes:
        raise PermissionError(required_permission)

    previous_state = instance.current_state
    target_state = rule.get("target")
    if not isinstance(target_state, str):
        raise WorkflowError("Workflow rule target is invalid")

    instance.current_state = target_state
    instance.context = {**instance.context, **payload.context_patch}
    instance.updated_by = payload.actor
    if instance.current_state in definition.terminal_states:
        instance.status = "complete"

    db.commit()
    db.refresh(instance)

    append_snapshot(
        db,
        EventSnapshotCreate(
            event_type="workflow.advanced",
            entity_type=instance.entity_type,
            entity_id=instance.entity_id,
            actor=payload.actor,
            payload={
                "workflow_code": instance.workflow_code,
                "action": payload.action,
                "from_state": previous_state,
                "to_state": instance.current_state,
                "status": instance.status,
            },
        ),
    )
    return instance
