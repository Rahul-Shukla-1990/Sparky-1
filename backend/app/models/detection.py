from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DarkActivityEvent(BaseModel):
    """Represents a suspected AIS blackout episode for a vessel."""

    mmsi: str
    start_timestamp: datetime
    end_timestamp: datetime
    gap_minutes: float = Field(..., description="Duration of the AIS gap in minutes")
    estimated_distance_km: float = Field(
        ..., description="Estimated maximum feasible distance during blackout"
    )
    observed_distance_km: float = Field(
        ..., description="Distance between observed positions surrounding blackout"
    )
    location_start: tuple[float, float]
    location_end: tuple[float, float]
    confidence: float = Field(
        ..., description="Confidence score between 0 and 1 for intentional dark activity"
    )
    notes: Optional[str] = None


class IdentityChangeEvent(BaseModel):
    """Tracks inconsistencies in vessel identity claims over time."""

    mmsi: str
    previous_imo: Optional[str]
    new_imo: Optional[str]
    previous_name: Optional[str]
    new_name: Optional[str]
    timestamp: datetime
    change_reason: str = Field(
        default="unknown",
        description="Optional explanation or detection heuristic for the change",
    )
