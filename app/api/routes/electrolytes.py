# app/api/routes/electrolytes.py
"""
Electrolytes API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.services.electrolytes_service import ElectrolytesService

router = APIRouter()


class ElectrolytesRequest(BaseModel):
    """Electrolytes analysis request."""
    text: str
    patient_info: Optional[Dict[str, Any]] = None


class ElectrolytesValuesRequest(BaseModel):
    """Electrolytes values request."""
    values: Dict[str, float]
    patient_info: Optional[Dict[str, Any]] = None


@router.post("/electrolytes/analyze")
async def analyze_electrolytes(request: ElectrolytesRequest):
    """
    Analyze Electrolytes from text.
    """
    try:
        service = ElectrolytesService()
        result = service.analyze_text(request.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/electrolytes/analyze-values")
async def analyze_electrolytes_values(request: ElectrolytesValuesRequest):
    """
    Analyze Electrolytes values.
    """
    try:
        service = ElectrolytesService()
        # FIXED: Removed patient_info argument - only passing values
        result = service.analyze_values(request.values)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/electrolytes/reference-ranges")
async def get_electrolytes_reference_ranges():
    """
    Get Electrolytes reference ranges.
    """
    from app.core.database import SessionLocal
    from sqlalchemy import text
    
    with SessionLocal() as db:
        result = db.execute(text("""
            SELECT parameter, level_name, min_value, max_value, status
            FROM electrolytes_rules
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
