import csv
import json
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Incident, ExportRecord


EXPORT_FIELDS = [
    "incident_uid", "title", "category", "alert_level", "verification_status",
    "review_status", "confidence_score", "region", "latitude", "longitude",
    "vessel_name", "imo", "mmsi", "source_channel", "source_platform",
    "source_display", "submitted_by", "submitted_by_user_id", "source_chat_or_group",
    "source_message_id", "source_name", "source_url", "detected_at",
    "incident_date", "duplicate_of_id", "source_count"
]


def incident_to_dict(incident: Incident) -> dict:
    data = {}
    for field in EXPORT_FIELDS:
        value = getattr(incident, field)
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        data[field] = value
    data["summary"] = incident.summary
    data["analyst_remarks"] = incident.analyst_remarks
    return data


def export_incidents_csv(db: Session, include_duplicates: bool = False) -> str:
    export_dir = Path(settings.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"incidents_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    query = db.query(Incident).order_by(Incident.detected_at.desc())
    if not include_duplicates:
        query = query.filter(Incident.duplicate_of_id.is_(None))
    incidents = query.all()

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_FIELDS + ["summary", "analyst_remarks"])
        writer.writeheader()
        for inc in incidents:
            writer.writerow(incident_to_dict(inc))

    db.add(ExportRecord(export_type="csv", file_path=str(path), record_count=len(incidents)))
    db.commit()
    return str(path)


def export_incidents_json(db: Session, include_duplicates: bool = False) -> str:
    export_dir = Path(settings.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / f"incidents_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

    query = db.query(Incident).order_by(Incident.detected_at.desc())
    if not include_duplicates:
        query = query.filter(Incident.duplicate_of_id.is_(None))
    incidents = query.all()

    payload = [incident_to_dict(inc) for inc in incidents]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    db.add(ExportRecord(export_type="json", file_path=str(path), record_count=len(incidents)))
    db.commit()
    return str(path)
