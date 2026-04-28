from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    class Config: from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: Optional[str] = None
    role: str = "Viewer"


class SourceOut(BaseModel):
    id: int; name: str; source_type: str; url: str; collection_method: str; trust_tier: int; region: str; enabled: bool; frequency_minutes: int; reliability_score: float; success_count: int; error_count: int
    last_success_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error_message: Optional[str] = None
    class Config: from_attributes = True


class SourceUpdate(BaseModel):
    enabled: Optional[bool] = None
    frequency_minutes: Optional[int] = None
    trust_tier: Optional[int] = None


class IncidentOut(BaseModel):
    id: int; incident_uid: str; title: str; category: str; detected_at: datetime; source_tier: int; confidence_score: float; verification_status: str; alert_level: str; review_status: str; duplicate_score: float; source_count: int
    summary: Optional[str] = None
    sub_category: Optional[str] = None
    incident_date: Optional[datetime] = None
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    region: Optional[str] = None
    vessel_name: Optional[str] = None
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    vessel_type: Optional[str] = None
    flag: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    analyst_verdict: Optional[str] = None
    analyst_remarks: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    duplicate_of_id: Optional[int] = None
    source_channel: Optional[str] = None
    source_platform: Optional[str] = None
    source_display: Optional[str] = None
    submitted_by: Optional[str] = None
    submitted_by_user_id: Optional[str] = None
    source_chat_or_group: Optional[str] = None
    source_message_id: Optional[str] = None
    include_daily: bool = False
    include_weekly: bool = False
    include_monthly: bool = False
    include_half_yearly: bool = False
    include_annual: bool = False
    class Config: from_attributes = True


class IncidentReviewUpdate(BaseModel):
    review_status: str = "Reviewed"
    analyst_verdict: Optional[str] = None
    analyst_remarks: Optional[str] = None


class CollectionLogOut(BaseModel):
    id: int; started_at: datetime; status: str; collected_count: int; stored_count: int; incident_count: int
    source_name: Optional[str] = None
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None
    class Config: from_attributes = True


class SocialSubmissionCreate(BaseModel):
    platform: str = "Manual"
    input_type: str = "text_or_url"
    submitted_text: str
    submitted_url: Optional[str] = None
    source_reliability: str = "Unverified"


class SocialSubmissionOut(BaseModel):
    id: int; platform: str; input_type: str; submitted_text: str; source_reliability: str; review_status: str; created_at: datetime
    submitted_url: Optional[str] = None
    submitted_by_username: Optional[str] = None
    telegram_chat_title: Optional[str] = None
    telegram_username: Optional[str] = None
    generated_incident_id: Optional[int] = None
    class Config: from_attributes = True


class AuditLogOut(BaseModel):
    id: int; action: str; created_at: datetime
    actor_username: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    class Config: from_attributes = True


class IncidentCategoryUpdate(BaseModel):
    category: str
    sub_category: Optional[str] = None


class IncidentEditUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    region: Optional[str] = None
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    vessel_name: Optional[str] = None
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    vessel_type: Optional[str] = None
    flag: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    alert_level: Optional[str] = None
    verification_status: Optional[str] = None


class IncidentCommentCreate(BaseModel):
    comment_text: str
    comment_type: str = "Analyst Note"


class IncidentCommentUpdate(BaseModel):
    comment_text: str
    comment_type: Optional[str] = None


class IncidentCommentOut(BaseModel):
    id: int
    incident_id: int
    comment_text: str
    comment_type: str
    created_by_username: Optional[str] = None
    created_at: datetime
    updated_by_username: Optional[str] = None
    updated_at: Optional[datetime] = None
    is_deleted: bool
    class Config: from_attributes = True

class ApiCandidateOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    auth: Optional[str] = None
    https: Optional[str] = None
    cors: Optional[str] = None
    url: Optional[str] = None
    source_catalogue: str
    maritime_relevance_score: float
    free_assumption: bool
    requires_key: bool
    approval_status: str
    admin_notes: Optional[str] = None
    generated_source_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiCandidateUpdate(BaseModel):
    approval_status: Optional[str] = None
    admin_notes: Optional[str] = None
    maritime_relevance_score: Optional[float] = None

class IncidentReportFlagsUpdate(BaseModel):
    include_daily: Optional[bool] = None
    include_weekly: Optional[bool] = None
    include_monthly: Optional[bool] = None
    include_half_yearly: Optional[bool] = None
    include_annual: Optional[bool] = None


class IncidentClusterCreate(BaseModel):
    name: str
    cluster_type: str = "Operational"
    description: Optional[str] = None
    report_period: Optional[str] = None
    color_label: Optional[str] = None


class IncidentClusterOut(BaseModel):
    id: int
    name: str
    cluster_type: str
    description: Optional[str] = None
    report_period: Optional[str] = None
    color_label: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClusterMembershipOut(BaseModel):
    id: int
    cluster_id: int
    incident_id: int
    added_by: Optional[str] = None
    added_at: datetime

    class Config:
        from_attributes = True


class AddIncidentToClusterRequest(BaseModel):
    incident_id: int


class IncidentAttachmentOut(BaseModel):
    id: int
    incident_id: int
    attachment_type: str
    display_name: Optional[str] = None
    url: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    description: Optional[str] = None
    uploaded_by: Optional[str] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True


class LinkAttachmentCreate(BaseModel):
    url: str
    display_name: Optional[str] = None
    description: Optional[str] = None
