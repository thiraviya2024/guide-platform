# app/models/schemas/analysis_schema.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LipidValues(BaseModel):
    total_cholesterol: Optional[float] = Field(None, ge=0, le=1000)
    ldl: Optional[float] = Field(None, ge=0, le=500)
    hdl: Optional[float] = Field(None, ge=0, le=200)
    triglycerides: Optional[float] = Field(None, ge=0, le=2000)
    vldl: Optional[float] = Field(None, ge=0, le=200)
    non_hdl: Optional[float] = Field(None, ge=0, le=500)


class ManualEntryRequest(BaseModel):
    lipid_values: LipidValues
    patient_info: Optional[Dict[str, Any]] = None


class LipidAnalysisRequest(BaseModel):
    lipid_values: LipidValues
    patient_info: Optional[Dict[str, Any]] = None


class BloodTestRequest(BaseModel):
    text: str = Field(..., min_length=5)
    patient_info: Optional[Dict[str, Any]] = None


class AnalysisResponse(BaseModel):
    success: bool
    message: str
    overall_risk: Optional[str] = None
    parameters: Optional[List[Dict[str, Any]]] = None
    combination_findings: Optional[List[Dict[str, Any]]] = None
    disease_predictions: Optional[List[Dict[str, Any]]] = None
    categorized_results: Optional[Dict[str, List[Dict[str, Any]]]] = None
    recommendations: Optional[Dict[str, Any]] = None
    evidence: Optional[Dict[str, Any]] = None
    ai_explanation: Optional[Dict[str, str]] = None
    risk_score: Optional[float] = None
    confidence_score: Optional[Dict[str, Any]] = None
    mimic_evidence: Optional[Dict[str, Any]] = None
