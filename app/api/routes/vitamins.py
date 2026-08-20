# app/api/routes/vitamins.py
"""
Vitamins API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.vitamins_service import VitaminsService

router = APIRouter()


class VitaminsRequest(BaseModel):
    """Vitamins analysis request."""
    text: str
    patient_info: Optional[Dict[str, Any]] = None


class VitaminsValuesRequest(BaseModel):
    """Vitamins values request."""
    values: Dict[str, float]
    patient_info: Optional[Dict[str, Any]] = None


@router.post("/vitamins/analyze")
async def analyze_vitamins(request: VitaminsRequest):
    """
    Analyze Vitamins from text.
    """
    try:
        service = VitaminsService()
        gender = request.patient_info.get('gender') if request.patient_info else None
        result = service.analyze_text(request.text, gender)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/vitamins/analyze-values")
async def analyze_vitamins_values(request: VitaminsValuesRequest):
    """
    Analyze Vitamins values.
    """
    try:
        service = VitaminsService()
        # FIXED: Removed patient_info argument - only passing values
        result = service.analyze_values(request.values)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vitamins/reference-ranges")
async def get_vitamins_reference_ranges():
    """
    Get Vitamins reference ranges.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text
    
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT parameter, level_name, min_value, max_value, status
            FROM vitamins_rules
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
