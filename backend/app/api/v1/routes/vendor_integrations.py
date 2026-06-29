from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.permissions import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.schemas.vendor_integration import (
    VendorAcknowledgementResponse,
    VendorAcknowledgementStatus,
    VendorASNResponse,
    VendorConnectorClaimRequest,
    VendorConnectorClaimResponse,
    VendorConnectorExecutionResponse,
    VendorConnectorExecutionResult,
    VendorConnectorImportRunResponse,
    VendorConnectorScheduleCreate,
    VendorConnectorScheduleResponse,
    VendorConnectorScheduleUpdate,
    VendorEndpointCreate,
    VendorEndpointResponse,
    VendorEventType,
    VendorInboundEventCreate,
    VendorInboundEventResponse,
    VendorShipmentResponse,
)
from app.services.vendor_acknowledgement_service import (
    VendorAcknowledgementError,
    get_vendor_acknowledgement,
    list_vendor_acknowledgements,
    process_vendor_acknowledgement,
)
from app.services.vendor_connector_import_service import (
    MAX_CONNECTOR_IMPORT_BYTES,
    VendorConnectorImportError,
    import_vendor_events,
    list_connector_import_runs,
)
from app.services.vendor_connector_operations_service import (
    VendorConnectorOperationsError,
    claim_connector_execution,
    complete_connector_execution,
    create_connector_schedule,
    enqueue_due_connector_executions,
    list_connector_executions,
    list_connector_schedules,
    replay_dead_letter,
    update_connector_schedule,
)
from app.services.vendor_integration_service import (
    VendorIntegrationError,
    create_vendor_endpoint,
    get_vendor_endpoint,
    ingest_vendor_event,
    list_vendor_endpoints,
    list_vendor_events,
)
from app.services.vendor_shipment_service import (
    VendorShipmentError,
    list_asns,
    list_shipments,
    process_asn,
    process_shipment_update,
)

router = APIRouter(prefix="/vendor-integrations", tags=["vendor-integrations"])


