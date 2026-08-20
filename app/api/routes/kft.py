# app/api/routes/kft.py
"""
KFT API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.kft_service import KFTService

router = APIRouter()


class KFTRequest(BaseModel):
    """KFT analysis request."""
    text: str
    patient_info: Optional[Dict[str, Any]] = None


class KFTValuesRequest(BaseModel):
    """KFT values request."""
    values: Dict[str, float]
    patient_info: Optional[Dict[str, Any]] = None


@router.post("/kft/analyze")
async def analyze_kft(request: KFTRequest):
    """
    Analyze KFT from text.
    """
    try:
        service = KFTService()
        gender = request.patient_info.get('gender') if request.patient_info else None
        result = service.analyze_text(request.text, gender)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kft/analyze-values")
async def analyze_kft_values(request: KFTValuesRequest):
    """
    Analyze KFT values.
    """
    try:
        service = KFTService()
        # FIXED: Removed patient_info argument - only passing values
        result = service.analyze_values(request.values)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kft/reference-ranges")
async def get_kft_reference_ranges():
    """
    Get KFT reference ranges.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text
    
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT parameter, level_name, min_value, max_value, status
            FROM kft_rules
            WHERE is_active = TRUE
            ORDER BY parameter, min_value
        """))
        
        ranges = {}
        for row in result:
            if row.parameter not in ranges:
                ranges[row.parameter] = []
            ranges[row.parameter].append({
                'level': row.level_name,
                'min': row.min_value,
                'max': row.max_value,
                'status': row.status
            })
        
        return ranges
