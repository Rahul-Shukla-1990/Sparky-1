from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db import get_db
from app.models import Incident, User, IncidentComment, SocialSubmission
from app.schemas import (
    IncidentOut,
    IncidentReviewUpdate,
    IncidentCategoryUpdate,
    IncidentEditUpdate,
    IncidentCommentCreate,
    IncidentCommentUpdate, IncidentReportFlagsUpdate,
    IncidentCommentOut,
)
from app.services.exporter import export_incidents_csv, export_incidents_json
from app.services.briefing import generate_daily_brief
from app.deps import require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    limit: int = Query(100, ge=1, le=500),
    category: str | None = None,
    alert_level: str | None = None,
    review_status: str | None = None,
    q: str | None = None,
    include_duplicates: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("Viewer")),
):
    query = db.query(Incident).order_by(Incident.detected_at.desc())
    if category:
        query = query.filter(Incident.category == category)
    if alert_level:
        query = query.filter(Incident.alert_level == alert_level)
    if review_status:
        query = query.filter(Incident.review_status == review_status)
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(Incident.title.ilike(term), Incident.summary.ilike(term), Incident.region.ilike(term), Incident.vessel_name.ilike(term), Incident.source_name.ilike(term)))
    if not include_duplicates:
        query = query.filter(Incident.duplicate_of_id.is_(None))
    return query.limit(limit).all()


@router.patch("/{incident_id}/review", response_model=IncidentOut)
def review_incident(incident_id: int, payload: IncidentReviewUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    inc.review_status = payload.review_status
    inc.analyst_verdict = payload.analyst_verdict
    inc.analyst_remarks = payload.analyst_remarks
    inc.reviewed_by = user.username
    inc.reviewed_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(inc)
    write_audit(db, user, "review_incident", "incident", str(inc.id), f"Verdict={payload.analyst_verdict}", request.client.host if request.client else None)
    return inc


@router.patch("/{incident_id}", response_model=IncidentOut)
def edit_incident(incident_id: int, payload: IncidentEditUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    allowed = [
        "title", "summary", "category", "sub_category", "region", "location_text", "latitude", "longitude",
        "vessel_name", "imo", "mmsi", "vessel_type", "flag", "source_name", "source_url", "alert_level", "verification_status",
    ]
    changed = []
    for field in allowed:
        value = getattr(payload, field)
        if value is not None:
            old = getattr(inc, field)
            setattr(inc, field, value)
            if old != value:
                changed.append(field)
    db.commit(); db.refresh(inc)
    write_audit(db, user, "edit_incident", "incident", str(inc.id), "Changed: " + ", ".join(changed), request.client.host if request.client else None)
    return inc


@router.patch("/{incident_id}/category", response_model=IncidentOut)
def move_category(incident_id: int, payload: IncidentCategoryUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    old = inc.category
    inc.category = payload.category
    inc.sub_category = payload.sub_category
    db.commit(); db.refresh(inc)
    write_audit(db, user, "move_incident_category", "incident", str(inc.id), f"{old} -> {inc.category}", request.client.host if request.client else None)
    return inc


@router.delete("/{incident_id}")
def delete_incident(incident_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    title = inc.title
    db.query(IncidentComment).filter(IncidentComment.incident_id == incident_id).delete()
    db.query(SocialSubmission).filter(SocialSubmission.generated_incident_id == incident_id).update({"generated_incident_id": None})
    db.delete(inc)
    db.commit()
    write_audit(db, user, "delete_incident", "incident", str(incident_id), f"Deleted: {title}", request.client.host if request.client else None)
    return {"status": "deleted", "incident_id": incident_id}


@router.get("/{incident_id}/comments", response_model=list[IncidentCommentOut])
def list_comments(incident_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("Viewer"))):
    return db.query(IncidentComment).filter(IncidentComment.incident_id == incident_id, IncidentComment.is_deleted == False).order_by(IncidentComment.created_at.asc()).all()


@router.post("/{incident_id}/comments", response_model=IncidentCommentOut)
def add_comment(incident_id: int, payload: IncidentCommentCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    comment = IncidentComment(
        incident_id=incident_id,
        comment_text=payload.comment_text,
        comment_type=payload.comment_type,
        created_by_user_id=user.id,
        created_by_username=user.username,
    )
    db.add(comment); db.commit(); db.refresh(comment)
    write_audit(db, user, "add_incident_comment", "incident_comment", str(comment.id), f"Incident={incident_id}", request.client.host if request.client else None)
    return comment


@router.patch("/comments/{comment_id}", response_model=IncidentCommentOut)
def edit_comment(comment_id: int, payload: IncidentCommentUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    comment = db.query(IncidentComment).filter(IncidentComment.id == comment_id, IncidentComment.is_deleted == False).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.comment_text = payload.comment_text
    if payload.comment_type:
        comment.comment_type = payload.comment_type
    comment.updated_by_username = user.username
    comment.updated_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(comment)
    write_audit(db, user, "edit_incident_comment", "incident_comment", str(comment.id), f"Incident={comment.incident_id}", request.client.host if request.client else None)
    return comment


@router.delete("/comments/{comment_id}")
def delete_comment(comment_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    comment = db.query(IncidentComment).filter(IncidentComment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_deleted = True
    comment.updated_by_username = user.username
    comment.updated_at = datetime.now(timezone.utc)
    db.commit()
    write_audit(db, user, "delete_incident_comment", "incident_comment", str(comment.id), f"Incident={comment.incident_id}", request.client.host if request.client else None)
    return {"status": "deleted", "comment_id": comment_id}


@router.post("/export/csv")
def export_csv(include_duplicates: bool = False, request: Request = None, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    path = export_incidents_csv(db, include_duplicates=include_duplicates)
    write_audit(db, user, "export_csv", "export", path, "CSV export generated", request.client.host if request and request.client else None)
    return {"export_path": path}


@router.post("/export/json")
def export_json(include_duplicates: bool = False, request: Request = None, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    path = export_incidents_json(db, include_duplicates=include_duplicates)
    write_audit(db, user, "export_json", "export", path, "JSON export generated", request.client.host if request and request.client else None)
    return {"export_path": path}


@router.post("/brief/daily")
def daily_brief(days: int = 1, request: Request = None, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    path = generate_daily_brief(db, days=days)
    write_audit(db, user, "generate_daily_brief", "brief", path, f"Days={days}", request.client.host if request and request.client else None)
    return {"brief_path": path}

@router.patch("/{incident_id}/report-flags", response_model=IncidentOut)
def update_report_flags(incident_id: int, payload: IncidentReportFlagsUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    for field in ["include_daily", "include_weekly", "include_monthly", "include_half_yearly", "include_annual"]:
        value = getattr(payload, field)
        if value is not None:
            setattr(inc, field, value)
    db.commit(); db.refresh(inc)
    write_audit(db, user, "update_report_flags", "incident", str(inc.id), "Updated report inclusion flags", request.client.host if request.client else None)
    return inc
