import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import IncidentAttachment, Incident, User
from app.schemas import IncidentAttachmentOut, LinkAttachmentCreate
from app.deps import require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/incidents/{incident_id}/attachments", tags=["attachments"])
UPLOAD_ROOT=Path("data/uploads"); UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

@router.get("", response_model=list[IncidentAttachmentOut])
def list_attachments(incident_id:int, db:Session=Depends(get_db), user:User=Depends(require_role("Viewer"))):
    return db.query(IncidentAttachment).filter(IncidentAttachment.incident_id==incident_id).order_by(IncidentAttachment.uploaded_at.desc()).all()

@router.post("/link", response_model=IncidentAttachmentOut)
def add_link(incident_id:int, payload:LinkAttachmentCreate, request:Request, db:Session=Depends(get_db), user:User=Depends(require_role("Collector"))):
    if not db.query(Incident).filter(Incident.id==incident_id).first(): raise HTTPException(status_code=404, detail="Incident not found")
    a=IncidentAttachment(incident_id=incident_id, attachment_type="link", display_name=payload.display_name or payload.url, url=payload.url, description=payload.description, uploaded_by=user.username)
    db.add(a); db.commit(); db.refresh(a)
    write_audit(db,user,"add_link_attachment","incident",str(incident_id),payload.url,request.client.host if request.client else None)
    return a

@router.post("/upload", response_model=IncidentAttachmentOut)
def upload_file(incident_id:int, request:Request, file:UploadFile=File(...), db:Session=Depends(get_db), user:User=Depends(require_role("Collector"))):
    if not db.query(Incident).filter(Incident.id==incident_id).first(): raise HTTPException(status_code=404, detail="Incident not found")
    safe=Path(file.filename or "upload.bin").name; ext=Path(safe).suffix; stored=f"incident_{incident_id}_{uuid.uuid4().hex}{ext}"; target=UPLOAD_ROOT/stored
    size=0
    with target.open("wb") as f:
        while True:
            chunk=file.file.read(1024*1024)
            if not chunk: break
            size+=len(chunk); f.write(chunk)
    mime=file.content_type or "application/octet-stream"; atype="image" if mime.startswith("image/") else "document"
    a=IncidentAttachment(incident_id=incident_id, attachment_type=atype, display_name=safe, file_name=safe, file_path=f"/uploads/{stored}", mime_type=mime, file_size=size, uploaded_by=user.username)
    db.add(a); db.commit(); db.refresh(a)
    write_audit(db,user,"upload_attachment","incident",str(incident_id),safe,request.client.host if request.client else None)
    return a
