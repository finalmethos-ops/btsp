from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.workflow import WorkflowInstance


def sync_workflow_entity_projection(db: Session, instance: "WorkflowInstance") -> None:
    """Update domain read projections without moving domain rules into the workflow engine."""
    if instance.entity_type != "purchase_request":
        return
    from app.models.purchasing import PurchaseRequest

    request = db.get(PurchaseRequest, instance.entity_id)
    if request is None:
        return
    request.status = instance.current_state
    request.updated_by = instance.updated_by
    request.revision += 1
