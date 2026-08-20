# app/api/routes/diabetes.py
"""
Diabetes API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.diabetes_service import DiabetesService

router = APIRouter()


class DiabetesRequest(BaseModel):
    """Diabetes analysis request."""
    text: str
    patient_info: Optional[Dict[str, Any]] = None


class DiabetesValuesRequest(BaseModel):
    """Diabetes values request."""
    values: Dict[str, float]
    patient_info: Optional[Dict[str, Any]] = None


@router.post("/diabetes/analyze")
async def analyze_diabetes(request: DiabetesRequest):
    """
    Analyze Diabetes from text.
    """
    try:
        service = DiabetesService()
        result = service.analyze_text(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/diabetes/analyze-values")
async def analyze_diabetes_values(request: DiabetesValuesRequest):
    """
    Analyze Diabetes values.
    """
    try:
        service = DiabetesService()
        # FIXED: Removed patient_info argument - only passing values
        result = service.analyze_values(request.values)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diabetes/reference-ranges")
async def get_diabetes_reference_ranges():
    """
    Get Diabetes reference ranges.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text
    
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT parameter, level_name, min_value, max_value, status
            FROM diabetes_rules
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
