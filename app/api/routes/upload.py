# app/api/routes/upload.py
"""
Upload API Routes
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import os
import shutil
from datetime import datetime

router = APIRouter()


@router.post("/upload/report")
async def upload_report(
    file: UploadFile = File(...),
    patient_id: Optional[str] = None
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(file.filename)[1]
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "message": "File uploaded successfully",
            "filename": safe_filename,
            "file_path": file_path,
            "file_size": os.path.getsize(file_path),
            "patient_id": patient_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload/files")
async def list_uploaded_files():
    """
    List all uploaded files.
    
    Returns:
        List of uploaded files
    """
    try:
        upload_dir = "uploads"
        if not os.path.exists(upload_dir):
            return {"success": True, "files": []}
        
        files = []
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            files.append({
                "filename": filename,
                "size": os.path.getsize(file_path),
                "created": datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
            })
        
        return {
            "success": True,
            "files": files
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/upload/file/{filename}")
async def delete_uploaded_file(filename: str):
    """
    Delete an uploaded file.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        Deletion status
    """
    try:
        file_path = os.path.join("uploads", filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        os.remove(file_path)
        
        return {
            "success": True,
            "message": f"File {filename} deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))