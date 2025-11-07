from __future__ import annotations

from functools import lru_cache
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application configuration values.

    Values can be overridden via environment variables. The defaults target
    local development with optional fallbacks to mocked data sources.
    """

    app_name: str = Field(default="Sparky Maritime Intelligence Platform")
    mongodb_uri: str = Field(default="mongodb://localhost:27017")
    mongodb_database: str = Field(default="sparky_maritime")
    external_feed_refresh_minutes: int = Field(default=15)
    indian_ocean_bbox: tuple[float, float, float, float] = Field(
        default=(20.0, -60.0, 120.0, 40.0),
        description="Bounding box (lon_min, lat_min, lon_max, lat_max) for the Indian Ocean Region",
    )
    history_years: int = Field(default=20, description="Years of historical AIS data to retain")

    class Config:
        env_prefix = "SPARKY_"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
