import hashlib
import re
from datetime import timezone
from dateutil import parser as date_parser


def make_incident_uid(title: str, url: str, category: str) -> str:
    base = f"{title}|{url}|{category}".encode("utf-8", errors="ignore")
    return "IOR-" + hashlib.sha256(base).hexdigest()[:16].upper()


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://\S+", text or "")


def extract_date(text: str):
    if not text:
        return None

    candidates = re.findall(
        r"\b(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|"
        r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})\b",
        text,
        flags=re.IGNORECASE,
    )
    for c in candidates[:3]:
        try:
            dt = date_parser.parse(c)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            continue
    return None


def extract_coordinates(text: str):
    if not text:
        return None, None

    match = re.search(r"(-?\d{1,2}\.\d+)\s*[, ]\s*(-?\d{1,3}\.\d+)", text)
    if match:
        lat = float(match.group(1))
        lon = float(match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon

    # Compact maritime position examples such as 12.34N 045.67E
    match = re.search(r"(\d{1,2}\.\d+)\s*([NS])\s+(\d{1,3}\.\d+)\s*([EW])", text, re.IGNORECASE)
    if match:
        lat = float(match.group(1)) * (1 if match.group(2).upper() == "N" else -1)
        lon = float(match.group(3)) * (1 if match.group(4).upper() == "E" else -1)
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon

    return None, None


def extract_vessel_identifiers(text: str):
    vessel_name = None
    imo = None
    mmsi = None

    imo_match = re.search(r"\bIMO\s*[:#-]?\s*(\d{7})\b", text or "", re.IGNORECASE)
    if imo_match:
        imo = imo_match.group(1)

    mmsi_match = re.search(r"\bMMSI\s*[:#-]?\s*(\d{9})\b", text or "", re.IGNORECASE)
    if mmsi_match:
        mmsi = mmsi_match.group(1)

    vessel_match = re.search(r"\b(?:MV|MT|FV|M/V|M/T|F/V)\s+([A-Z0-9][A-Z0-9\-\s]{2,40})\b", text or "")
    if vessel_match:
        vessel_name = vessel_match.group(0).strip()

    return vessel_name, imo, mmsi
