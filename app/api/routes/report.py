# app/api/routes/report.py
"""
Report API Routes
"""

from fastapi import APIRouter, HTTPException, Response, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import os
import logging

from app.services.pdf_service import PDFService
from app.services.ai_service import AIService, AIProviderUnavailable
from app.core.config import settings
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies.auth import current_patient
from app.database.models.domain import Patient, Report, ReportFinding

router = APIRouter()
logger = logging.getLogger(__name__)
pdf_service = PDFService()
ai_service = AIService()


class ReportRequest(BaseModel):
    """Report generation request."""
    patient_info: Dict[str, Any]
    results: Dict[str, Any]
    disease_risks: List[Dict[str, Any]] = []
    overall_status: str = "Normal"
    include_ai_explanation: bool = True
    include_lifestyle: bool = True


@router.post("/report/generate")
async def generate_report(request: ReportRequest):
    """
    Generate a comprehensive report with PDF and AI explanation.
    """
    try:
        # Generate AI explanation if requested
        ai_explanation = None
        lifestyle = None
        
        if request.include_ai_explanation:
            try:
                ai_explanation = ai_service.explain_results(
                    request.results,
                    request.disease_risks
                )
            except AIProviderUnavailable:
                logger.warning("Report generated without an AI explanation because providers are unavailable")
        
        if request.include_lifestyle:
            try:
                lifestyle = ai_service.generate_lifestyle_recommendations(
                    request.results
                )
            except AIProviderUnavailable:
                logger.warning("Report generated without AI lifestyle guidance because providers are unavailable")
        
        # Generate PDF
        pdf_path = pdf_service.generate_report(
            request.patient_info,
            request.results,
            request.disease_risks,
            request.overall_status,
            ai_explanation
        )
        
        return {
            "success": True,
            "message": "Report generated successfully",
            "pdf_path": pdf_path,
            "ai_explanation": ai_explanation,
            "lifestyle_recommendations": lifestyle,
            "patient_info": request.patient_info,
            "overall_status": request.overall_status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/download/{filename}")
async def download_report(filename: str, patient: Patient = Depends(current_patient), db: Session = Depends(get_db)):
    """
    Download a generated PDF report.
    """
    from fastapi.responses import FileResponse
    
    # Legacy PDF download is retained but scoped to the authenticated owner.
    report = db.query(Report).filter_by(patient_id=patient.id, stored_filename=filename).one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    file_path = report.storage_path
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )


@router.get("/reports/{report_id}/download")
async def download_persisted_report(report_id: str, patient: Patient = Depends(current_patient), db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    report = db.query(Report).filter_by(id=report_id, patient_id=patient.id).one_or_none()
    if not report or not os.path.exists(report.storage_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report.storage_path, filename=report.original_filename)


@router.post("/report/ai-explain")
async def ai_explain_results(
    report_id: str,
    patient: Patient = Depends(current_patient),
    db: Session = Depends(get_db),
):
    """
    Explain only the authenticated patient's immutable rule-engine evidence.
    Client-supplied result fields are deliberately not accepted here.
    """
    try:
        report = db.query(Report).filter_by(id=report_id, patient_id=patient.id).one_or_none()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        finding = db.query(ReportFinding).filter_by(report_id=report.id).one_or_none()
        if not finding:
            raise HTTPException(status_code=404, detail="Report analysis not found")
        evidence = finding.evidence
        explanation = ai_service.explain_results(evidence.get("results", {}), evidence.get("disease_risks", []))
        # This endpoint is allowed to regenerate an explanation, but it must
        # update the same authenticated report rather than return ephemeral AI
        # text that disappears from report history.
        report.ai_explanation = explanation
        db.commit()
        return {
            "success": True,
            "report_id": report.id,
            "explanation": explanation
        }
    except HTTPException:
        raise
    except AIProviderUnavailable as exc:
        return JSONResponse(status_code=503, content={
            "success": False,
            "error": "AI providers unavailable",
            "details": str(exc),
        })
    except Exception:
        logger.exception("Report AI explanation failed")
        return JSONResponse(status_code=502, content={
            "success": False,
            "error": "AI explanation failed",
            "details": "The AI explanation service could not complete the request.",
        })


@router.post("/report/lifestyle")
async def generate_lifestyle(results: Dict[str, Any]):
    """
    Generate AI-powered lifestyle recommendations.
    """
    try:
        recommendations = ai_service.generate_lifestyle_recommendations(results)
        return {
            "success": True,
            "recommendations": recommendations
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/report/health-summary")
async def generate_health_summary(
    patient_info: Dict[str, Any],
    results: Dict[str, Any]
):
    """
    Generate AI-powered health summary.
    """
    try:
        summary = ai_service.generate_health_summary(patient_info, results)
        return {
            "success": True,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
