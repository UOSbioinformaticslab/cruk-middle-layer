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
