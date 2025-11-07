from __future__ import annotations

from typing import Iterable, List

from ..models.ais import AISMessage
from ..models.detection import DarkActivityEvent
from ..utils.geo import haversine_distance_km, is_water_route

# Conversion constant from knots to km/h
KNOT_TO_KMH = 1.852


class DarkActivityDetector:
    """Evaluate AIS message sequences to identify suspicious gaps."""

    def __init__(
        self,
        *,
        blackout_threshold_minutes: float = 30.0,
        acceleration_buffer_kmh: float = 10.0,
        confidence_distance_ratio: float = 1.5,
    ) -> None:
        self.blackout_threshold_minutes = blackout_threshold_minutes
        self.acceleration_buffer_kmh = acceleration_buffer_kmh
        self.confidence_distance_ratio = confidence_distance_ratio

    def detect(self, track: Iterable[AISMessage]) -> List[DarkActivityEvent]:
        """Return detected dark activity events for a chronologically sorted track."""

        messages = list(track)
        events: List[DarkActivityEvent] = []
        for previous, current in zip(messages, messages[1:]):
            gap_minutes = (current.timestamp - previous.timestamp).total_seconds() / 60.0
            if gap_minutes < self.blackout_threshold_minutes:
                continue

            observed_distance = haversine_distance_km(
                (previous.latitude, previous.longitude),
                (current.latitude, current.longitude),
            )
            estimated_distance = self._estimate_max_distance(previous, gap_minutes)
            water_only = is_water_route(
                (previous.latitude, previous.longitude),
                (current.latitude, current.longitude),
            )

            if not water_only:
                # Travelling across land is physically implausible for vessels and indicates spoofing.
                confidence = 1.0
                note = "Route crosses land and indicates identity/position spoofing"
            else:
                confidence = min(1.0, observed_distance / (estimated_distance * self.confidence_distance_ratio))
                note = None

            if observed_distance > estimated_distance * self.confidence_distance_ratio or not water_only:
                events.append(
                    DarkActivityEvent(
                        mmsi=current.mmsi,
                        start_timestamp=previous.timestamp,
                        end_timestamp=current.timestamp,
                        gap_minutes=gap_minutes,
                        estimated_distance_km=estimated_distance,
                        observed_distance_km=observed_distance,
                        location_start=(previous.latitude, previous.longitude),
                        location_end=(current.latitude, current.longitude),
                        confidence=confidence,
                        notes=note,
                    )
                )
        return events

    def _estimate_max_distance(self, message: AISMessage, gap_minutes: float) -> float:
        """Estimate feasible travel distance during an AIS blackout."""

        speed_knots = message.sog or 0.0
        speed_kmh = speed_knots * KNOT_TO_KMH + self.acceleration_buffer_kmh
        hours = gap_minutes / 60.0
        return speed_kmh * hours


class DarkActivitySummariser:
    """Aggregate dark activity events into daily statistics."""

    def summarise(self, events: Iterable[DarkActivityEvent]) -> dict[str, float]:
        total_events = 0
        high_confidence = 0
        average_gap = 0.0

        events_list: List[DarkActivityEvent] = list(events)
        if not events_list:
            return {
                "total_events": 0,
                "high_confidence_events": 0,
                "average_gap_minutes": 0.0,
            }

        for event in events_list:
            total_events += 1
            if event.confidence >= 0.75:
                high_confidence += 1
            average_gap += event.gap_minutes

        return {
            "total_events": total_events,
            "high_confidence_events": high_confidence,
            "average_gap_minutes": average_gap / total_events,
        }
