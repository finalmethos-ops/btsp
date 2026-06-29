from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.core.config import settings
from app.db.session import get_db
from app.models.analytics import AnalyticsReportRun
from app.models.identity import User
from app.schemas.analytics import (
    AnalyticsReportRunResponse,
    AnalyticsReportScheduleCreate,
    AnalyticsReportScheduleResponse,
    AnalyticsReportType,
    InventoryPositionResponse,
    OperationalDashboardResponse,
    SpendAnalysisResponse,
    SpendDimension,
    VendorScorecardResponse,
    WorkflowAnalyticsResponse,
)
from app.services.analytics_report_service import (
    AnalyticsReportError,
    create_report_schedule,
    list_report_runs,
    list_report_schedules,
    render_analytics_report,
    report_run_path,
    run_due_reports,
)
from app.services.analytics_service import (
    inventory_positions,
    operational_dashboard,
    spend_analysis,
    vendor_scorecards,
    workflow_analytics,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _validate_date_window(date_from: datetime | None, date_to: datetime | None) -> None:
    if date_from is not None and date_to is not None and date_from >= date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from must be earlier than date_to",
        )


@router.get("/operational-dashboard", response_model=OperationalDashboardResponse)
def read_operational_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> OperationalDashboardResponse:
    return operational_dashboard(db)


@router.get("/spend", response_model=SpendAnalysisResponse)
def read_spend_analysis(
    group_by: SpendDimension = SpendDimension.VENDOR,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    vendor_code: str | None = None,
    store_number: str | None = None,
    workflow_code: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> SpendAnalysisResponse:
    _validate_date_window(date_from, date_to)
    return spend_analysis(
        db,
        group_by,
        date_from=date_from,
        date_to=date_to,
        vendor_code=vendor_code,
        store_number=store_number,
        workflow_code=workflow_code,
    )


@router.get("/vendor-scorecards", response_model=VendorScorecardResponse)
def read_vendor_scorecards(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    minimum_orders: int = Query(default=1, ge=1, le=1000000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> VendorScorecardResponse:
    _validate_date_window(date_from, date_to)
    return vendor_scorecards(db, date_from, date_to, minimum_orders)


@router.get("/workflows", response_model=WorkflowAnalyticsResponse)
def read_workflow_analytics(
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    workflow_code: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> WorkflowAnalyticsResponse:
    _validate_date_window(date_from, date_to)
    return workflow_analytics(db, date_from, date_to, workflow_code)


@router.get("/inventory-position", response_model=InventoryPositionResponse)
def read_inventory_position(
    store_number: str | None = None,
    product_code: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> InventoryPositionResponse:
    return inventory_positions(db, store_number, product_code)


@router.get("/exports/{report_type}")
def export_report(
    report_type: AnalyticsReportType,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> Response:
    content = render_analytics_report(db, report_type, {})
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report_type.value}.csv"'},
    )


@router.post(
    "/report-schedules",
    response_model=AnalyticsReportScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_report_schedule(
    payload: AnalyticsReportScheduleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("analytics.reports.manage")),
) -> AnalyticsReportScheduleResponse:
    try:
        schedule = create_report_schedule(db, payload, user.email)
    except AnalyticsReportError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return AnalyticsReportScheduleResponse.model_validate(schedule)


@router.get("/report-schedules", response_model=list[AnalyticsReportScheduleResponse])
def read_report_schedules(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> list[AnalyticsReportScheduleResponse]:
    return [
        AnalyticsReportScheduleResponse.model_validate(item)
        for item in list_report_schedules(db, limit)
    ]


@router.post("/report-runs/run-due", response_model=list[AnalyticsReportRunResponse])
def generate_due_reports(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("analytics.reports.manage")),
) -> list[AnalyticsReportRunResponse]:
    return [
        AnalyticsReportRunResponse.model_validate(item)
        for item in run_due_reports(db, user.email, settings.analytics_report_path)
    ]


@router.get("/report-runs", response_model=list[AnalyticsReportRunResponse])
def read_report_runs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> list[AnalyticsReportRunResponse]:
    return [AnalyticsReportRunResponse.model_validate(item) for item in list_report_runs(db, limit)]


@router.get("/report-runs/{run_id}/content")
def download_report_run(
    run_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("analytics.read")),
) -> FileResponse:
    run = db.get(AnalyticsReportRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report run not found")
    try:
        path = report_run_path(run, settings.analytics_report_path)
    except AnalyticsReportError as exc:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail=str(exc)) from exc
    return FileResponse(path, media_type=run.content_type, filename=f"analytics-{run.id}.csv")
