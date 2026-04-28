from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import SocialSubmission, User
from app.schemas import SocialSubmissionCreate, SocialSubmissionOut
from app.deps import require_role
from app.services.social_intake import create_social_submission
from app.services.telegram import poll_telegram_once
from app.audit import write_audit

router = APIRouter(prefix="/api/social", tags=["social"])

@router.post("/submit", response_model=SocialSubmissionOut)
def submit_social(payload: SocialSubmissionCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Collector"))):
    sub = create_social_submission(db, payload.platform, payload.input_type, payload.submitted_text, payload.submitted_url, payload.source_reliability, user=user)
    write_audit(db, user, "submit_social", "social_submission", str(sub.id), f"Platform={payload.platform}", request.client.host if request.client else None)
    return sub

@router.get("/submissions", response_model=list[SocialSubmissionOut])
def list_submissions(limit: int = 100, db: Session = Depends(get_db), user: User = Depends(require_role("Viewer"))):
    return db.query(SocialSubmission).order_by(SocialSubmission.created_at.desc()).limit(limit).all()

@router.post("/telegram/poll-once")
def telegram_poll_once(request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Admin"))):
    result = poll_telegram_once(db)
    write_audit(db, user, "telegram_poll_once", "telegram", None, str(result), request.client.host if request.client else None)
    return result
