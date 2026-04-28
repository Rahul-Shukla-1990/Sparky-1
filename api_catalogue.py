import re
from datetime import datetime, timezone
from typing import Iterable
import requests
from sqlalchemy.orm import Session
from app.models import ApiCandidate, Source


PUBLIC_APIS_README_RAW = "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"

RELEVANT_CATEGORIES = {
    "News": 70,
    "Government": 65,
    "Open Data": 65,
    "Security": 55,
    "Transportation": 80,
    "Weather": 55,
    "Geocoding": 60,
    "Environment": 60,
    "Tracking": 65,
}

MARITIME_TERMS = [
    "maritime", "ship", "vessel", "ais", "marine", "ocean", "weather",
    "transport", "tracking", "news", "security", "government", "open data",
    "environment", "geocoding", "pollution", "fish", "fishing", "port"
]


def score_api(category: str | None, name: str, description: str) -> float:
    score = float(RELEVANT_CATEGORIES.get(category or "", 15))
    text = f"{name} {description} {category}".lower()
    hits = sum(1 for term in MARITIME_TERMS if term in text)
    score += min(30, hits * 6)
    return min(100.0, score)


def parse_public_apis_markdown(markdown: str) -> list[dict]:
    current_category = None
    rows: list[dict] = []

    for line in markdown.splitlines():
        stripped = line.strip()

        if stripped.startswith("### "):
            current_category = stripped.replace("###", "", 1).strip()
            continue

        if not current_category or not stripped.startswith("|"):
            continue

        # Skip table headers and separators.
        if "API" in stripped and "Description" in stripped and "Auth" in stripped:
            continue
        if set(stripped.replace("|", "").strip()) <= {"-", ":", " "}:
            continue

        parts = [p.strip() for p in stripped.strip("|").split("|")]
        if len(parts) < 5:
            continue

        api_cell, description, auth, https, cors = parts[:5]
        name_match = re.search(r"\[([^\]]+)\]\(([^\)]+)\)", api_cell)
        if name_match:
            name = name_match.group(1).strip()
            url = name_match.group(2).strip()
        else:
            name = re.sub(r"[*_`]", "", api_cell).strip()
            url = None

        if not name or name.lower() == "api":
            continue

        rows.append({
            "name": name,
            "description": re.sub(r"<[^>]+>", "", description).strip(),
            "category": current_category,
            "auth": auth.replace("`", "").strip(),
            "https": https.strip(),
            "cors": cors.strip(),
            "url": url,
        })

    return rows


def fetch_public_apis_catalogue() -> list[dict]:
    response = requests.get(PUBLIC_APIS_README_RAW, timeout=45)
    response.raise_for_status()
    return parse_public_apis_markdown(response.text)


def seed_fallback_catalogue() -> list[dict]:
    return [
        {"name": "GDELT", "description": "Global news and events open data useful for maritime incident discovery", "category": "News", "auth": "No", "https": "Yes", "cors": "Unknown", "url": "https://www.gdeltproject.org/"},
        {"name": "Nominatim", "description": "OpenStreetMap geocoding API for converting place names to coordinates", "category": "Geocoding", "auth": "No", "https": "Yes", "cors": "Yes", "url": "https://nominatim.openstreetmap.org/"},
        {"name": "Open-Meteo", "description": "Free weather forecast API for meteorological context", "category": "Weather", "auth": "No", "https": "Yes", "cors": "Yes", "url": "https://open-meteo.com/"},
        {"name": "Data.gov", "description": "US government open data catalogue", "category": "Government", "auth": "No", "https": "Yes", "cors": "Unknown", "url": "https://data.gov/"},
        {"name": "Open Government India", "description": "Indian government open data portal", "category": "Government", "auth": "apiKey", "https": "Yes", "cors": "Unknown", "url": "https://data.gov.in/"},
        {"name": "AIS Hub", "description": "AIS related vessel data catalogue entry requiring careful evaluation", "category": "Transportation", "auth": "apiKey", "https": "No", "cors": "Unknown", "url": "http://www.aishub.net/"},
    ]


def import_candidates(db: Session, rows: Iterable[dict], minimum_score: float = 45.0) -> dict:
    imported = 0
    updated = 0
    skipped = 0

    for row in rows:
        category = row.get("category")
        name = row.get("name", "").strip()
        description = row.get("description", "").strip()
        if not name:
            skipped += 1
            continue

        score = score_api(category, name, description)
        if score < minimum_score:
            skipped += 1
            continue

        auth = row.get("auth") or ""
        requires_key = auth.lower() not in {"", "no", "none", "unknown"}

        existing = db.query(ApiCandidate).filter(
            ApiCandidate.name == name,
            ApiCandidate.category == category
        ).first()

        if existing:
            existing.description = description
            existing.auth = auth
            existing.https = row.get("https")
            existing.cors = row.get("cors")
            existing.url = row.get("url")
            existing.maritime_relevance_score = score
            existing.requires_key = requires_key
            existing.updated_at = datetime.now(timezone.utc)
            updated += 1
        else:
            db.add(ApiCandidate(
                name=name,
                description=description,
                category=category,
                auth=auth,
                https=row.get("https"),
                cors=row.get("cors"),
                url=row.get("url"),
                maritime_relevance_score=score,
                requires_key=requires_key,
                free_assumption=True,
                approval_status="Candidate",
            ))
            imported += 1

    db.commit()
    return {"imported": imported, "updated": updated, "skipped": skipped}


def import_from_public_apis(db: Session) -> dict:
    try:
        rows = fetch_public_apis_catalogue()
        result = import_candidates(db, rows)
        result["source"] = "public-apis/public-apis"
        result["mode"] = "live_fetch"
        return result
    except Exception as exc:
        rows = seed_fallback_catalogue()
        result = import_candidates(db, rows, minimum_score=0)
        result["source"] = "fallback_seed"
        result["mode"] = "fallback"
        result["error"] = str(exc)
        return result


def approve_candidate_as_source(db: Session, candidate: ApiCandidate) -> Source:
    if candidate.generated_source_id:
        existing_source = db.query(Source).filter(Source.id == candidate.generated_source_id).first()
        if existing_source:
            return existing_source

    source = Source(
        name=f"API Candidate - {candidate.name}",
        source_type=f"api_catalogue_{candidate.category or 'general'}",
        url=candidate.url or "",
        collection_method="api_candidate_manual",
        trust_tier=3,
        region="API Catalogue",
        enabled=False,
        frequency_minutes=360,
        reliability_score=max(25.0, min(75.0, candidate.maritime_relevance_score)),
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    candidate.generated_source_id = source.id
    candidate.approval_status = "Approved"
    candidate.updated_at = datetime.now(timezone.utc)
    db.commit()
    return source
