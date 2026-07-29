import json
import math
from datetime import timedelta
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.event_management import ManagedEvent, StoreLoadoutAssignment, StoreLoadoutEvent
from app.models.store import Store
from app.schemas.store_loadout import (
    StoreLoadoutRouteEstimateResponse,
    StoreLoadoutRouteRecalculateResponse,
)


class LoadoutRoutingError(ValueError):
    pass


_STATE_NAME_TO_CODE = {
    "ALABAMA": "AL",
    "ALASKA": "AK",
    "ARIZONA": "AZ",
    "ARKANSAS": "AR",
    "CALIFORNIA": "CA",
    "COLORADO": "CO",
    "CONNECTICUT": "CT",
    "DELAWARE": "DE",
    "FLORIDA": "FL",
    "GEORGIA": "GA",
    "HAWAII": "HI",
    "IDAHO": "ID",
    "ILLINOIS": "IL",
    "INDIANA": "IN",
    "IOWA": "IA",
    "KANSAS": "KS",
    "KENTUCKY": "KY",
    "LOUISIANA": "LA",
    "MAINE": "ME",
    "MARYLAND": "MD",
    "MASSACHUSETTS": "MA",
    "MICHIGAN": "MI",
    "MINNESOTA": "MN",
    "MISSISSIPPI": "MS",
    "MISSOURI": "MO",
    "MONTANA": "MT",
    "NEBRASKA": "NE",
    "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH",
    "NEW JERSEY": "NJ",
    "NEW MEXICO": "NM",
    "NEW YORK": "NY",
    "NORTH CAROLINA": "NC",
    "NORTH DAKOTA": "ND",
    "OHIO": "OH",
    "OKLAHOMA": "OK",
    "OREGON": "OR",
    "PENNSYLVANIA": "PA",
    "RHODE ISLAND": "RI",
    "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD",
    "TENNESSEE": "TN",
    "TEXAS": "TX",
    "UTAH": "UT",
    "VERMONT": "VT",
    "VIRGINIA": "VA",
    "WASHINGTON": "WA",
    "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI",
    "WYOMING": "WY",
    "DISTRICT OF COLUMBIA": "DC",
}


def _state_code(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    return _STATE_NAME_TO_CODE.get(normalized, normalized)


def _validated_api_base(value: str, label: str) -> str:
    parsed = urlparse(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise LoadoutRoutingError(f"{label} must be a valid HTTP(S) endpoint")
    if settings.environment.lower() == "production" and parsed.scheme != "https":
        raise LoadoutRoutingError(f"{label} must use HTTPS in production")
    return value.rstrip("/")


def _geocode(query: str) -> tuple[float, float]:
    base_url = _validated_api_base(settings.geocoding_api_url, "Geocoding API")
    url = f"{base_url}?{urlencode({'q': query, 'format': 'jsonv2', 'limit': 1})}"
    request = Request(url, headers={"User-Agent": "BTSP-loadout-routing/1.0"})
    try:
        # The provider base is restricted by _validated_api_base above.
        with urlopen(request, timeout=8) as response:  # nosec B310
            results = json.load(response)
    except Exception as exc:  # pragma: no cover - provider/network dependent
        raise LoadoutRoutingError("Address geocoding is currently unavailable") from exc
    if not results:
        raise LoadoutRoutingError("Could not locate the event or store address")
    return float(results[0]["lat"]), float(results[0]["lon"])


def estimate_store_route(
    db: Session, event_id: str, store_number: str
) -> StoreLoadoutRouteEstimateResponse | None:
    event = db.get(ManagedEvent, event_id)
    store = db.scalar(select(Store).where(Store.store_number == store_number))
    if event is None or store is None:
        return None
    if (
        store.state_code
        and event.state_code
        and _state_code(store.state_code) != _state_code(event.state_code)
    ):
        raise LoadoutRoutingError("Store must be in the event state for loadout")
    event_address = ", ".join(
        value
        for value in [
            event.address_line1,
            event.city,
            _state_code(event.state_code),
            event.postal_code,
        ]
        if value
    )
    store_address = ", ".join(
        value
        for value in [
            store.address_line1,
            store.city,
            _state_code(store.state_code),
            store.postal_code,
        ]
        if value
    )
    if not event_address or not store_address:
        raise LoadoutRoutingError("Both event and store addresses are required")
    event_lat, event_lon = _geocode(event_address)
    store_lat, store_lon = _geocode(store_address)
    routing_base = _validated_api_base(settings.routing_api_url, "Routing API")
    route_url = f"{routing_base}/{event_lon},{event_lat};{store_lon},{store_lat}"
    request = Request(
        f"{route_url}?{urlencode({'overview': 'false'})}",
        headers={"User-Agent": "BTSP-loadout-routing/1.0"},
    )
    try:
        # The provider base is restricted by _validated_api_base above.
        with urlopen(request, timeout=10) as response:  # nosec B310
            route = json.load(response)
        route_data = route["routes"][0]
        distance_miles = float(route_data["distance"]) / 1609.344
        drive_minutes = max(1, math.ceil(float(route_data["duration"]) / 60))
        source = "OSRM/OpenStreetMap"
    except Exception as exc:  # pragma: no cover - provider/network dependent
        raise LoadoutRoutingError("Driving route calculation is currently unavailable") from exc
    try:
        event_zone = ZoneInfo(event.timezone)
    except Exception:
        event_zone = ZoneInfo("UTC")
    target = event.ends_at.astimezone(event_zone).replace(
        hour=18, minute=0, second=0, microsecond=0
    )
    loadout = db.scalar(select(StoreLoadoutEvent).where(StoreLoadoutEvent.event_id == event_id))
    if loadout and loadout.loadout_deadline:
        target = loadout.loadout_deadline.astimezone(event_zone).replace(
            hour=18, minute=0, second=0, microsecond=0
        )
    departure = target - timedelta(minutes=drive_minutes)
    return StoreLoadoutRouteEstimateResponse(
        store_number=store_number,
        distance_miles=round(distance_miles, 2),
        estimated_drive_minutes=drive_minutes,
        recommended_departure_at=departure,
        arrival_target_at=target,
        source=source,
    )


def recalculate_store_routes(db: Session, event_id: str) -> StoreLoadoutRouteRecalculateResponse:
    assignments = db.scalars(
        select(StoreLoadoutAssignment)
        .where(StoreLoadoutAssignment.event_id == event_id)
        .where(StoreLoadoutAssignment.status.not_in(("signed_complete", "released_from_venue")))
    ).all()
    updated = 0
    failed: list[str] = []
    for assignment in assignments:
        try:
            estimate = estimate_store_route(db, event_id, assignment.store_number)
        except LoadoutRoutingError:
            failed.append(assignment.store_number)
            continue
        if estimate is None:
            failed.append(assignment.store_number)
            continue
        assignment.distance_miles = estimate.distance_miles
        assignment.estimated_drive_minutes = estimate.estimated_drive_minutes
        assignment.recommended_departure_at = estimate.recommended_departure_at
        updated += 1
    db.commit()
    return StoreLoadoutRouteRecalculateResponse(
        updated=updated,
        failed_store_numbers=sorted(set(failed)),
    )
