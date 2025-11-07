"""Lightweight offline demo server for the maritime intelligence backend.

This module mirrors the behaviour of the FastAPI application using nothing but
Python's standard library so that we can run a functional demonstration inside
restricted execution environments. The endpoints return realistic sample data
covering vessel summaries, dark-activity analytics, bilingual map layers, and a
websocket stream for live situational awareness overlays.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import random
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qs, urlparse

from .utils.geo import haversine_distance_km, is_water_route

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
STATIC_DIR = Path(__file__).with_name("static")
INDEX_HTML = (STATIC_DIR / "index.html").read_bytes()
try:
    INDIA_OUTLINE = json.loads((STATIC_DIR / "data" / "india_outline.geojson").read_text(encoding="utf-8"))
except FileNotFoundError:  # pragma: no cover - defensive fallback
    INDIA_OUTLINE = {"type": "FeatureCollection", "features": []}
try:
    EEZ_GLOBAL = json.loads((STATIC_DIR / "data" / "eez_simplified.geojson").read_text(encoding="utf-8"))
except FileNotFoundError:  # pragma: no cover - defensive fallback
    EEZ_GLOBAL = {"type": "FeatureCollection", "features": []}
try:
    MARITIME_ZONES = json.loads(
        (STATIC_DIR / "data" / "maritime_zones_demo.geojson").read_text(encoding="utf-8")
    )
except FileNotFoundError:  # pragma: no cover - defensive fallback
    MARITIME_ZONES = {"type": "FeatureCollection", "features": []}

MARITIME_ZONE_INDEX: Dict[str, Dict[str, object]] = {}
for feature in MARITIME_ZONES.get("features", []):
    zone = feature.get("properties", {}).get("zone")
    if not zone:
        continue
    key = zone.lower()
    bucket = MARITIME_ZONE_INDEX.setdefault(key, {"type": "FeatureCollection", "features": []})
    bucket["features"].append(feature)
WEBSOCKET_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
STREAM_INTERVAL_SECONDS = 1.0
REGION_BOUNDS = {
    "lat_min": -35.0,
    "lat_max": 28.0,
    "lon_min": 30.0,
    "lon_max": 110.0,
}


@dataclass
class IdentitySnapshot:
    timestamp: datetime
    mmsi: str
    imo: Optional[str]
    name: str
    call_sign: str
    flag: str
    vessel_type: str
    length_m: float
    beam_m: float
    draught_m: float
    build_year: int


@dataclass
class AISMessage:
    mmsi: str
    imo: Optional[str]
    timestamp: datetime
    latitude: float
    longitude: float
    sog: float
    cog: float
    heading: Optional[float]
    vessel_name: str
    nav_status: str
    source: str = "demo"


@dataclass
class DarkActivityEvent:
    mmsi: str
    start_timestamp: datetime
    end_timestamp: datetime
    gap_minutes: float
    estimated_distance_km: float
    observed_distance_km: float
    location_start: tuple[float, float]
    location_end: tuple[float, float]
    confidence: float
    notes: Optional[str]


@dataclass
class IdentityChangeEvent:
    mmsi: str
    timestamp: datetime
    field: str
    previous: str
    current: str


@dataclass
class VesselRecord:
    mmsi: str
    imo: str
    track: List[AISMessage]
    identities: List[IdentitySnapshot]

    @property
    def current_identity(self) -> IdentitySnapshot:
        return sorted(self.identities, key=lambda snap: snap.timestamp)[-1]


def _json_default(value):
    if isinstance(value, datetime):
        return value.strftime(ISO_FORMAT)
    if hasattr(value, "_asdict"):
        return value._asdict()
    raise TypeError(f"Type {type(value)!r} is not JSON serialisable")


def _random_route_segment(lat: float, lon: float) -> tuple[float, float]:
    """Generate a small step that remains within an Indian Ocean envelope."""

    for _ in range(10):
        delta_lat = random.uniform(-1.5, 1.5)
        delta_lon = random.uniform(-1.5, 1.5)
        candidate = (lat + delta_lat, lon + delta_lon)
        if is_water_route((lat, lon), candidate, samples=8):
            return candidate
    return lat, lon


def _generate_identity(mmsi: str, seed: int, timestamp: datetime) -> IdentitySnapshot:
    random.seed(seed)
    names = [
        "Sagar",
        "Nautilus",
        "Varuna",
        "Aranya",
        "Pravah",
        "Anahita",
        "Samudra",
        "Ganga",
        "Yamuna",
        "Sindhu",
    ]
    flags = ["IN", "LK", "OM", "AE", "TZ", "ZA"]
    types = ["Tanker", "Cargo", "Fishing", "Research", "Supply"]
    return IdentitySnapshot(
        timestamp=timestamp,
        mmsi=mmsi,
        imo=f"IMO{7000000 + seed:07d}",
        name=f"{random.choice(names)} {seed}",
        call_sign=f"{random.choice(['VT', 'VU', 'A4', '9V'])}{seed:03d}",
        flag=random.choice(flags),
        vessel_type=random.choice(types),
        length_m=round(random.uniform(95.0, 280.0), 1),
        beam_m=round(random.uniform(16.0, 48.0), 1),
        draught_m=round(random.uniform(6.5, 14.5), 1),
        build_year=random.randint(1994, 2020),
    )


def _maybe_mutate_identity(identity: IdentitySnapshot, timestamp: datetime, seed: int) -> IdentitySnapshot:
    random.seed(seed + 99)
    if random.random() < 0.2:
        # introduce a rename to showcase identity tracking
        new_name = identity.name + " II"
        return IdentitySnapshot(
            timestamp=timestamp,
            mmsi=identity.mmsi,
            imo=identity.imo,
            name=new_name,
            call_sign=identity.call_sign,
            flag=identity.flag,
            vessel_type=identity.vessel_type,
            length_m=identity.length_m,
            beam_m=identity.beam_m,
            draught_m=identity.draught_m,
            build_year=identity.build_year,
        )
    return identity


def _generate_track(mmsi: str, identity: IdentitySnapshot, *, points: int = 60) -> List[AISMessage]:
    random.seed(int(mmsi[-4:]))
    base_time = datetime.utcnow() - timedelta(hours=points)
    lat = random.uniform(-10.0, 15.0)
    lon = random.uniform(45.0, 85.0)

    track: List[AISMessage] = []
    timestamp = base_time
    for idx in range(points):
        if idx and idx % 12 == 0:
            # insert a blackout gap every 12 samples (~3 hours)
            timestamp += timedelta(hours=random.uniform(3.5, 9.0))
        else:
            timestamp += timedelta(minutes=30)

        next_lat, next_lon = _random_route_segment(lat, lon)
        sog = random.uniform(8.0, 16.0)
        cog = random.uniform(0.0, 359.0)
        nav_status = random.choice([
            "under_way_using_engine",
            "restricted_manoeuvrability",
            "engaged_in_fishing",
        ])

        track.append(
            AISMessage(
                mmsi=mmsi,
                imo=identity.imo,
                timestamp=timestamp,
                latitude=next_lat,
                longitude=next_lon,
                sog=sog,
                cog=cog,
                heading=None,
                vessel_name=identity.name,
                nav_status=nav_status,
            )
        )
        lat, lon = next_lat, next_lon
    return track


def build_dataset(count: int = 50) -> Dict[str, VesselRecord]:
    dataset: Dict[str, VesselRecord] = {}
    for idx in range(count):
        mmsi = f"{500000000 + idx:09d}"
        identity = _generate_identity(mmsi, idx, datetime.utcnow() - timedelta(days=14))
        identity_mutated = _maybe_mutate_identity(identity, datetime.utcnow() - timedelta(days=2), idx)
        identities = [identity]
        if identity_mutated is not identity:
            identities.append(identity_mutated)
        track = _generate_track(mmsi, identity_mutated)
        dataset[mmsi] = VesselRecord(mmsi=mmsi, imo=identity.imo or "", track=track, identities=identities)
    return dataset


DATASET = build_dataset()
IMO_TO_MMSI = {record.imo: record.mmsi for record in DATASET.values() if record.imo}


def detect_dark_activity(track: Iterable[AISMessage]) -> List[DarkActivityEvent]:
    messages = list(track)
    events: List[DarkActivityEvent] = []
    for previous, current in zip(messages, messages[1:]):
        gap_minutes = (current.timestamp - previous.timestamp).total_seconds() / 60.0
        if gap_minutes < 30.0:
            continue

        observed = haversine_distance_km(
            (previous.latitude, previous.longitude),
            (current.latitude, current.longitude),
        )
        estimated = ((previous.sog or 0.0) * 1.852 + 10.0) * (gap_minutes / 60.0)
        water_only = is_water_route(
            (previous.latitude, previous.longitude),
            (current.latitude, current.longitude),
        )
        notes = None
        confidence = min(1.0, observed / (estimated * 1.5)) if estimated else 0.0
        if not water_only:
            notes = "Route intersects land, possible spoofing"
            confidence = 1.0
        if observed > estimated * 1.5 or not water_only:
            events.append(
                DarkActivityEvent(
                    mmsi=current.mmsi,
                    start_timestamp=previous.timestamp,
                    end_timestamp=current.timestamp,
                    gap_minutes=gap_minutes,
                    estimated_distance_km=estimated,
                    observed_distance_km=observed,
                    location_start=(previous.latitude, previous.longitude),
                    location_end=(current.latitude, current.longitude),
                    confidence=confidence,
                    notes=notes,
                )
            )
    return events


def detect_identity_events(record: VesselRecord) -> List[IdentityChangeEvent]:
    snapshots = sorted(record.identities, key=lambda snap: snap.timestamp)
    events: List[IdentityChangeEvent] = []
    for prev, cur in zip(snapshots, snapshots[1:]):
        if prev.name != cur.name:
            events.append(
                IdentityChangeEvent(
                    mmsi=record.mmsi,
                    timestamp=cur.timestamp,
                    field="name",
                    previous=prev.name,
                    current=cur.name,
                )
            )
        if prev.call_sign != cur.call_sign:
            events.append(
                IdentityChangeEvent(
                    mmsi=record.mmsi,
                    timestamp=cur.timestamp,
                    field="call_sign",
                    previous=prev.call_sign,
                    current=cur.call_sign,
                )
            )
    return events


def _serialise_message(message: AISMessage) -> Dict[str, object]:
    payload = asdict(message)
    payload["timestamp"] = message.timestamp.strftime(ISO_FORMAT)
    return payload


def _serialise_identity(identity: IdentitySnapshot) -> Dict[str, object]:
    payload = asdict(identity)
    payload["timestamp"] = identity.timestamp.strftime(ISO_FORMAT)
    return payload


def _serialise_dark_event(event: DarkActivityEvent) -> Dict[str, object]:
    payload = asdict(event)
    payload["start_timestamp"] = event.start_timestamp.strftime(ISO_FORMAT)
    payload["end_timestamp"] = event.end_timestamp.strftime(ISO_FORMAT)
    payload["location_start"] = list(event.location_start)
    payload["location_end"] = list(event.location_end)
    return payload


def _serialise_identity_event(event: IdentityChangeEvent) -> Dict[str, object]:
    payload = asdict(event)
    payload["timestamp"] = event.timestamp.strftime(ISO_FORMAT)
    return payload


def _find_record(identifier: str) -> VesselRecord:
    if identifier in DATASET:
        return DATASET[identifier]
    if identifier in IMO_TO_MMSI:
        return DATASET[IMO_TO_MMSI[identifier]]
    raise KeyError(identifier)


def _identity_integrity_score(record: VesselRecord) -> int:
    penalties = len(detect_identity_events(record)) * 12
    score = max(45, 100 - penalties)
    return score


def _daily_dark_activity_summary() -> Dict[str, object]:
    events = [event for record in DATASET.values() for event in detect_dark_activity(record.track)]
    if not events:
        return {
            "total_events": 0,
            "high_confidence_events": 0,
            "average_gap_minutes": 0.0,
            "top_hotspots": [],
        }
    total = len(events)
    high = sum(1 for event in events if event.confidence >= 0.75)
    avg_gap = sum(event.gap_minutes for event in events) / total
    hotspots = sorted(
        (
            {
                "latitude": event.location_end[0],
                "longitude": event.location_end[1],
                "confidence": round(event.confidence, 2),
            }
            for event in events
        ),
        key=lambda item: item["confidence"],
        reverse=True,
    )[:5]
    return {
        "total_events": total,
        "high_confidence_events": high,
        "average_gap_minutes": round(avg_gap, 2),
        "top_hotspots": hotspots,
    }


def _layers_payload() -> Dict[str, list]:
    cables = [
        {
            "name": {"en": "SEA-ME-WE 5", "hi": "सी-मि-वी 5"},
            "coordinates": [[11.0, 79.0], [15.0, 65.0], [20.0, 55.0]],
        },
        {
            "name": {"en": "i2i Cable", "hi": "आई2आई केबल"},
            "coordinates": [[13.0, 80.0], [2.0, 103.0]],
        },
    ]
    shipping_lanes = [
        {
            "name": {"en": "Hormuz to Mumbai", "hi": "हॉर्मुज़ से मुंबई"},
            "coordinates": [[25.5, 56.5], [19.0, 72.8]],
        },
        {
            "name": {"en": "Cape Route", "hi": "केप मार्ग"},
            "coordinates": [[-34.0, 18.0], [11.0, 43.0], [7.0, 80.0]],
        },
    ]
    chokepoints = [
        {
            "name": {"en": "Malacca Strait", "hi": "मलक्का जलडमरूमध्य"},
            "coordinates": [[1.2, 103.5]],
        },
        {
            "name": {"en": "Bab-el-Mandeb", "hi": "बाब एल-मंदेब"},
            "coordinates": [[12.6, 43.4]],
        },
    ]
    ports = [
        {
            "name": {"en": "Mumbai", "hi": "मुंबई"},
            "coordinates": [18.955, 72.835],
        },
        {
            "name": {"en": "Chennai", "hi": "चेन्नई"},
            "coordinates": [13.0827, 80.2707],
        },
        {
            "name": {"en": "Colombo", "hi": "कोलंबो"},
            "coordinates": [6.9271, 79.8612],
        },
    ]
    slocs = [
        {
            "name": {"en": "Strait of Hormuz", "hi": "हॉर्मुज़ जलडमरूमध्य"},
            "coordinates": [[26.0, 56.2], [25.8, 57.1]],
        },
        {
            "name": {"en": "Lombok Corridor", "hi": "लोम्बोक मार्ग"},
            "coordinates": [[-8.5, 115.9], [-9.5, 116.5]],
        },
    ]
    aoi_templates = [
        {
            "name": {"en": "Gulf of Oman", "hi": "ओमान की खाड़ी"},
            "coordinates": [[24.7, 56.0], [24.1, 59.3], [23.0, 58.7], [23.6, 55.9]],
        },
        {
            "name": {"en": "Lakshadweep Sea", "hi": "लक्षद्वीप सागर"},
            "coordinates": [[12.5, 71.0], [10.0, 74.5], [11.5, 76.5], [13.8, 73.2]],
        },
    ]
    heatmap_cells = [
        {
            "coordinates": [random.uniform(45.0, 85.0), random.uniform(-10.0, 20.0)],
            "intensity": round(random.uniform(0.3, 0.95), 2),
        }
        for _ in range(30)
    ]
    return {
        "undersea_cables": cables,
        "major_shipping_lanes": shipping_lanes,
        "strategic_chokepoints": chokepoints,
        "ports_and_anchorages": ports,
        "slocs": slocs,
        "aoi_templates": aoi_templates,
        "daily_ior_heatmap": heatmap_cells,
        "india_outline": INDIA_OUTLINE,
        "exclusive_economic_zones": EEZ_GLOBAL,
        "maritime_zones": MARITIME_ZONE_INDEX,
    }


class WebSocketConnection:
    def __init__(self, sock):
        self._socket = sock
        self._lock = threading.Lock()
        self._closed = False
        self._socket.settimeout(2.0)

    def send_text(self, message: str) -> None:
        if self._closed:
            raise ConnectionError("WebSocket is closed")
        payload = message.encode("utf-8")
        header = bytearray([0x81])  # FIN + text frame
        length = len(payload)
        if length < 126:
            header.append(length)
        elif length < (1 << 16):
            header.append(126)
            header.extend(length.to_bytes(2, "big"))
        else:
            header.append(127)
            header.extend(length.to_bytes(8, "big"))
        with self._lock:
            try:
                self._socket.sendall(header + payload)
            except OSError as exc:  # pragma: no cover - depends on client connection
                self._closed = True
                raise ConnectionError(str(exc)) from exc

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._socket.sendall(b"\x88\x00")
        except OSError:
            pass
        finally:
            self._closed = True
            try:
                self._socket.close()
            except OSError:
                pass


def _initialise_live_state() -> Dict[str, Dict[str, object]]:
    state: Dict[str, Dict[str, object]] = {}
    for record in DATASET.values():
        latest = record.track[-1]
        identity = record.current_identity
        state[record.mmsi] = {
            "mmsi": record.mmsi,
            "imo": identity.imo,
            "name": identity.name,
            "latitude": latest.latitude,
            "longitude": latest.longitude,
            "sog": max(6.0, min(latest.sog, 18.0)),
            "cog": latest.cog,
            "flag": identity.flag,
            "vessel_type": identity.vessel_type,
            "status": "on",
            "silence_timer": random.randint(25, 90),
            "silent_for": 0,
        }
    return state


LIVE_STATE = _initialise_live_state()
STATE_LOCK = threading.Lock()
SAR_DETECTIONS: List[Dict[str, object]] = []
ALERT_BUFFER: List[Dict[str, object]] = []


def _advance_position(state: Dict[str, object], dt_seconds: float) -> None:
    sog = state.get("sog", 12.0)
    sog += random.uniform(-0.4, 0.4)
    sog = max(4.5, min(19.5, sog))
    cog = (state.get("cog", 0.0) + random.uniform(-3.0, 3.0)) % 360
    state["sog"] = sog
    state["cog"] = cog

    distance_km = sog * 1.852 * (dt_seconds / 3600.0)
    bearing = math.radians(cog)
    lat = state.get("latitude", 0.0)
    lon = state.get("longitude", 0.0)
    delta_lat = (distance_km / 111.32) * math.cos(bearing)
    delta_lon = (distance_km / (111.32 * max(0.2, math.cos(math.radians(lat))))) * math.sin(bearing)
    lat = max(REGION_BOUNDS["lat_min"], min(REGION_BOUNDS["lat_max"], lat + delta_lat))
    lon = max(REGION_BOUNDS["lon_min"], min(REGION_BOUNDS["lon_max"], lon + delta_lon))

    if not is_water_route((state["latitude"], state["longitude"]), (lat, lon)):
        # bounce off land by reversing heading
        cog = (cog + 180.0) % 360
        state["cog"] = cog
        lat = state["latitude"]
        lon = state["longitude"]

    state["latitude"] = lat
    state["longitude"] = lon


def _maybe_toggle_silence(state: Dict[str, object], now: datetime) -> Optional[Dict[str, object]]:
    state["silence_timer"] = max(0, state.get("silence_timer", 0) - STREAM_INTERVAL_SECONDS)
    alert: Optional[Dict[str, object]] = None
    if state["status"] == "silent":
        state["silent_for"] += STREAM_INTERVAL_SECONDS
        if state["silent_for"] >= state.get("resume_after", 30):
            state["status"] = "on"
            state["silence_timer"] = random.randint(60, 180)
            state["silent_for"] = 0
    elif state["silence_timer"] <= 0 and random.random() < 0.08:
        state["status"] = "silent"
        state["silent_for"] = 0
        state["resume_after"] = random.randint(25, 90)
        alert = {
            "type": "ais-silence",
            "mmsi": state["mmsi"],
            "name": state.get("name"),
            "severity": random.choice(["medium", "high"]),
            "message": f"AIS gap detected for vessel {state.get('name')} ({state['mmsi']}).",
            "timestamp": datetime.utcnow().strftime(ISO_FORMAT),
        }
    return alert


def _snapshot_state() -> List[Dict[str, object]]:
    with STATE_LOCK:
        return [
            {
                "mmsi": state["mmsi"],
                "imo": state.get("imo"),
                "name": state.get("name"),
                "latitude": round(state["latitude"], 5),
                "longitude": round(state["longitude"], 5),
                "sog": round(state["sog"], 2),
                "cog": round(state["cog"], 2),
                "status": state.get("status", "on"),
                "flag": state.get("flag"),
                "vessel_type": state.get("vessel_type"),
            }
            for state in LIVE_STATE.values()
        ]


def _update_live_state(now: datetime) -> List[Dict[str, object]]:
    new_alerts: List[Dict[str, object]] = []
    with STATE_LOCK:
        for state in LIVE_STATE.values():
            _advance_position(state, STREAM_INTERVAL_SECONDS)
            alert = _maybe_toggle_silence(state, now)
            if alert:
                new_alerts.append(alert)
    return new_alerts


def _generate_sar_hit(now: datetime) -> Optional[Dict[str, object]]:
    if random.random() > 0.18:
        return None
    lat = random.uniform(-5.0, 20.0)
    lon = random.uniform(45.0, 85.0)
    hit = {
        "id": f"sar-{int(now.timestamp())}-{random.randint(10, 999)}",
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "confidence": round(random.uniform(0.55, 0.95), 2),
        "timestamp": now,
    }
    return hit


def _serialise_sar_hit(hit: Dict[str, object]) -> Dict[str, object]:
    return {
        "id": hit["id"],
        "latitude": hit["latitude"],
        "longitude": hit["longitude"],
        "confidence": hit["confidence"],
        "timestamp": hit["timestamp"].strftime(ISO_FORMAT),
    }


def _refresh_sar_hits(now: datetime) -> List[Dict[str, object]]:
    new_hit = _generate_sar_hit(now)
    if new_hit:
        SAR_DETECTIONS.append(new_hit)
        ALERT_BUFFER.append(
            {
                "type": "sar",
                "severity": random.choice(["medium", "high"]),
                "message": "SAR contact without AIS correlation detected.",
                "timestamp": now.strftime(ISO_FORMAT),
            }
        )
    window = now - timedelta(seconds=18)
    while SAR_DETECTIONS and SAR_DETECTIONS[0]["timestamp"] < window:
        SAR_DETECTIONS.pop(0)
    return [_serialise_sar_hit(hit) for hit in SAR_DETECTIONS]


def _append_alerts(new_alerts: List[Dict[str, object]]) -> None:
    if not new_alerts:
        return
    ALERT_BUFFER.extend(new_alerts)
    del ALERT_BUFFER[:-40]


def dataset_summary() -> List[Dict[str, object]]:
    summaries: List[Dict[str, object]] = []
    with STATE_LOCK:
        for record in sorted(DATASET.values(), key=lambda rec: rec.mmsi):
            state = LIVE_STATE.get(record.mmsi)
            latest = record.track[-1]
            identity = record.current_identity
            summaries.append(
                {
                    "mmsi": record.mmsi,
                    "imo": identity.imo,
                    "name": identity.name,
                    "flag": identity.flag,
                    "latest_timestamp": latest.timestamp.strftime(ISO_FORMAT),
                    "latitude": state["latitude"] if state else latest.latitude,
                    "longitude": state["longitude"] if state else latest.longitude,
                    "status": state.get("status", "on") if state else "on",
                    "identity_integrity": _identity_integrity_score(record),
                }
            )
    return summaries


def _build_vessel_detail(record: VesselRecord) -> Dict[str, object]:
    track = record.track[-48:]
    identity = record.current_identity
    with STATE_LOCK:
        live_state = LIVE_STATE.get(record.mmsi)
    return {
        "identifier": record.mmsi,
        "latest_message": _serialise_message(track[-1]),
        "identity": _serialise_identity(identity),
        "dark_events": [_serialise_dark_event(event) for event in detect_dark_activity(track)],
        "identity_events": [_serialise_identity_event(event) for event in detect_identity_events(record)],
        "metrics": {
            "identity_integrity": _identity_integrity_score(record),
            "dark_activity_events": len(detect_dark_activity(track)),
        },
        "live_state": live_state,
    }


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "MaritimeDemo/2.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003 - signature fixed by BaseHTTPRequestHandler
        return

    def _send_response(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, default=_json_default).encode("utf-8")
        self._send_response(body, "application/json", status=status)

    def _send_html(self, body: bytes, status: int = 200) -> None:
        self._send_response(body, "text/html; charset=utf-8", status=status)

    def _handle_websocket(self, segments: List[str]) -> None:
        if segments[:2] != ["ws", "ais"]:
            self.send_error(404, "WebSocket endpoint not found")
            return
        key = self.headers.get("Sec-WebSocket-Key")
        if not key:
            self.send_error(400, "Missing Sec-WebSocket-Key header")
            return
        accept = base64.b64encode(hashlib.sha1((key + WEBSOCKET_GUID).encode()).digest()).decode()
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()

        connection = WebSocketConnection(self.connection)
        try:
            while True:
                now = datetime.utcnow()
                new_alerts = _update_live_state(now)
                sar_hits = _refresh_sar_hits(now)
                _append_alerts(new_alerts)
                payload = {
                    "type": "ais_snapshot",
                    "timestamp": now.strftime(ISO_FORMAT),
                    "vessels": _snapshot_state(),
                    "sar_hits": sar_hits,
                    "alerts": ALERT_BUFFER[-12:],
                }
                connection.send_text(json.dumps(payload))
                time.sleep(STREAM_INTERVAL_SECONDS)
        except ConnectionError:
            connection.close()
        finally:
            self.close_connection = True

    def do_GET(self) -> None:  # noqa: N802 - method signature defined by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        segments = [segment for segment in parsed.path.split("/") if segment]
        query = parse_qs(parsed.query or "")

        if self.headers.get("Upgrade", "").lower() == "websocket":
            self._handle_websocket(segments)
            return

        try:
            if not segments:
                self._send_html(INDEX_HTML)
                return

            if segments[0] == "health":
                self._send_json({"status": "ok", "dataset_vessels": len(DATASET)})
                return

            if segments[0] == "vessels":
                if len(segments) == 1:
                    self._send_json(dataset_summary())
                    return
                identifier = segments[1]
                record = _find_record(identifier)

                if len(segments) == 2:
                    self._send_json(_build_vessel_detail(record))
                    return

                action = segments[2]
                lookback_hours = int(query.get("lookback_hours", [24])[0])
                cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
                track = [message for message in record.track if message.timestamp >= cutoff]
                if not track:
                    track = record.track[-1:]

                if action == "track":
                    self._send_json([_serialise_message(msg) for msg in track])
                    return
                if action == "dark-activity":
                    self._send_json([_serialise_dark_event(event) for event in detect_dark_activity(track)])
                    return
                if action == "identity-events":
                    self._send_json([_serialise_identity_event(event) for event in detect_identity_events(record)])
                    return
                self._send_json({"error": "Unsupported action"}, status=404)
                return

            if segments[0] == "analysis" and segments[1:] == ["indian-ocean"]:
                self._send_json(
                    {
                        "region": "Indian Ocean",
                        "summary": _daily_dark_activity_summary(),
                        "generated_at": datetime.utcnow().strftime(ISO_FORMAT),
                    }
                )
                return

            if segments[0] == "layers":
                payload = _layers_payload()
                if len(segments) == 1:
                    self._send_json({"available_layers": list(payload)})
                    return
                if segments[1] == "maritime-zones":
                    zone_payload = payload.get("maritime_zones", {})
                    if len(segments) == 2:
                        self._send_json({"available_zones": sorted(zone_payload)})
                        return
                    zone_key = segments[2].replace("-", "_") if len(segments) > 2 else ""
                    if zone_key not in zone_payload:
                        self._send_json({"error": "Maritime zone not found"}, status=404)
                        return
                    self._send_json(zone_payload[zone_key])
                    return
                key = segments[1].replace("-", "_")
                if key not in payload:
                    self._send_json({"error": "Layer not found"}, status=404)
                    return
                self._send_json(payload[key])
                return

            self._send_json({"error": "Not found"}, status=404)
        except KeyError:
            self._send_json({"error": "Vessel not found"}, status=404)
        except Exception as exc:  # pragma: no cover - defensive logging
            self._send_json({"error": str(exc)}, status=500)


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print(f"Maritime demo server running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down demo server...")
    finally:
        server.server_close()


if __name__ == "__main__":
    serve()
