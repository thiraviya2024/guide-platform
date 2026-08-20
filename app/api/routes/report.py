# app/api/routes/report.py
"""
Report API Routes
"""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import os

from app.services.pdf_service import PDFService
from app.services.ai_service import AIService
from app.core.config import settings

router = APIRouter()
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
            except Exception as e:
                ai_explanation = "AI explanation unavailable. Please consult your healthcare provider."
        
        if request.include_lifestyle:
            try:
                lifestyle = ai_service.generate_lifestyle_recommendations(
                    request.results
                )
            except Exception as e:
                lifestyle = "Lifestyle recommendations unavailable."
        
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
async def download_report(filename: str):
    """
    Download a generated PDF report.
    """
    from fastapi.responses import FileResponse
    
    file_path = f"reports/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Report not found")
    
    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=filename
    )


@router.post("/report/ai-explain")
async def ai_explain_results(
    results: Dict[str, Any], 
    disease_risks: List[Dict[str, Any]] = []
):
    """
    Get AI explanation for test results.
    """
    try:
        explanation = ai_service.explain_results(results, disease_risks)
        return {
            "success": True,
            "explanation": explanation
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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