# app/api/routes/cbc.py
"""
CBC API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.cbc_service import CBCService

router = APIRouter()


class CBCRequest(BaseModel):
    """CBC analysis request."""
    text: str
    patient_info: Optional[Dict[str, Any]] = None


class CBCValuesRequest(BaseModel):
    """CBC values request."""
    values: Dict[str, float]
    patient_info: Optional[Dict[str, Any]] = None


@router.post("/cbc/analyze")
async def analyze_cbc(request: CBCRequest):
    """
    Analyze CBC from text.
    """
    try:
        service = CBCService()
        gender = request.patient_info.get('gender') if request.patient_info else None
        result = service.analyze_text(request.text, gender)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cbc/analyze-values")
async def analyze_cbc_values(request: CBCValuesRequest):
    """
    Analyze CBC values.
    """
    try:
        service = CBCService()
        # FIXED: Removed gender argument - only passing values
        result = service.analyze_values(request.values)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cbc/reference-ranges")
async def get_cbc_reference_ranges():
    """
    Get CBC reference ranges.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text
    
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT parameter, level_name, min_value, max_value, status
            FROM cbc_rules
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
