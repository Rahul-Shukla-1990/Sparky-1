from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import get_settings


async def get_database() -> AsyncIOMotorDatabase:
    """Return an AsyncIOMotorDatabase connected using configured settings."""

    settings = get_settings()
    client = AsyncIOMotorClient(settings.mongodb_uri)
    return client[settings.mongodb_database]
