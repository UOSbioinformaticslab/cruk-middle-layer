from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from datetime import datetime, timezone
from database import Base

class TeamRequest(Base):
    __tablename__ = "team_requests"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    team_name = Column(String, nullable=False)
    hdr_gateway_email = Column(String, nullable=True)
    team_introduction = Column(Text, nullable=True)
    reason = Column(Text, nullable=False)
    team_url = Column(String, nullable=True)
    data_access_request_url = Column(String, nullable=True)
    team_logo_base64 = Column(Text, nullable=True)
    status = Column(String, default="Pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ErrorLog(Base):
    __tablename__ = "error_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    service_name = Column(String, index=True)
    correlation_id = Column(String, index=True)
    message = Column(Text, nullable=True)
    stack_trace = Column(Text, nullable=True)
    status = Column(String, default="Open", index=True)
    assigned_to = Column(String, nullable=True)
    resolution_notes = Column(Text, nullable=True)

class DataCustodianEnquiry(Base):
    __tablename__ = "data_custodian_enquiries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    team_id = Column(Integer, index=True, nullable=False)
    user_id = Column(Integer, nullable=True)
    dataset_name = Column(String, nullable=True)
    contact_number = Column(String, nullable=True)
    enquiry_text = Column(Text, nullable=False)
    consent_given = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    applicant_name = Column(String, nullable=True)
    applicant_email = Column(String, nullable=True)
    applicant_organisation = Column(String, nullable=True)

class TourVoiceover(Base):
    __tablename__ = "tour_voiceovers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tour_id = Column(String, index=True, nullable=False)
    step_index = Column(Integer, nullable=False)
    audio_filename = Column(String, nullable=False)
    mime_type = Column(String, default="audio/webm")
    duration_seconds = Column(Integer, default=0)
    created_by_user = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    dataset_id = Column(String, index=True, nullable=True)
    dataset_name = Column(String, nullable=True)
    recommender_used = Column(Boolean, default=False)
    recommender_action = Column(String, nullable=True)  # ACCEPT_ALL, DISMISS_ALL, INDIVIDUAL_REVIEW, SKIPPED
    total_recommended = Column(Integer, default=0)
    total_accepted = Column(Integer, default=0)
    total_rejected = Column(Integer, default=0)
    manual_filters_added = Column(Text, nullable=True)  # JSON-encoded array
    sections_visited = Column(Text, nullable=True)      # JSON-encoded array
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

class FilterRejectionEvent(Base):
    __tablename__ = "filter_rejection_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    upload_session_id = Column(Integer, index=True, nullable=True)
    dataset_id = Column(String, index=True, nullable=True)
    dataset_name = Column(String, nullable=True)
    filter_id = Column(String, index=True, nullable=False)
    filter_label = Column(String, nullable=True)
    triggering_phrase = Column(String, index=True, nullable=True)
    metadata_field = Column(String, nullable=True)
    snippet_context = Column(Text, nullable=True)  # Bounded to +-100 chars
    rejection_type = Column(String, default="INDIVIDUAL_DISMISS")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

