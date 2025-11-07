from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_database
from ..models.ais import AISMessage
from ..models.detection import DarkActivityEvent, IdentityChangeEvent
from ..services.dark_activity import DarkActivityDetector
from ..services.identity import IdentityTracker
from ..services.repository import VesselRepository

router = APIRouter(prefix="/vessels", tags=["vessels"])


def _validate_identifier(identifier: str) -> str:
    if not identifier.isdigit() and len(identifier) < 7:
        raise HTTPException(status_code=400, detail="Identifier must be MMSI or IMO")
    return identifier


@router.get("/{identifier}", response_model=dict)
async def get_vessel_summary(
    identifier: str,
    db=Depends(get_database),
) -> dict:
    identifier = _validate_identifier(identifier)
    repository = VesselRepository(db)
    messages = await repository.get_recent_messages(identifier)
    if not messages:
        raise HTTPException(status_code=404, detail="Vessel not found")

    identity = await repository.get_identity(messages[0].mmsi)
    detector = DarkActivityDetector()
    tracker = IdentityTracker()

    dark_events = detector.detect(messages)
    identity_events = tracker.analyse(identity, messages)

    return {
        "identifier": identifier,
        "latest_message": messages[-1],
        "identity": identity,
        "dark_events": dark_events,
        "identity_events": identity_events,
    }


@router.get("/{identifier}/track", response_model=list[AISMessage])
async def get_track(
    identifier: str,
    lookback_hours: int = 24,
    db=Depends(get_database),
) -> list[AISMessage]:
    identifier = _validate_identifier(identifier)
    repository = VesselRepository(db)
    return await repository.get_recent_messages(identifier, lookback_hours=lookback_hours)


@router.get("/{identifier}/dark-activity", response_model=list[DarkActivityEvent])
async def get_dark_activity(
    identifier: str,
    db=Depends(get_database),
) -> list[DarkActivityEvent]:
    identifier = _validate_identifier(identifier)
    repository = VesselRepository(db)
    messages = await repository.get_recent_messages(identifier, lookback_hours=72)
    detector = DarkActivityDetector()
    return detector.detect(messages)


@router.get("/{identifier}/identity-events", response_model=list[IdentityChangeEvent])
async def get_identity_events(
    identifier: str,
    db=Depends(get_database),
) -> list[IdentityChangeEvent]:
    identifier = _validate_identifier(identifier)
    repository = VesselRepository(db)
    messages = await repository.get_recent_messages(identifier, lookback_hours=72)
    tracker = IdentityTracker()
    identity = await repository.get_identity(messages[0].mmsi) if messages else None
    return tracker.analyse(identity, messages)
