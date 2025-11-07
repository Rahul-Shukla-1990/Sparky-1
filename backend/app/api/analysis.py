from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from ..config import get_settings
from ..dependencies import get_database
from ..services.dark_activity import DarkActivitySummariser
from ..services.repository import VesselRepository

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/daily", response_model=dict)
async def daily_indian_ocean_summary(
    days: int = 1,
    db=Depends(get_database),
) -> dict:
    settings = get_settings()
    repository = VesselRepository(db)
    events = await repository.list_recent_dark_events(
        region_bbox=settings.indian_ocean_bbox, days=days
    )
    summariser = DarkActivitySummariser()
    stats = summariser.summarise(events)
    stats["region"] = "Indian Ocean"
    stats["as_of"] = datetime.utcnow()
    return stats