@router.post(
    "/connector-schedules",
    response_model=VendorConnectorScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_schedule(
    payload: VendorConnectorScheduleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.connectors.operate")),
) -> VendorConnectorScheduleResponse:
    try:
        schedule = create_connector_schedule(db, payload, user.email)
    except VendorConnectorOperationsError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return VendorConnectorScheduleResponse.model_validate(schedule)


@router.get("/connector-schedules", response_model=list[VendorConnectorScheduleResponse])
def read_schedules(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> list[VendorConnectorScheduleResponse]:
    return [
        VendorConnectorScheduleResponse.model_validate(item)
        for item in list_connector_schedules(db)
    ]


@router.patch(
    "/connector-schedules/{schedule_id}",
    response_model=VendorConnectorScheduleResponse,
)
def update_schedule(
    schedule_id: str,
    payload: VendorConnectorScheduleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.connectors.operate")),
) -> VendorConnectorScheduleResponse:
    try:
        schedule = update_connector_schedule(db, schedule_id, payload, user.email)
    except VendorConnectorOperationsError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return VendorConnectorScheduleResponse.model_validate(schedule)


@router.post(
    "/connector-executions/enqueue-due", response_model=list[VendorConnectorExecutionResponse]
)
def enqueue_due(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.connectors.operate")),
) -> list[VendorConnectorExecutionResponse]:
    return [
        VendorConnectorExecutionResponse.model_validate(item)
        for item in enqueue_due_connector_executions(db, user.email)
    ]


@router.post(
    "/connector-executions/claim",
    response_model=VendorConnectorClaimResponse | None,
)
def claim_execution(
    payload: VendorConnectorClaimRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.connectors.work")),
) -> VendorConnectorClaimResponse | None:
    claimed = claim_connector_execution(db, payload.worker_id, payload.lease_seconds)
    if claimed is None:
        return None
    execution, token = claimed
    public = VendorConnectorExecutionResponse.model_validate(execution)
    endpoint = get_vendor_endpoint(db, execution.endpoint_id)
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Claimed connector endpoint no longer exists",
        )
    return VendorConnectorClaimResponse(
        **public.model_dump(),
        lease_token=token,
        endpoint_transport=endpoint.transport,
        endpoint_connection_reference=endpoint.connection_reference,
        endpoint_configuration=endpoint.configuration,
    )


@router.post(
    "/connector-executions/{execution_id}/result",
    response_model=VendorConnectorExecutionResponse,
)
def complete_execution(
    execution_id: str,
    payload: VendorConnectorExecutionResult,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.connectors.work")),
) -> VendorConnectorExecutionResponse:
    try:
        execution = complete_connector_execution(db, execution_id, payload, user.email)
    except VendorConnectorOperationsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return VendorConnectorExecutionResponse.model_validate(execution)


@router.post(
    "/connector-executions/{execution_id}/replay",
    response_model=VendorConnectorExecutionResponse,
)
def replay_execution(
    execution_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.connectors.operate")),
) -> VendorConnectorExecutionResponse:
    try:
        execution = replay_dead_letter(db, execution_id, user.email)
    except VendorConnectorOperationsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return VendorConnectorExecutionResponse.model_validate(execution)


@router.get("/connector-executions", response_model=list[VendorConnectorExecutionResponse])
def read_executions(
    execution_status: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> list[VendorConnectorExecutionResponse]:
    return [
        VendorConnectorExecutionResponse.model_validate(item)
        for item in list_connector_executions(db, execution_status)
    ]


@router.post(
    "/endpoints/{endpoint_id}/imports",
    response_model=VendorConnectorImportRunResponse,
)
async def import_endpoint_events(
    endpoint_id: str,
    response: Response,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.integrations.ingest")),
) -> VendorConnectorImportRunResponse:
    content = await file.read(MAX_CONNECTOR_IMPORT_BYTES + 1)
    try:
        run, created = import_vendor_events(
            db,
            endpoint_id,
            content,
            file.filename or "import.json",
            file.content_type,
            user.email,
        )
    except VendorConnectorImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return VendorConnectorImportRunResponse.model_validate(run)


@router.get("/imports", response_model=list[VendorConnectorImportRunResponse])
def read_connector_imports(
    endpoint_id: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> list[VendorConnectorImportRunResponse]:
    return [
        VendorConnectorImportRunResponse.model_validate(run)
        for run in list_connector_import_runs(db, endpoint_id)
    ]


@router.post(
    "/endpoints",
    response_model=VendorEndpointResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_endpoint(
    payload: VendorEndpointCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.integrations.manage")),
) -> VendorEndpointResponse:
    try:
        endpoint = create_vendor_endpoint(db, payload, user.email)
    except VendorIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return VendorEndpointResponse.model_validate(endpoint)


@router.get("/endpoints", response_model=list[VendorEndpointResponse])
def read_endpoints(
    vendor_code: str | None = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> list[VendorEndpointResponse]:
    return [
        VendorEndpointResponse.model_validate(endpoint)
        for endpoint in list_vendor_endpoints(db, vendor_code, active_only)
    ]


@router.get("/endpoints/{endpoint_id}", response_model=VendorEndpointResponse)
def read_endpoint(
    endpoint_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> VendorEndpointResponse:
    endpoint = get_vendor_endpoint(db, endpoint_id)
    if endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vendor endpoint not found"
        )
    return VendorEndpointResponse.model_validate(endpoint)


@router.post("/events", response_model=VendorInboundEventResponse)
def receive_event(
    payload: VendorInboundEventCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.integrations.ingest")),
) -> VendorInboundEventResponse:
    try:
        event, created = ingest_vendor_event(db, payload, user.email)
    except VendorIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return VendorInboundEventResponse.model_validate(event)


@router.get("/events", response_model=list[VendorInboundEventResponse])
def read_events(
    endpoint_id: str | None = None,
    vendor_code: str | None = None,
    event_type: VendorEventType | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> list[VendorInboundEventResponse]:
    return [
        VendorInboundEventResponse.model_validate(event)
        for event in list_vendor_events(
            db,
            endpoint_id=endpoint_id,
            vendor_code=vendor_code,
            event_type=event_type.value if event_type is not None else None,
        )
    ]


@router.post(
    "/events/{event_id}/process-acknowledgement",
    response_model=VendorAcknowledgementResponse,
)
def process_acknowledgement(
    event_id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.acknowledgements.process")),
) -> VendorAcknowledgementResponse:
    try:
        acknowledgement, created = process_vendor_acknowledgement(db, event_id, user.email)
    except VendorAcknowledgementError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return VendorAcknowledgementResponse.model_validate(acknowledgement)


@router.get("/acknowledgements", response_model=list[VendorAcknowledgementResponse])
def read_acknowledgements(
    purchase_order_id: str | None = None,
    vendor_code: str | None = None,
    acknowledgement_status: VendorAcknowledgementStatus | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> list[VendorAcknowledgementResponse]:
    return [
        VendorAcknowledgementResponse.model_validate(item)
        for item in list_vendor_acknowledgements(
            db,
            purchase_order_id=purchase_order_id,
            vendor_code=vendor_code,
            acknowledgement_status=(
                acknowledgement_status.value if acknowledgement_status is not None else None
            ),
        )
    ]


@router.get("/acknowledgements/{acknowledgement_id}", response_model=VendorAcknowledgementResponse)
def read_acknowledgement(
    acknowledgement_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> VendorAcknowledgementResponse:
    acknowledgement = get_vendor_acknowledgement(db, acknowledgement_id)
    if acknowledgement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor acknowledgement not found",
        )
    return VendorAcknowledgementResponse.model_validate(acknowledgement)


@router.post("/events/{event_id}/process-shipment", status_code=status.HTTP_201_CREATED)
def project_shipment(
    event_id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.logistics.process")),
):
    try:
        update, created = process_shipment_update(db, event_id, user.email)
    except VendorShipmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.status_code = 201 if created else 200
    return {"shipment_id": update.shipment_id, "status": update.status}


@router.post("/events/{event_id}/process-asn", response_model=VendorASNResponse)
def project_asn(
    event_id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("vendor.logistics.process")),
) -> VendorASNResponse:
    try:
        asn, created = process_asn(db, event_id, user.email)
    except VendorShipmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    response.status_code = 201 if created else 200
    return VendorASNResponse.model_validate(asn)


@router.get("/shipments", response_model=list[VendorShipmentResponse])
def read_shipments(
    purchase_order_id: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> list[VendorShipmentResponse]:
    return [
        VendorShipmentResponse.model_validate(item)
        for item in list_shipments(db, purchase_order_id)
    ]


@router.get("/asns", response_model=list[VendorASNResponse])
def read_asns(
    purchase_order_id: str | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("vendor.integrations.read")),
) -> list[VendorASNResponse]:
    return [VendorASNResponse.model_validate(item) for item in list_asns(db, purchase_order_id)]
