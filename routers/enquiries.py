from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(tags=["enquiries"])

@router.post("/teams/{team_id}/enquiries", response_model=schemas.EnquiryResponse)
def create_enquiry(
    team_id: int,
    enquiry: schemas.EnquiryCreate,
    db: Session = Depends(get_db)
):
    # Note: Middle layer doesn't verify the basic_backend JWT. 
    # It relies on the frontend/backend to supply the applicant details.
    
    new_enquiry = models.DataCustodianEnquiry(
        team_id=team_id,
        user_id=None, # user_id could be passed if needed, but name/email is sufficient for notifications
        dataset_name=enquiry.dataset_name,
        contact_number=enquiry.contact_number,
        enquiry_text=enquiry.enquiry_text,
        consent_given=enquiry.consent_given,
        applicant_name=enquiry.applicant_name,
        applicant_email=enquiry.applicant_email,
        applicant_organisation=enquiry.applicant_organisation
    )
    
    db.add(new_enquiry)
    db.commit()
    db.refresh(new_enquiry)
    
    return new_enquiry

@router.get("/teams/{team_id}/enquiries", response_model=List[schemas.EnquiryResponse])
def get_team_enquiries(
    team_id: int,
    db: Session = Depends(get_db)
):
    enquiries = db.query(models.DataCustodianEnquiry).filter(models.DataCustodianEnquiry.team_id == team_id).all()
    return enquiries

@router.get("/admin/enquiries", response_model=List[schemas.EnquiryResponse])
def get_all_enquiries(db: Session = Depends(get_db)):
    # Note: Middle layer assumes the request is authorized (or should add auth middleware if needed)
    enquiries = db.query(models.DataCustodianEnquiry).order_by(models.DataCustodianEnquiry.created_at.desc()).all()
    return enquiries
