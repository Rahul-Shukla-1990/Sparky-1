import re
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from app.models import Incident


STOPWORDS = {
    "the", "a", "an", "of", "in", "on", "near", "off", "and", "to", "for",
    "with", "after", "at", "by", "from", "reported", "report", "incident"
}


def normalize_title(title: str) -> str:
    t = re.sub(r"[^a-z0-9\s]", " ", (title or "").lower())
    words = [w for w in t.split() if w not in STOPWORDS and len(w) > 2]
    return " ".join(words[:14])


def make_normalized_key(category: str, title: str, vessel_name: str | None, incident_date) -> str:
    date_part = incident_date.date().isoformat() if incident_date else "unknown-date"
    vessel_part = (vessel_name or "").lower().strip()
    title_part = normalize_title(title)
    return f"{category}|{date_part}|{vessel_part}|{title_part}"


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a or "", b or "").ratio() * 100.0


def find_duplicate(db: Session, candidate: Incident) -> tuple[int | None, float]:
    # Strong exact normalized-key match first.
    if candidate.normalized_key:
        existing = (
            db.query(Incident)
            .filter(Incident.normalized_key == candidate.normalized_key)
            .filter(Incident.id != candidate.id)
            .filter(Incident.duplicate_of_id.is_(None))
            .first()
        )
        if existing:
            return existing.id, 100.0

    # Conservative fuzzy match among recent same-category incidents.
    possibles = (
        db.query(Incident)
        .filter(Incident.category == candidate.category)
        .filter(Incident.duplicate_of_id.is_(None))
        .order_by(Incident.detected_at.desc())
        .limit(100)
        .all()
    )

    cand_norm = normalize_title(candidate.title)
    best_id = None
    best_score = 0.0

    for inc in possibles:
        if inc.id == candidate.id:
            continue
        score = similarity(cand_norm, normalize_title(inc.title))
        if candidate.vessel_name and inc.vessel_name and candidate.vessel_name.lower() == inc.vessel_name.lower():
            score += 20
        if candidate.incident_date and inc.incident_date and candidate.incident_date.date() == inc.incident_date.date():
            score += 10

        score = min(100.0, score)
        if score > best_score:
            best_score = score
            best_id = inc.id

    if best_score >= 82:
        return best_id, best_score

    return None, best_score
