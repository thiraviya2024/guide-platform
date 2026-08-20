from pydantic import BaseModel 
from typing import Optional, Dict, Any, List 
 
class LipidValues(BaseModel): 
    total_cholesterol: Optional[float] = None 
    ldl: Optional[float] = None 
    hdl: Optional[float] = None 
    triglycerides: Optional[float] = None 
    vldl: Optional[float] = None 
    non_hdl: Optional[float] = None 
 
class ManualEntryRequest(BaseModel): 
    lipid_values: LipidValues 
    patient_info: Optional[Dict[str, Any]] = None 
 
class AnalysisResponse(BaseModel): 
    success: bool 
    message: str 
    parameters: List[Dict[str, Any]] 
    combination_findings: List[Dict[str, Any]] 
    disease_predictions: List[Dict[str, Any]] 
    overall_risk: str 
    risk_score: float 
    mimic_evidence: Dict[str, Any] 
    ai_explanation: Dict[str, str] 
    confidence_score: Dict[str, Any] 
