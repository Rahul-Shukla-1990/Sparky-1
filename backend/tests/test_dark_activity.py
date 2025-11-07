from __future__ import annotations

from datetime import datetime, timedelta

import pytest

pytest.importorskip("pydantic")

from app.models.ais import AISMessage
from app.services.dark_activity import DarkActivityDetector


def build_message(minutes_offset: int, lat: float, lon: float, sog: float = 12.0) -> AISMessage:
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    return AISMessage(
        mmsi="123456789",
        imo="9876543",
        timestamp=base_time + timedelta(minutes=minutes_offset),
        latitude=lat,
        longitude=lon,
        sog=sog,
    )


def test_detects_dark_activity_when_distance_infeasible() -> None:
    detector = DarkActivityDetector(blackout_threshold_minutes=30, confidence_distance_ratio=1.2)
    messages = [
        build_message(0, 0.0, 50.0, sog=10.0),
        build_message(120, 20.0, 70.0, sog=10.0),
    ]

    events = detector.detect(messages)

    assert len(events) == 1
    event = events[0]
    assert event.observed_distance_km > event.estimated_distance_km
    assert event.confidence > 0.5


def test_ignores_short_gaps() -> None:
    detector = DarkActivityDetector(blackout_threshold_minutes=30)
    messages = [
        build_message(0, 0.0, 50.0),
        build_message(10, 0.1, 50.1),
    ]

    events = detector.detect(messages)

    assert not events
