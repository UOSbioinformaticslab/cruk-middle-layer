from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TeamRequestBase(BaseModel):
    user_name: Optional[str] = None
    email: Optional[str] = None
    team_name: str
    hdr_gateway_email: Optional[str] = None
    team_introduction: Optional[str] = None
    reason: str
    team_url: Optional[str] = None
    data_access_request_url: Optional[str] = None
    team_logo_base64: Optional[str] = None

class TeamRequestResponse(TeamRequestBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class ErrorLogCreate(BaseModel):
    service_name: str
    correlation_id: str
    message: Optional[str] = None
    stack_trace: Optional[str] = None

class ErrorLogUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None

class ErrorLogResponse(ErrorLogCreate):
    id: int
    timestamp: datetime
    status: str
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None

    class Config:
        from_attributes = True

class EnquiryCreate(BaseModel):
    contact_number: Optional[str] = None
    dataset_name: Optional[str] = None
    enquiry_text: str
    consent_given: bool
    applicant_name: Optional[str] = None
    applicant_email: Optional[str] = None
    applicant_organisation: Optional[str] = None

class EnquiryResponse(BaseModel):
    id: int
    team_id: int
    user_id: Optional[int] = None
    dataset_name: Optional[str] = None
    contact_number: Optional[str] = None
    enquiry_text: str
    consent_given: bool
    created_at: datetime
    applicant_name: Optional[str] = None
    applicant_email: Optional[str] = None
    applicant_organisation: Optional[str] = None

    class Config:
        from_attributes = True

from typing import List, Dict, Any

class RejectedFilterIn(BaseModel):
    filter_id: str
    filter_label: Optional[str] = None
    triggering_phrase: Optional[str] = None
    metadata_field: Optional[str] = None
    snippet_context: Optional[str] = None
    rejection_type: Optional[str] = "INDIVIDUAL_DISMISS"

class UploadSessionCreate(BaseModel):
    session_id: str
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    recommender_used: bool = False
    recommender_action: Optional[str] = "INDIVIDUAL_REVIEW"
    total_recommended: int = 0
    total_accepted: int = 0
    total_rejected: int = 0
    sections_visited: Optional[List[str]] = []
    manual_filters_added: Optional[List[Dict[str, Any]]] = []
    rejected_filters: Optional[List[RejectedFilterIn]] = []

class UploadSessionResponse(BaseModel):
    id: int
    session_id: str
    dataset_id: Optional[str] = None
    dataset_name: Optional[str] = None
    recommender_action: Optional[str] = None
    total_recommended: int
    total_accepted: int
    total_rejected: int
    created_at: datetime

    class Config:
        from_attributes = True

class TriggeringPhraseSummary(BaseModel):
    phrase: str
    field: Optional[str] = None
    count: int
    sample_snippets: List[str] = []

class FilterRejectionGroup(BaseModel):
    filter_id: str
    filter_label: str
    filter_hierarchy: Optional[str] = None
    rejection_count: int
    dataset_names: List[str] = []
    triggering_phrases: List[TriggeringPhraseSummary] = []

class FilterRejectionsResponse(BaseModel):
    since: str
    total_rejections: int
    filters: List[FilterRejectionGroup]

class ManualFilterItem(BaseModel):
    filter_id: str
    filter_label: str
    filter_hierarchy: Optional[str] = None
    category: Optional[str] = None
    times_added: int
    datasets: List[str] = []

class ManualFiltersResponse(BaseModel):
    since: str
    total_manual_additions: int
    filters: List[ManualFilterItem]
