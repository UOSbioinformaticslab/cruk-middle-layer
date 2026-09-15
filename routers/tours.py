import os
import shutil
import urllib.request
import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import models
from database import get_db

router = APIRouter(
    prefix="/api/v1/tours",
    tags=["Guided Tour Voiceovers"]
)

# Configurable upload directory (Option 1: Railway Persistent Volume / Local Disk)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/audio")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Authentication Verification Helper against VITE_BACKEND_URL / Gatekeeper
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

def verify_admin_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token is required"
        )
    token = authorization.split(" ")[1]
    
    # Validate token against primary backend service (VITE_BACKEND_URL)
    try:
        req = urllib.request.Request(
            f"{BACKEND_URL}/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                user_data = json.loads(resp.read().decode())
                # Allow if user is superuser/admin or has valid admin privileges
                is_admin = user_data.get("is_superuser") or user_data.get("is_admin") or user_data.get("role") == "admin"
                if not is_admin:
                    # In development, also check if logged in as test@test.com or skw24
                    email = user_data.get("email", "")
                    if email not in ["test@test.com", "skw24@sussex.ac.uk", "b.hall@ucl.ac.uk"]:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required to edit tour voiceovers")
                return user_data.get("email", "admin")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Token validation warning against backend: {e}")
        # Development fallback if token format is valid string
        if len(token) > 10:
            return "admin_dev"
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

@router.get("/{tour_id}/voiceovers")
def get_tour_voiceovers(tour_id: str, db: Session = Depends(get_db)):
    """
    Returns a map of step indices to relative audio URL paths for the given tour_id.
    Relative paths are used so they resolve correctly both locally and on Railway.
    """
    voiceovers = db.query(models.TourVoiceover).filter(models.TourVoiceover.tour_id == tour_id).all()
    result = {}
    for v in voiceovers:
        # Return relative URL path: /static/audio/{filename}
        result[str(v.step_index)] = f"/static/audio/{v.audio_filename}"
    
    return {
        "tour_id": tour_id,
        "voiceovers": result
    }

@router.post("/{tour_id}/steps/{step_index}/voiceover")
async def upload_step_voiceover(
    tour_id: str,
    step_index: int,
    file: UploadFile = File(...),
    admin_email: str = Depends(verify_admin_token),
    db: Session = Depends(get_db)
):
    """
    Uploads or updates a step voiceover audio file (Admin Only).
    Saves binary file to UPLOAD_DIR and upserts SQL metadata record.
    """
    ext = "webm"
    if file.filename and "." in file.filename:
        ext = file.filename.split(".")[-1]
    
    filename = f"{tour_id}_step_{step_index}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save file to Option 1 Storage (Persistent Volume / Local Disk)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Upsert SQL Database Record in middle
    existing = db.query(models.TourVoiceover).filter(
        models.TourVoiceover.tour_id == tour_id,
        models.TourVoiceover.step_index == step_index
    ).first()
    
    if existing:
        existing.audio_filename = filename
        existing.mime_type = file.content_type or f"audio/{ext}"
        existing.created_by_user = admin_email
        existing.updated_at = datetime.now(timezone.utc)
    else:
        new_record = models.TourVoiceover(
            tour_id=tour_id,
            step_index=step_index,
            audio_filename=filename,
            mime_type=file.content_type or f"audio/{ext}",
            created_by_user=admin_email
        )
        db.add(new_record)
        
    db.commit()
    
    return {
        "message": "Voiceover uploaded successfully",
        "tour_id": tour_id,
        "step_index": step_index,
        "audio_url": f"/static/audio/{filename}"
    }

@router.delete("/{tour_id}/steps/{step_index}/voiceover")
def delete_step_voiceover(
    tour_id: str,
    step_index: int,
    admin_email: str = Depends(verify_admin_token),
    db: Session = Depends(get_db)
):
    """
    Deletes a step voiceover file and removes its metadata record (Admin Only).
    """
    existing = db.query(models.TourVoiceover).filter(
        models.TourVoiceover.tour_id == tour_id,
        models.TourVoiceover.step_index == step_index
    ).first()
    
    if existing:
        file_path = os.path.join(UPLOAD_DIR, existing.audio_filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"File delete error: {e}")
                
        db.delete(existing)
        db.commit()
        return {"message": "Voiceover deleted successfully"}
        
    raise HTTPException(status_code=404, detail="Voiceover not found")
