# app/api/routes/doctor.py
"""
Doctor Portal API Routes
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from typing import Optional, Dict, Any
from datetime import datetime
import json

from app.services.dataset_service import DatasetService

router = APIRouter()
dataset_service = DatasetService()


@router.post("/doctor/datasets/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    category: Optional[str] = Query(None, description="Report category (auto-detect if not provided)")
):
    """
    Upload Excel/CSV dataset for clinical rules.
    
    Supports: .xlsx, .xls, .csv
    
    Returns:
        Preview with column mapping for doctor confirmation
    """
    try:
        # Validate file type
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        file_extension = '.' + file.filename.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Process file
        result = dataset_service.process_upload(
            file.file,
            file.filename,
            category
        )
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', 'Processing failed'))
        
        return {
            'success': True,
            'message': 'File processed successfully',
            'data': result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/doctor/datasets/confirm")
async def confirm_dataset(
    mapping: Dict[str, str],
    category: str,
    file_path: str,
    uploaded_by: str = "doctor"
):
    """
    Confirm mapping and import dataset.
    
    Args:
        mapping: Column to parameter mapping
        category: Report category
        file_path: Path to the uploaded file
        uploaded_by: User who uploaded
    
    Returns:
        Import confirmation with version info
    """
    try:
        result = dataset_service.save_dataset(
            mapping=mapping,
            category=category,
            file_path=file_path,
            uploaded_by=uploaded_by
        )
        
        if result.get('success'):
            return {
                'success': True,
                'message': result.get('message'),
                'data': result
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Import failed'))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doctor/datasets/versions")
async def get_dataset_versions(
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get all dataset versions.
    
    Returns:
        List of versions with status
    """
    try:
        result = dataset_service.get_versions(category)
        
        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to get versions'))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/doctor/datasets/activate/{version_id}")
async def activate_version(version_id: int):
    """
    Activate a dataset version.
    
    Args:
        version_id: ID of the version to activate
    
    Returns:
        Activation confirmation
    """
    try:
        result = dataset_service.activate_version(version_id)
        
        if result.get('success'):
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Activation failed'))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/doctor/datasets/categories")
async def get_categories():
    """
    Get all available report categories.
    
    Returns:
        List of categories with parameter counts
    """
    try:
        categories = {
            'lipid': {
                'display_name': 'Lipid Profile',
                'parameters': ['total_cholesterol', 'ldl', 'hdl', 'triglycerides', 'vldl', 'non_hdl'],
                'icon': '🩸'
            },
            'cbc': {
                'display_name': 'Complete Blood Count',
                'parameters': ['hemoglobin', 'wbc', 'platelets', 'rbc', 'neutrophils', 'lymphocytes'],
                'icon': '🧬'
            },
            'lft': {
                'display_name': 'Liver Function Test',
                'parameters': ['alt', 'ast', 'alp', 'total_bilirubin', 'direct_bilirubin', 'total_protein', 'albumin', 'globulin', 'ag_ratio', 'ggt'],
                'icon': '🫀'
            },
            'kft': {
                'display_name': 'Kidney Function Test',
                'parameters': ['creatinine', 'bun', 'uric_acid', 'sodium', 'potassium', 'chloride', 'bicarbonate', 'egfr'],
                'icon': '🫘'
            },
            'thyroid': {
                'display_name': 'Thyroid Panel',
                'parameters': ['tsh', 't3', 't4', 'free_t3', 'free_t4'],
                'icon': '🦋'
            },
            'diabetes': {
                'display_name': 'Diabetes Panel',
                'parameters': ['fasting_glucose', 'hba1c', 'insulin', 'homa_ir', 'postprandial_glucose'],
                'icon': '🍬'
            },
            'vitamins': {
                'display_name': 'Vitamins Panel',
                'parameters': ['vitamin_b12', 'vitamin_d', 'folate', 'iron', 'ferritin'],
                'icon': '💊'
            },
            'electrolytes': {
                'display_name': 'Electrolytes Panel',
                'parameters': ['calcium', 'magnesium', 'phosphorus'],
                'icon': '⚡'
            }
        }
        
        return {
            'success': True,
            'categories': categories
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))