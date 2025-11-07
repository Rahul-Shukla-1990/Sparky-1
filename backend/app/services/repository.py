from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from ..models.ais import AISMessage, VesselIdentity
from ..models.detection import DarkActivityEvent, IdentityChangeEvent


class VesselRepository:
    """Persistence layer for vessel telemetry and analytics artifacts."""

    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._db = database

    async def get_recent_messages(
        self, identifier: str, *, lookback_hours: int = 48
    ) -> list[AISMessage]:
        """Return recent AIS messages for a vessel by MMSI or IMO."""

        query = {
            "$or": [{"mmsi": identifier}, {"imo": identifier}],
            "timestamp": {"$gte": datetime.utcnow() - timedelta(hours=lookback_hours)},
        }
        cursor = (
            self._db.ais_messages.find(query).sort("timestamp", 1)
        )  # type: ignore[attr-defined]
        return [AISMessage(**doc) async for doc in cursor]

    async def upsert_messages(self, messages: Iterable[AISMessage]) -> None:
        """Insert or update AIS messages based on MMSI and timestamp."""

        for message in messages:
            await self._db.ais_messages.update_one(  # type: ignore[attr-defined]
                {"mmsi": message.mmsi, "timestamp": message.timestamp},
                {"$set": message.dict()},
                upsert=True,
            )

    async def save_dark_activity_event(self, event: DarkActivityEvent) -> None:
        await self._db.dark_activity_events.insert_one(event.dict())  # type: ignore[attr-defined]

    async def save_identity_change_event(self, event: IdentityChangeEvent) -> None:
        await self._db.identity_change_events.insert_one(event.dict())  # type: ignore[attr-defined]

    async def get_identity(self, mmsi: str) -> Optional[VesselIdentity]:
        document = await self._db.vessel_identities.find_one({"mmsi": mmsi})  # type: ignore[attr-defined]
        return VesselIdentity(**document) if document else None

    async def upsert_identity(self, identity: VesselIdentity) -> None:
        await self._db.vessel_identities.update_one(  # type: ignore[attr-defined]
            {"mmsi": identity.mmsi},
            {"$set": identity.dict()},
            upsert=True,
        )

    async def list_recent_dark_events(
        self, *, region_bbox: tuple[float, float, float, float], days: int = 1
    ) -> list[DarkActivityEvent]:
        lon_min, lat_min, lon_max, lat_max = region_bbox
        query = {
            "start_timestamp": {"$gte": datetime.utcnow() - timedelta(days=days)},
            "location_start": {
                "$geoWithin": {
                    "$box": [
                        [lon_min, lat_min],
                        [lon_max, lat_max],
                    ]
                }
            },
        }
        cursor = self._db.dark_activity_events.find(query).sort("start_timestamp", -1)  # type: ignore[attr-defined]
        return [DarkActivityEvent(**doc) async for doc in cursor]
