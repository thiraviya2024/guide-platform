# app/api/routes/lft.py
"""
LFT API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.lft_service import LFTService

router = APIRouter()


class LFTRequest(BaseModel):
    """LFT analysis request."""
    text: str
    patient_info: Optional[Dict[str, Any]] = None


class LFTValuesRequest(BaseModel):
    """LFT values request."""
    values: Dict[str, float]
    patient_info: Optional[Dict[str, Any]] = None


@router.post("/lft/analyze")
async def analyze_lft(request: LFTRequest):
    """
    Analyze LFT from text.
    """
    try:
        service = LFTService()
        gender = request.patient_info.get('gender') if request.patient_info else None
        result = service.analyze_text(request.text, gender)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lft/analyze-values")
async def analyze_lft_values(request: LFTValuesRequest):
    """
    Analyze LFT values.
    """
    try:
        service = LFTService()
        # FIXED: Removed patient_info argument - only passing values
        result = service.analyze_values(request.values)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lft/reference-ranges")
async def get_lft_reference_ranges():
    """
    Get LFT reference ranges.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text
    
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT parameter, level_name, min_value, max_value, status
            FROM lft_rules
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
