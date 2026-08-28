# app/api/routes/upload.py
"""
Upload API Routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Optional
import os
import shutil
import hashlib
from datetime import datetime

router = APIRouter()
from sqlalchemy.orm import Session
from app.api.dependencies.auth import current_patient
from app.core.database import get_db
from app.database.models.domain import Patient, Report


@router.post("/upload/report")
async def upload_report(
    file: UploadFile = File(...),
    module: str = "unknown",
    patient: Patient = Depends(current_patient),
    db: Session = Depends(get_db),
):
    """
    Upload a medical report file.
    
    Args:
        file: The file to upload (PDF, DOCX, TXT, etc.)
        patient_id: Optional patient ID
        
    Returns:
        Upload status and file info
    """
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        file_extension = os.path.splitext(file.filename)[1]
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        with open(file_path, "rb") as uploaded:
            content_sha256 = hashlib.file_digest(uploaded, "sha256").hexdigest()
        existing = db.query(Report).filter_by(patient_id=patient.id, content_sha256=content_sha256).one_or_none()
        if existing:
            os.remove(file_path)
            return {"success": True, "message": "File was already uploaded", "filename": existing.stored_filename,
                    "file_path": existing.storage_path, "file_size": os.path.getsize(existing.storage_path) if os.path.exists(existing.storage_path) else None,
                    "report_id": existing.id, "analysis_status": existing.analysis_status}
        report = Report(patient_id=patient.id, original_filename=file.filename, stored_filename=safe_filename, storage_path=file_path, module=module, analysis_status="UPLOADED", content_sha256=content_sha256)
        db.add(report)
        try:
            db.commit()
        except Exception:
            db.rollback()
            # Do not claim persistence if metadata insertion fails.
            if os.path.exists(file_path): os.remove(file_path)
            raise
        return {
            "success": True,
            "message": "File uploaded successfully",
            "filename": safe_filename,
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "report_id": report.id,
            "analysis_status": report.analysis_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/files")
async def list_uploaded_files(patient: Patient = Depends(current_patient), db: Session = Depends(get_db)):
    """
    List all uploaded files.
    
    Returns:
        List of uploaded files
    """
    try:
        files = [{"report_id": r.id, "filename": r.original_filename, "size": os.path.getsize(r.storage_path) if os.path.exists(r.storage_path) else None, "created": r.uploaded_at.isoformat()} for r in db.query(Report).filter_by(patient_id=patient.id)]
        
        return {
            "success": True,
            "files": files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/upload/file/{filename}")
async def delete_uploaded_file(filename: str, patient: Patient = Depends(current_patient), db: Session = Depends(get_db)):
    """
    Delete an uploaded file.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        Deletion status
    """
    try:
        report = db.query(Report).filter_by(patient_id=patient.id, stored_filename=filename).one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail="File not found")
        file_path = report.storage_path
        if os.path.exists(file_path): os.remove(file_path)
        db.delete(report); db.commit()
        
        return {
            "success": True,
            "message": f"File {filename} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
