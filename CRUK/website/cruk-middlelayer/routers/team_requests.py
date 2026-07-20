from fastapi import APIRouter, Depends, Form, UploadFile, File, Request, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
import base64
import time
from typing import List
from datetime import datetime, timezone

router = APIRouter(prefix="/team_requests", tags=["Team Requests"])

# Simple in-memory rate limiter: dict of IP -> list of timestamps
rate_limits = {}

def check_rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    
    if ip in rate_limits:
        rate_limits[ip] = [t for t in rate_limits[ip] if now - t < 3600]
    else:
        rate_limits[ip] = []
    
    if len(rate_limits[ip]) >= 5:
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    
    rate_limits[ip].append(now)

@router.post("/", response_model=schemas.TeamRequestResponse)
async def create_team_request(
    request: Request,
    email: str = Form(""),
    team_name: str = Form(...),
    team_introduction: str = Form(""),
    reason: str = Form(...),
    team_url: str = Form(""),
    hdr_gateway_email: str = Form(""),
    data_access_request_url: str = Form(""),
    website_url: str = Form(""), # Honeypot
    user_name: str = Form(""),
    team_logo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Rate Limit Check
    check_rate_limit(request)
    
    # Honeypot Check (If filled, silently act like it succeeded to fool bots)
    if website_url != "":
        return schemas.TeamRequestResponse(
            id=999,
            email=email,
            team_name=team_name,
            reason=reason,
            status="Pending",
            created_at=datetime.now(timezone.utc)
        )

    logo_base64 = None
    if team_logo:
        if not team_logo.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Team logo must be an image.")
            
        contents = await team_logo.read()
        if contents:
            logo_base64 = base64.b64encode(contents).decode('utf-8')
            logo_base64 = f"data:{team_logo.content_type};base64,{logo_base64}"
    
    new_request = models.TeamRequest(
        user_name=user_name if user_name else None,
        email=email if email else None,
        team_name=team_name,
        hdr_gateway_email=hdr_gateway_email if hdr_gateway_email else None,
        team_introduction=team_introduction if team_introduction else None,
        reason=reason,
        team_url=team_url if team_url else None,
        data_access_request_url=data_access_request_url if data_access_request_url else None,
        team_logo_base64=logo_base64
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    
    return new_request

@router.get("/", response_model=List[schemas.TeamRequestResponse])
def get_team_requests(db: Session = Depends(get_db)):
    """
    Retrieve all team requests. Visible in Swagger for admins.
    """
    requests = db.query(models.TeamRequest).all()
    return requests
