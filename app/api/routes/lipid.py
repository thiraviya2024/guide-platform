"""Backward-compatible Lipid analysis routes."""
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.lipid_service import LipidService

router = APIRouter()


class LipidValuesRequest(BaseModel):
    values: Dict[str, float]
    patient_info: Optional[Dict[str, Any]] = None


@router.post("/lipid/analyze-values")
async def analyze_lipid_values(request: LipidValuesRequest):
    try:
        return LipidService().analyze_values(request.values)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
