from app.nlp.taxonomy import IOR_REGION_TERMS


# Broad operational belt: Gulf of Guinea to Philippines Sea.
# This is intentionally inclusive for v0.2. v0.3 should replace it with polygon-based AOI.
BROAD_IOR_BOUNDS = {
    "min_lat": -50.0,
    "max_lat": 35.0,
    "min_lon": -25.0,
    "max_lon": 150.0,
}


def coordinate_in_broad_ior(lat: float | None, lon: float | None) -> bool:
    if lat is None or lon is None:
        return False
    return (
        BROAD_IOR_BOUNDS["min_lat"] <= lat <= BROAD_IOR_BOUNDS["max_lat"]
        and BROAD_IOR_BOUNDS["min_lon"] <= lon <= BROAD_IOR_BOUNDS["max_lon"]
    )


def aoi_score(text: str, lat: float | None = None, lon: float | None = None) -> float:
    if coordinate_in_broad_ior(lat, lon):
        return 100.0

    t = (text or "").lower()
    hits = sum(1 for term in IOR_REGION_TERMS if term in t)
    if hits == 0:
        return 0.0
    return min(100.0, 30.0 + hits * 15.0)


def passes_aoi_filter(text: str, lat: float | None = None, lon: float | None = None, threshold: float = 30.0) -> bool:
    return aoi_score(text, lat, lon) >= threshold
