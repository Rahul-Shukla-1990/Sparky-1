from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db import get_db
from app.models import Incident, Source, SocialSubmission, User
from app.deps import require_role

router = APIRouter(prefix="/api/stats", tags=["stats"])

@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(require_role("Viewer"))):
    total = db.query(func.count(Incident.id)).filter(Incident.duplicate_of_id.is_(None)).scalar() or 0
    pending = db.query(func.count(Incident.id)).filter(Incident.review_status == "Pending Review", Incident.duplicate_of_id.is_(None)).scalar() or 0
    duplicates = db.query(func.count(Incident.id)).filter(Incident.duplicate_of_id.is_not(None)).scalar() or 0
    sources = db.query(func.count(Source.id)).scalar() or 0
    enabled_sources = db.query(func.count(Source.id)).filter(Source.enabled == True).scalar() or 0
    social_submissions = db.query(func.count(SocialSubmission.id)).scalar() or 0
    by_category = dict(db.query(Incident.category, func.count(Incident.id)).filter(Incident.duplicate_of_id.is_(None)).group_by(Incident.category).all())
    by_alert = dict(db.query(Incident.alert_level, func.count(Incident.id)).filter(Incident.duplicate_of_id.is_(None)).group_by(Incident.alert_level).all())
    return {"total_incidents": total, "pending_review": pending, "duplicates": duplicates, "sources": sources, "enabled_sources": enabled_sources, "social_submissions": social_submissions, "by_category": by_category, "by_alert": by_alert}
