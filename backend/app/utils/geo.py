from __future__ import annotations

import math
from typing import Iterable, Tuple

EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> float:
    """Compute the great-circle distance between two (lat, lon) points."""

    lat1, lon1 = map(math.radians, point_a)
    lat2, lon2 = map(math.radians, point_b)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


def interpolate_points(
    point_a: Tuple[float, float],
    point_b: Tuple[float, float],
    segments: int = 10,
) -> Iterable[Tuple[float, float]]:
    """Yield intermediate points along the rhumb line between two coordinates."""

    lat1, lon1 = point_a
    lat2, lon2 = point_b
    for i in range(segments + 1):
        t = i / segments
        yield (lat1 + (lat2 - lat1) * t, lon1 + (lon2 - lon1) * t)


LAND_BBOXES = [
    # East Africa
    ((-35.0, 28.0, 15.0, 52.0)),
    # Arabian Peninsula
    ((12.0, 34.0, 30.0, 60.0)),
    # Indian mainland including northern territories
    ((5.0, 68.0, 37.5, 98.0)),
    # Western Himalayas (Jammu & Kashmir, Ladakh)
    ((30.5, 73.0, 37.5, 81.5)),
    # Northeastern states
    ((20.0, 92.0, 29.8, 98.5)),
    # Sri Lanka
    ((5.0, 79.0, 10.0, 82.0)),
    # Lakshadweep Islands
    ((8.0, 71.0, 13.8, 74.6)),
    # Andaman & Nicobar Islands
    ((6.0, 92.0, 15.0, 94.8)),
    # Southeast Asia archipelago (coarse approximation)
    ((-10.0, 94.0, 10.0, 142.0)),
    # Australia (northwest coast relevant to Indian Ocean routes)
    ((-35.0, 110.0, -10.0, 130.0)),
]


def _point_is_land(lat: float, lon: float) -> bool:
    for lat_min, lon_min, lat_max, lon_max in LAND_BBOXES:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return True
    return False


def is_water_route(point_a: Tuple[float, float], point_b: Tuple[float, float], samples: int = 25) -> bool:
    """Determine whether the path between two points remains over water.

    The function samples equidistant points on the route and verifies that each
    remains outside a coarse set of land bounding boxes covering the Indian
    Ocean theatre. The approximation is intentionally conservative and suitable
    for feasibility checks when high-precision bathymetry is unavailable.
    """

    for lat, lon in interpolate_points(point_a, point_b, segments=samples):
        if _point_is_land(lat, lon):
            return False
    return True
