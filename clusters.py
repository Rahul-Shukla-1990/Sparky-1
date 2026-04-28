from collections import Counter, defaultdict
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.db import get_db
from app.models import IncidentCluster, IncidentClusterMembership, Incident, User
from app.schemas import IncidentClusterCreate, IncidentClusterOut, ClusterMembershipOut, AddIncidentToClusterRequest
from app.deps import require_role
from app.audit import write_audit

router = APIRouter(prefix="/api/clusters", tags=["clusters"])

@router.get("", response_model=list[IncidentClusterOut])
def list_clusters(db: Session = Depends(get_db), user: User = Depends(require_role("Viewer"))):
    return db.query(IncidentCluster).order_by(IncidentCluster.created_at.desc()).all()

@router.post("", response_model=IncidentClusterOut)
def create_cluster(payload: IncidentClusterCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    c = IncidentCluster(name=payload.name, cluster_type=payload.cluster_type, description=payload.description, report_period=payload.report_period, color_label=payload.color_label, created_by=user.username)
    db.add(c); db.commit(); db.refresh(c)
    write_audit(db, user, "create_cluster", "cluster", str(c.id), c.name, request.client.host if request.client else None)
    return c

@router.post("/{cluster_id}/incidents", response_model=ClusterMembershipOut)
def add_incident(cluster_id: int, payload: AddIncidentToClusterRequest, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("Analyst"))):
    if not db.query(IncidentCluster).filter(IncidentCluster.id == cluster_id).first() or not db.query(Incident).filter(Incident.id == payload.incident_id).first():
        raise HTTPException(status_code=404, detail="Cluster or incident not found")
    m = IncidentClusterMembership(cluster_id=cluster_id, incident_id=payload.incident_id, added_by=user.username)
    db.add(m)
    try:
        db.commit(); db.refresh(m)
    except IntegrityError:
        db.rollback()
        m = db.query(IncidentClusterMembership).filter(IncidentClusterMembership.cluster_id==cluster_id, IncidentClusterMembership.incident_id==payload.incident_id).first()
    write_audit(db, user, "add_incident_to_cluster", "cluster", str(cluster_id), f"Incident {payload.incident_id}", request.client.host if request.client else None)
    return m

@router.get("/{cluster_id}/incidents")
def cluster_incidents(cluster_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("Viewer"))):
    rows = db.query(IncidentClusterMembership, Incident).join(Incident, Incident.id == IncidentClusterMembership.incident_id).filter(IncidentClusterMembership.cluster_id == cluster_id).order_by(Incident.detected_at.desc()).all()
    return [{"membership_id":m.id,"incident_id":i.id,"title":i.title,"category":i.category,"alert_level":i.alert_level,"review_status":i.review_status,"detected_at":i.detected_at.isoformat() if i.detected_at else None} for m,i in rows]

REPORT_FIELD_MAP={"daily":"include_daily","weekly":"include_weekly","monthly":"include_monthly","half_yearly":"include_half_yearly","annual":"include_annual"}

@router.get("/report-graphs")
def report_graphs(period: str = Query("daily"), db: Session = Depends(get_db), user: User = Depends(require_role("Viewer"))):
    if period not in REPORT_FIELD_MAP: raise HTTPException(status_code=400, detail="Invalid period")
    flag = getattr(Incident, REPORT_FIELD_MAP[period])
    incidents = db.query(Incident).filter(flag == True).filter(Incident.duplicate_of_id.is_(None)).all()
    category_counts = Counter(i.category for i in incidents); alert_counts = Counter(i.alert_level for i in incidents)
    memberships = db.query(IncidentClusterMembership, IncidentCluster, Incident).join(IncidentCluster, IncidentCluster.id==IncidentClusterMembership.cluster_id).join(Incident, Incident.id==IncidentClusterMembership.incident_id).filter(flag == True).all()
    cluster_counts=Counter(); cluster_category=defaultdict(Counter)
    for m,c,i in memberships:
        cluster_counts[c.name]+=1; cluster_category[c.name][i.category]+=1
    return {"period":period,"total_incidents":len(incidents),"category_counts":dict(category_counts),"alert_counts":dict(alert_counts),"cluster_counts":dict(cluster_counts),"cluster_category":{k:dict(v) for k,v in cluster_category.items()}}
