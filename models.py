from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    display_name = Column(String(120), nullable=True)
    password_hash = Column(Text, nullable=False)
    role = Column(String(30), nullable=False, default="Viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_username = Column(String(80), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    source_type = Column(String(100), nullable=False)
    url = Column(Text, nullable=False)
    collection_method = Column(String(50), nullable=False)
    trust_tier = Column(Integer, default=3)
    region = Column(String(255), default="IOR")
    enabled = Column(Boolean, default=True)
    frequency_minutes = Column(Integer, default=60)
    reliability_score = Column(Float, default=50.0)
    success_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error_at = Column(DateTime(timezone=True), nullable=True)
    last_error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    raw_documents = relationship("RawDocument", back_populates="source")


class RawDocument(Base):
    __tablename__ = "raw_documents"
    __table_args__ = (UniqueConstraint("source_id", "url", name="uq_raw_source_url"),)
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    title = Column(Text, nullable=True)
    url = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), default=utcnow)
    raw_text = Column(Text, nullable=True)
    language = Column(String(20), nullable=True)
    processed = Column(Boolean, default=False)
    relevance_score = Column(Float, default=0.0)
    aoi_score = Column(Float, default=0.0)
    source = relationship("Source", back_populates="raw_documents")
    incidents = relationship("Incident", back_populates="raw_document")


class SocialSubmission(Base):
    __tablename__ = "social_submissions"
    id = Column(Integer, primary_key=True)
    platform = Column(String(80), nullable=False, default="Manual")
    input_type = Column(String(80), nullable=False, default="text_or_url")
    submitted_text = Column(Text, nullable=False)
    submitted_url = Column(Text, nullable=True)
    submitted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_by_username = Column(String(100), nullable=True)
    telegram_chat_id = Column(String(100), nullable=True)
    telegram_chat_title = Column(String(255), nullable=True)
    telegram_user_id = Column(String(100), nullable=True)
    telegram_username = Column(String(100), nullable=True)
    telegram_message_id = Column(String(100), nullable=True)
    source_reliability = Column(String(50), default="Unverified")
    review_status = Column(String(50), default="Pending Review")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    generated_incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=True)


class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    incident_uid = Column(String(64), nullable=False, unique=True)
    raw_document_id = Column(Integer, ForeignKey("raw_documents.id"), nullable=True)
    social_submission_id = Column(Integer, ForeignKey("social_submissions.id"), nullable=True)
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)
    sub_category = Column(String(100), nullable=True)
    incident_date = Column(DateTime(timezone=True), nullable=True)
    detected_at = Column(DateTime(timezone=True), default=utcnow)
    location_text = Column(Text, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    region = Column(String(255), nullable=True)
    vessel_name = Column(String(255), nullable=True)
    imo = Column(String(20), nullable=True)
    mmsi = Column(String(20), nullable=True)
    vessel_type = Column(String(100), nullable=True)
    flag = Column(String(100), nullable=True)
    source_name = Column(String(255), nullable=True)
    source_url = Column(Text, nullable=True)
    source_tier = Column(Integer, default=3)

    # Explicit provenance fields added in v0.6.
    source_channel = Column(String(100), default="background_source")
    source_platform = Column(String(100), nullable=True)
    source_display = Column(String(255), nullable=True)
    submitted_by = Column(String(255), nullable=True)
    submitted_by_user_id = Column(String(100), nullable=True)
    source_chat_or_group = Column(String(255), nullable=True)
    source_message_id = Column(String(100), nullable=True)

    include_daily = Column(Boolean, default=False)
    include_weekly = Column(Boolean, default=False)
    include_monthly = Column(Boolean, default=False)
    include_half_yearly = Column(Boolean, default=False)
    include_annual = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)
    verification_status = Column(String(50), default="Unverified")
    alert_level = Column(String(50), default="Low")
    review_status = Column(String(50), default="Pending Review")
    analyst_verdict = Column(String(50), nullable=True)
    analyst_remarks = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    normalized_key = Column(String(255), nullable=True)
    duplicate_of_id = Column(Integer, ForeignKey("incidents.id"), nullable=True)
    duplicate_score = Column(Float, default=0.0)
    source_count = Column(Integer, default=1)
    raw_document = relationship("RawDocument", back_populates="incidents")


class IncidentComment(Base):
    __tablename__ = "incident_comments"
    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    comment_text = Column(Text, nullable=False)
    comment_type = Column(String(50), default="Analyst Note")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_username = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_by_username = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    is_deleted = Column(Boolean, default=False)


class IncidentCluster(Base):
    __tablename__ = "incident_clusters"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    cluster_type = Column(String(100), default="Operational")
    description = Column(Text, nullable=True)
    report_period = Column(String(50), nullable=True)
    color_label = Column(String(50), nullable=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)


class IncidentClusterMembership(Base):
    __tablename__ = "incident_cluster_memberships"
    __table_args__ = (UniqueConstraint("cluster_id", "incident_id", name="uq_cluster_incident"),)

    id = Column(Integer, primary_key=True)
    cluster_id = Column(Integer, ForeignKey("incident_clusters.id"), nullable=False)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    added_by = Column(String(100), nullable=True)
    added_at = Column(DateTime(timezone=True), default=utcnow)


class IncidentAttachment(Base):
    __tablename__ = "incident_attachments"

    id = Column(Integer, primary_key=True)
    incident_id = Column(Integer, ForeignKey("incidents.id"), nullable=False)
    attachment_type = Column(String(50), default="link")
    display_name = Column(String(255), nullable=True)
    url = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=True)
    file_path = Column(Text, nullable=True)
    mime_type = Column(String(120), nullable=True)
    file_size = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    uploaded_by = Column(String(100), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=utcnow)


class CollectionLog(Base):
    __tablename__ = "collection_logs"
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    source_name = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), default=utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), default="Started")
    collected_count = Column(Integer, default=0)
    stored_count = Column(Integer, default=0)
    incident_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)


class ExportRecord(Base):
    __tablename__ = "export_records"
    id = Column(Integer, primary_key=True)
    export_type = Column(String(50), nullable=False)
    file_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    record_count = Column(Integer, default=0)



class ApiCandidate(Base):
    __tablename__ = "api_candidates"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    auth = Column(String(100), nullable=True)
    https = Column(String(30), nullable=True)
    cors = Column(String(50), nullable=True)
    url = Column(Text, nullable=True)
    source_catalogue = Column(String(255), default="public-apis/public-apis")
    maritime_relevance_score = Column(Float, default=0.0)
    free_assumption = Column(Boolean, default=True)
    requires_key = Column(Boolean, default=False)
    approval_status = Column(String(50), default="Candidate")
    admin_notes = Column(Text, nullable=True)
    generated_source_id = Column(Integer, ForeignKey("sources.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow)


class AppState(Base):
    __tablename__ = "app_state"
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow)
