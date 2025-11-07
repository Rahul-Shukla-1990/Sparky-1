from __future__ import annotations

from datetime import datetime

import pytest

pytest.importorskip("pydantic")

from app.models.ais import AISMessage, VesselIdentity
from app.services.identity import IdentityTracker


def build_message(imo: str | None, name: str | None) -> AISMessage:
    return AISMessage(
        mmsi="123456789",
        imo=imo,
        vessel_name=name,
        timestamp=datetime(2024, 1, 1, 0, 0, 0),
        latitude=0.0,
        longitude=0.0,
    )


def test_detects_imo_change() -> None:
    tracker = IdentityTracker()
    identity = VesselIdentity(mmsi="123456789", imo="1234567")
    messages = [build_message("7654321", None)]

    events = tracker.analyse(identity, messages)

    assert len(events) == 1
    assert events[0].change_reason == "IMO change detected"


def test_detects_name_change() -> None:
    tracker = IdentityTracker()
    identity = VesselIdentity(mmsi="123456789", imo="1234567", name="Alpha")
    messages = [build_message("1234567", "Beta")]

    events = tracker.analyse(identity, messages)

    assert len(events) == 1
    assert events[0].change_reason == "Vessel name change detected"
