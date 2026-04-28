import yaml
from pathlib import Path
from sqlalchemy.orm import Session
from app.models import Source


def load_source_registry(path: str = "data/sources.yml") -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return data.get("sources", [])


def sync_sources_to_db(db: Session, path: str = "data/sources.yml") -> int:
    count = 0
    for src in load_source_registry(path):
        existing = db.query(Source).filter(Source.name == src["name"]).first()
        if existing:
            existing.url = src["url"]
            existing.source_type = src["source_type"]
            existing.collection_method = src["collection_method"]
            existing.trust_tier = src.get("trust_tier", 3)
            existing.region = src.get("region", "IOR")
            existing.enabled = src.get("enabled", True)
            existing.frequency_minutes = src.get("frequency_minutes", 60)
        else:
            db.add(Source(
                name=src["name"],
                source_type=src["source_type"],
                url=src["url"],
                collection_method=src["collection_method"],
                trust_tier=src.get("trust_tier", 3),
                region=src.get("region", "IOR"),
                enabled=src.get("enabled", True),
                frequency_minutes=src.get("frequency_minutes", 60),
                reliability_score=75.0 if src.get("trust_tier", 3) == 1 else 60.0 if src.get("trust_tier", 3) == 2 else 50.0,
            ))
        count += 1
    db.commit()
    return count
