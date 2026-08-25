"""Deterministic clinical analysis API."""

from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.clinical_analysis import analyze_clinical_values

router = APIRouter(prefix="/clinical", tags=["Clinical"])


class ClinicalAnalysisRequest(BaseModel):
    module: str = Field(..., min_length=1)
    results: Dict[str, Any] = Field(..., min_length=1)
    patient: Optional[Dict[str, Any]] = None


@router.post("/analyze")
async def analyze_clinical(request: ClinicalAnalysisRequest) -> Dict[str, Any]:
    return analyze_clinical_values(request.module, request.results, request.patient)
