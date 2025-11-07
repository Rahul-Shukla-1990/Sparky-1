from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi.testclient import TestClient

from app.main import app
from app.models.ais import AISMessage


class FakeRepository:
    def __init__(self) -> None:
        base_time = datetime(2024, 1, 1, 0, 0, 0)
        self.messages = [
            AISMessage(
                mmsi="123456789",
                imo="1234567",
                timestamp=base_time,
                latitude=0.0,
                longitude=50.0,
                sog=12.0,
            ),
            AISMessage(
                mmsi="123456789",
                imo="1234567",
                timestamp=base_time + timedelta(hours=3),
                latitude=15.0,
                longitude=75.0,
                sog=12.0,
            ),
        ]

    async def get_recent_messages(self, identifier: str, lookback_hours: int = 48):
        return self.messages

    async def get_identity(self, mmsi: str):
        return None

    async def list_recent_dark_events(self, *, region_bbox: tuple[float, float, float, float], days: int = 1):
        return []


@pytest.fixture(autouse=True)
def override_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeRepository()

    async def _get_database() -> Any:
        class DummyDB:
            pass

        return DummyDB()

    monkeypatch.setattr("app.api.vessels.get_database", _get_database)
    monkeypatch.setattr("app.api.analysis.get_database", _get_database)
    monkeypatch.setattr("app.api.vessels.VesselRepository", lambda db: repo)
    monkeypatch.setattr("app.api.analysis.VesselRepository", lambda db: repo)


def test_healthcheck() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_vessel_summary_returns_dark_event() -> None:
    client = TestClient(app)
    response = client.get("/vessels/123456789")
    assert response.status_code == 200
    data = response.json()
    assert data["identifier"] == "123456789"
    assert data["dark_events"], "Expected dark activity event"


def test_layers_endpoints_return_data() -> None:
    client = TestClient(app)
    response = client.get("/layers/undersea-cables")
    assert response.status_code == 200
    cables = response.json()
    assert cables and cables[0]["name"]["hi"]

    response = client.get("/layers/exclusive-economic-zones")
    assert response.status_code == 200
    eez = response.json()
    assert eez["type"] == "FeatureCollection"
    assert eez["features"], "Expected EEZ features"

    response = client.get("/layers/maritime-zones")
    assert response.status_code == 200
    zones = response.json()
    assert "territorial_sea" in zones

    response = client.get("/layers/maritime-zones/territorial-sea")
    assert response.status_code == 200
    territorial = response.json()
    assert territorial["features"], "Expected territorial sea polygons"
