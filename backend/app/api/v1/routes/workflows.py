from fastapi import APIRouter, Depends

from app.auth.dependencies import get_current_user
from app.core.workflows import WORKFLOW_ROUTES
from app.models.identity import User
from app.services.auth_service import user_workflow_codes

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/available")
def read_available_workflows(current_user: User = Depends(get_current_user)) -> list[dict[str, str]]:
    workflows = user_workflow_codes(current_user)
    return [
        {"code": workflow_code, "route": WORKFLOW_ROUTES[workflow_code]}
        for workflow_code in workflows
        if workflow_code in WORKFLOW_ROUTES
    ]
