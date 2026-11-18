import os
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import auth
import models
from database import get_db

router = APIRouter(
    prefix="/api/v1/tours",
    tags=["Guided Tour Voiceovers"]
)

# Configurable upload directory (Option 1: Railway Persistent Volume / Local Disk)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads/audio")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_AUDIO_EXTENSIONS = {"webm", "mp3", "wav", "ogg", "m4a"}
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
TOUR_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_tour_id(tour_id: str) -> str:
    if not TOUR_ID_PATTERN.match(tour_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tour_id format",
        )
    return tour_id


@router.get("/{tour_id}/voiceovers")
def get_tour_voiceovers(tour_id: str, db: Session = Depends(get_db)):
    """
    Returns a map of step indices to relative audio URL paths for the given tour_id.
    Relative paths are used so they resolve correctly both locally and on Railway.
    """
    _validate_tour_id(tour_id)
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
    admin_user: dict = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    """
    Uploads or updates a step voiceover audio file (Admin Only).
    Saves binary file to UPLOAD_DIR and upserts SQL metadata record.
    """
    _validate_tour_id(tour_id)
    admin_email = admin_user.get("email", "admin")

    ext = "webm"
    if file.filename and "." in file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format. Allowed: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}",
        )

    contents = await file.read(MAX_AUDIO_BYTES + 1)
    if len(contents) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file exceeds 10 MB limit",
        )

    filename = f"{tour_id}_step_{step_index}.{ext}"
    upload_root = Path(UPLOAD_DIR).resolve()
    file_path = (upload_root / filename).resolve()
    if file_path.parent != upload_root:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file path")

    # Save file to Option 1 Storage (Persistent Volume / Local Disk)
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
        
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
    admin_user: dict = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    """
    Deletes a step voiceover file and removes its metadata record (Admin Only).
    """
    _validate_tour_id(tour_id)
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
