from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models import Source, RawDocument, Incident, CollectionLog
from app.collectors.rss_collector import collect_rss
from app.collectors.web_collector import collect_static_page
from app.collectors.gdelt_collector import collect_gdelt_query
from app.nlp.classifier import maritime_relevance_score, classify_incident, determine_alert_level, verification_status
from app.nlp.extractor import make_incident_uid, extract_date, extract_coordinates, extract_vessel_identifiers
from app.nlp.aoi import aoi_score, passes_aoi_filter
from app.services.dedupe import make_normalized_key, find_duplicate


def _mark_success(source: Source):
    source.success_count = (source.success_count or 0) + 1
    source.last_success_at = datetime.now(timezone.utc)
    total = max(1, (source.success_count or 0) + (source.error_count or 0))
    source.reliability_score = min(100.0, 40.0 + (source.success_count or 0) / total * 60.0)
    source.last_error_message = None


def _mark_error(source: Source, message: str):
    source.error_count = (source.error_count or 0) + 1
    source.last_error_at = datetime.now(timezone.utc)
    source.last_error_message = message[:1000]
    total = max(1, (source.success_count or 0) + (source.error_count or 0))
    source.reliability_score = max(0.0, 40.0 + (source.success_count or 0) / total * 60.0)


def create_incident_from_text(db: Session, title: str, text: str, source_name: str, source_url: str | None, source_tier: int, region: str, raw_document_id: int | None = None, social_submission_id: int | None = None, base_confidence_boost: float = 0.0):
    combined = f"{title}\n\n{text}"
    category, cat_conf = classify_incident(combined)
    base_conf = cat_conf + base_confidence_boost + ({1: 20, 2: 12, 3: 5}.get(source_tier, 0))
    lat, lon = extract_coordinates(combined)
    if lat is not None and lon is not None:
        base_conf += 10
    vessel_name, imo, mmsi = extract_vessel_identifiers(combined)
    if vessel_name or imo or mmsi:
        base_conf += 7
    if aoi_score(combined, lat, lon) >= 60:
        base_conf += 5
    confidence = min(100.0, base_conf)
    incident_date = extract_date(combined)
    uid = make_incident_uid(title or "untitled", source_url or combined[:120], category)
    incident = Incident(
        incident_uid=uid, raw_document_id=raw_document_id, social_submission_id=social_submission_id,
        title=title or "Untitled maritime incident candidate", summary=(text or "")[:900], category=category,
        incident_date=incident_date, latitude=lat, longitude=lon, region=region, vessel_name=vessel_name, imo=imo, mmsi=mmsi,
        source_name=source_name, source_url=source_url, source_tier=source_tier, confidence_score=confidence,
        verification_status=verification_status(confidence), alert_level=determine_alert_level(category, combined, confidence),
        review_status="Pending Review", normalized_key=make_normalized_key(category, title or "untitled", vessel_name, incident_date)
    )
    db.add(incident)
    try:
        db.commit(); db.refresh(incident)
        duplicate_id, dup_score = find_duplicate(db, incident)
        if duplicate_id:
            incident.duplicate_of_id = duplicate_id
            incident.duplicate_score = dup_score
            primary = db.query(Incident).filter(Incident.id == duplicate_id).first()
            if primary:
                primary.source_count = (primary.source_count or 1) + 1
        else:
            incident.duplicate_score = dup_score
        db.commit(); db.refresh(incident)
        return incident
    except IntegrityError:
        db.rollback(); return None


def collect_source(db: Session, source: Source) -> dict:
    log = CollectionLog(source_id=source.id, source_name=source.name, status="Started")
    db.add(log); db.commit(); db.refresh(log)
    src = {"name": source.name, "url": source.url, "collection_method": source.collection_method, "trust_tier": source.trust_tier, "region": source.region}
    try:
        if source.collection_method == "rss": items = collect_rss(src)
        elif source.collection_method == "static_page": items = collect_static_page(src)
        elif source.collection_method == "gdelt_query": src["query"] = source.url; items = collect_gdelt_query(src)
        else: raise ValueError(f"Unsupported collection method: {source.collection_method}")
        stored = incidents = 0
        for item in items:
            lat, lon = extract_coordinates(item.raw_text)
            raw = RawDocument(source_id=source.id, title=item.title, url=item.url, published_at=item.published_at, raw_text=item.raw_text, relevance_score=maritime_relevance_score(item.raw_text), aoi_score=aoi_score(item.raw_text, lat, lon))
            db.add(raw)
            try:
                db.commit(); db.refresh(raw); stored += 1
            except IntegrityError:
                db.rollback(); continue
            if raw.relevance_score >= 20 and passes_aoi_filter(item.raw_text, lat, lon):
                inc = create_incident_from_text(db, raw.title or "Untitled maritime incident candidate", raw.raw_text or "", source.name, raw.url, source.trust_tier, source.region, raw_document_id=raw.id)
                if inc:
                    incidents += 1; raw.processed = True; db.commit()
        log.status = "Success"; log.collected_count = len(items); log.stored_count = stored; log.incident_count = incidents; log.finished_at = datetime.now(timezone.utc)
        _mark_success(source); db.commit()
        return {"source": source.name, "collected": len(items), "stored": stored, "incidents": incidents}
    except Exception as exc:
        msg = str(exc); log.status = "Error"; log.error_message = msg; log.finished_at = datetime.now(timezone.utc)
        _mark_error(source, msg); db.commit()
        return {"source": source.name, "error": msg, "collected": 0, "stored": 0, "incidents": 0}


def run_collection_cycle(db: Session) -> list[dict]:
    return [collect_source(db, source) for source in db.query(Source).filter(Source.enabled == True).all()]
