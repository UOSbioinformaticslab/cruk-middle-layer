from sqlalchemy import Column, Integer, String, Text, DateTime
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
