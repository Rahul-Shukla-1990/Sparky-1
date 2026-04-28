from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Source, CollectionLog, User
from app.schemas import SourceOut, SourceUpdate, CollectionLogOut
from app.services.pipeline import run_collection_cycle
from app.deps import require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/sources", tags=["sources"])

@router.get("", response_model=list[SourceOut])
def list_sources(db: Session = Depends(get_db), user: User = Depends(require_role("Viewer"))):
    return db.query(Source).order_by(Source.trust_tier.asc(), Source.name.asc()).all()

@router.patch("/{source_id}", response_model=SourceOut)
def update_source(source_id: int, payload: SourceUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Admin"))):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source: raise HTTPException(status_code=404, detail="Source not found")
    if payload.enabled is not None: source.enabled = payload.enabled
    if payload.frequency_minutes is not None: source.frequency_minutes = payload.frequency_minutes
    if payload.trust_tier is not None: source.trust_tier = payload.trust_tier
    db.commit(); db.refresh(source)
    write_audit(db, user, "update_source", "source", str(source.id), f"Updated source {source.name}", request.client.host if request.client else None)
    return source

@router.post("/collect-now")
def collect_now(request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    result = {"results": run_collection_cycle(db)}
    write_audit(db, user, "collect_now", "sources", "all", "Manual collection triggered", request.client.host if request.client else None)
    return result

@router.get("/logs", response_model=list[CollectionLogOut])
def collection_logs(limit: int = 100, db: Session = Depends(get_db), user: User = Depends(require_role("Viewer"))):
    return db.query(CollectionLog).order_by(CollectionLog.started_at.desc()).limit(limit).all()
