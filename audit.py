from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogOut
from app.deps import require_role

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("", response_model=list[AuditLogOut])
def list_audit(limit: int = 200, db: Session = Depends(get_db), user: User = Depends(require_role("Admin"))):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
