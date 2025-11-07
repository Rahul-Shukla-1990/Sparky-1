from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NavigationStatus(str, Enum):
    UNDER_WAY_USING_ENGINE = "under_way_using_engine"
    AT_ANCHOR = "at_anchor"
    NOT_UNDER_COMMAND = "not_under_command"
    RESTRICTED_MANOEUVRABILITY = "restricted_manoeuvrability"
    CONSTRAINED_BY_DRAUGHT = "constrained_by_draught"
    MOORED = "moored"
    AGROUND = "aground"
    ENGAGED_IN_FISHING = "engaged_in_fishing"
    UNDER_WAY_SAILING = "under_way_sailing"
    RESERVED_FOR_FUTURE_USE = "reserved_for_future_use"
    AIS_SART = "ais_sart"
    UNKNOWN = "unknown"


class AISMessage(BaseModel):
    """Canonical representation of an AIS position report."""

    mmsi: str = Field(..., description="Maritime Mobile Service Identity")
    imo: Optional[str] = Field(default=None, description="IMO number when available")
    timestamp: datetime
    latitude: float
    longitude: float
    sog: Optional[float] = Field(default=None, description="Speed over ground in knots")
    cog: Optional[float] = Field(default=None, description="Course over ground in degrees")
    heading: Optional[float] = Field(default=None, description="True heading in degrees")
    vessel_name: Optional[str] = Field(default=None, description="Vessel name transmitted in AIS")
    nav_status: Optional[NavigationStatus] = None
    source: str = Field(default="mongo", description="Origin of the message")


class VesselIdentity(BaseModel):
    """Identity metadata for a vessel."""

    mmsi: str
    imo: Optional[str]
    name: Optional[str]
    call_sign: Optional[str]
    flag: Optional[str]
    vessel_type: Optional[str]
    length_m: Optional[float]
    width_m: Optional[float]
