# app/api/routes/thyroid.py
"""
Thyroid API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.thyroid_service import ThyroidService

router = APIRouter()


class ThyroidRequest(BaseModel):
    """Thyroid analysis request."""
    text: str
    patient_info: Optional[Dict[str, Any]] = None


class ThyroidValuesRequest(BaseModel):
    """Thyroid values request."""
    values: Dict[str, float]
    patient_info: Optional[Dict[str, Any]] = None


@router.post("/thyroid/analyze")
async def analyze_thyroid(request: ThyroidRequest):
    """
    Analyze Thyroid from text.
    """
    try:
        service = ThyroidService()
        result = service.analyze_text(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/thyroid/analyze-values")
async def analyze_thyroid_values(request: ThyroidValuesRequest):
    """
    Analyze Thyroid values.
    """
    try:
        service = ThyroidService()
        # FIXED: Removed patient_info argument - only passing values
        result = service.analyze_values(request.values)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thyroid/reference-ranges")
async def get_thyroid_reference_ranges():
    """
    Get Thyroid reference ranges.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text
    
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT parameter, level_name, min_value, max_value, status
            FROM thyroid_rules
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
