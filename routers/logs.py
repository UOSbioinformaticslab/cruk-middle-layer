from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/logs",
    tags=["Logs"]
)

@router.post("/error", response_model=schemas.ErrorLogResponse)
def create_error_log(log_in: schemas.ErrorLogCreate, db: Session = Depends(get_db)):
    db_log = models.ErrorLog(**log_in.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

from typing import List
from fastapi import HTTPException

@router.get("/errors", response_model=List[schemas.ErrorLogResponse])
def get_error_logs(db: Session = Depends(get_db)):
    return db.query(models.ErrorLog).order_by(models.ErrorLog.timestamp.desc()).all()

@router.put("/errors/{log_id}", response_model=schemas.ErrorLogResponse)
def update_error_log(log_id: int, log_update: schemas.ErrorLogUpdate, db: Session = Depends(get_db)):
    db_log = db.query(models.ErrorLog).filter(models.ErrorLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    update_data = log_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_log, key, value)
    
    db.commit()
    db.refresh(db_log)
    return db_log

@router.delete("/errors/{log_id}")
def delete_error_log(log_id: int, db: Session = Depends(get_db)):
    db_log = db.query(models.ErrorLog).filter(models.ErrorLog.id == log_id).first()
    if not db_log:
        raise HTTPException(status_code=404, detail="Log not found")
    
    db.delete(db_log)
    db.commit()
    return {"detail": "Log deleted"}
