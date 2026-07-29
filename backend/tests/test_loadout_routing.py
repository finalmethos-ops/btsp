from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.loadout_routing_service import (
    LoadoutRoutingError,
    _validated_api_base,
    estimate_store_route,
    recalculate_store_routes,
)


def _event():
    return SimpleNamespace(
        id="event-1",
        timezone="America/New_York",
        ends_at=datetime(2027, 5, 3, 20, tzinfo=UTC),
        address_line1="100 Show Way",
        city="Orlando",
        state_code="FL",
        postal_code="32801",
    )


def _store():
    return SimpleNamespace(
        store_number="1001",
        address_line1="200 Store Way",
        city="Tampa",
        state_code="FL",
        postal_code="33602",
    )


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None


def test_routing_provider_rejects_non_http_endpoints() -> None:
    with pytest.raises(LoadoutRoutingError, match="HTTP\\(S\\)"):
        _validated_api_base("file:///tmp/route.json", "Routing API")
    with pytest.raises(LoadoutRoutingError, match="HTTP\\(S\\)"):
        _validated_api_base("https://user:secret@routes.example.test", "Routing API")


def test_route_estimate_targets_six_pm_in_event_timezone() -> None:
    db = MagicMock()
    db.get.return_value = _event()
    db.scalar.side_effect = [_store(), None]
    with (
        patch(
            "app.services.loadout_routing_service._geocode",
            side_effect=[(28.5, -81.4), (27.95, -82.46)],
        ),
        patch(
            "app.services.loadout_routing_service.urlopen",
            return_value=_Response(),
        ) as open_route,
        patch(
            "app.services.loadout_routing_service.json.load",
            return_value={"routes": [{"distance": 160934.4, "duration": 7200}]},
        ),
    ):
        estimate = estimate_store_route(db, "event-1", "1001")

    assert estimate is not None
    assert estimate.distance_miles == 100
    assert estimate.estimated_drive_minutes == 120
    assert estimate.arrival_target_at.hour == 18
    assert estimate.arrival_target_at.tzinfo is not None
    assert estimate.recommended_departure_at.hour == 16
    assert open_route.called


def test_recalculate_routes_skips_completed_assignments() -> None:
    db = MagicMock()
    active = SimpleNamespace(
        store_number="1001",
        status="not_started",
        distance_miles=None,
        estimated_drive_minutes=None,
        recommended_departure_at=None,
    )
    db.scalars.return_value.all.return_value = [active]
    db.get.return_value = _event()
    db.scalar.side_effect = [_store(), None]
    with (
        patch(
            "app.services.loadout_routing_service._geocode",
            side_effect=[(28.5, -81.4), (27.95, -82.46)],
        ),
        patch(
            "app.services.loadout_routing_service.urlopen",
            return_value=_Response(),
        ),
        patch(
            "app.services.loadout_routing_service.json.load",
            return_value={"routes": [{"distance": 160934.4, "duration": 7200}]},
        ),
    ):
        result = recalculate_store_routes(db, "event-1")

    assert result.updated == 1
    assert result.failed_store_numbers == []
    assert active.distance_miles == 100
    assert active.estimated_drive_minutes == 120
    db.commit.assert_called_once()
