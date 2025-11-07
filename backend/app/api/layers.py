from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/layers", tags=["layers"])

STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
try:
    EEZ_DATA = json.loads(
        (STATIC_DIR / "data" / "eez_simplified.geojson").read_text(encoding="utf-8")
    )
except FileNotFoundError:  # pragma: no cover - defensive fallback
    EEZ_DATA = {"type": "FeatureCollection", "features": []}

try:
    MARITIME_ZONES = json.loads(
        (STATIC_DIR / "data" / "maritime_zones_demo.geojson").read_text(encoding="utf-8")
    )
except FileNotFoundError:  # pragma: no cover - defensive fallback
    MARITIME_ZONES = {"type": "FeatureCollection", "features": []}

MARITIME_ZONE_INDEX: dict[str, dict] = {}
for feature in MARITIME_ZONES.get("features", []):
    zone = feature.get("properties", {}).get("zone")
    if not zone:
        continue
    key = zone.lower()
    bucket = MARITIME_ZONE_INDEX.setdefault(key, {"type": "FeatureCollection", "features": []})
    bucket["features"].append(feature)

UNDERSEA_CABLES = [
    {
        "id": "iocc-1",
        "name": {"en": "India-Oman Cable Corridor", "hi": "भारत-ओमान केबल गलियारा"},
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [72.8777, 19.076],
                [58.4059, 23.588],
            ],
        },
    }
]

SHIPPING_LANES = [
    {
        "id": "iocl-1",
        "name": {"en": "Malacca Strait Eastbound", "hi": "मलक्का जलडमरूमध्य पूर्वगामी"},
        "geometry": {
            "type": "LineString",
            "coordinates": [
                [95.0, 5.0],
                [103.0, 1.0],
            ],
        },
    }
]


@router.get("/undersea-cables", response_model=list)
def get_undersea_cables() -> list[dict]:
    return UNDERSEA_CABLES


@router.get("/shipping-lanes", response_model=list)
def get_shipping_lanes() -> list[dict]:
    return SHIPPING_LANES


@router.get("/exclusive-economic-zones", response_model=dict)
def get_exclusive_economic_zones() -> dict:
    """Return a simplified global EEZ FeatureCollection for map overlays."""

    return EEZ_DATA


@router.get("/maritime-zones", response_model=list[str])
def list_maritime_zones() -> list[str]:
    """List the maritime legal layers available in the demo dataset."""

    return sorted(MARITIME_ZONE_INDEX)


@router.get("/maritime-zones/{zone_key}", response_model=dict)
def get_maritime_zone(zone_key: str) -> dict:
    """Return the feature collection associated with a maritime zone."""

    key = zone_key.replace("-", "_").lower()
    if key not in MARITIME_ZONE_INDEX:
        raise HTTPException(status_code=404, detail="Maritime zone not available")
    return MARITIME_ZONE_INDEX[key]
