# app/api/routes/ai.py
"""
AI Orchestrator API Routes
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.services.ai_orchestrator import AIOrchestrator
from app.core.config import settings
from app.services.response_sanitizer import sanitize_model_output
from app.services.report_context import load_report_context

logger = logging.getLogger(__name__)
router = APIRouter()
ai_orchestrator = AIOrchestrator()

_FACTUAL_FIELDS = {
    "test_name", "name", "parameter", "value", "unit", "reference_range",
    "ref_range", "status", "flag", "calculated_value", "calculated_values",
    "risk", "risks", "finding", "findings", "disease", "confidence",
    "severity", "recommendation", "reason", "food", "category"
}


def _factual_evidence(value: Any) -> Any:
    """Keep only factual clinical fields before evidence reaches an LLM."""
    if isinstance(value, dict):
        return {
            key: _factual_evidence(item)
            for key, item in value.items()
            if key in _FACTUAL_FIELDS or isinstance(item, (dict, list))
        }
    if isinstance(value, list):
        return [_factual_evidence(item) for item in value]
    return value


def _clinical_evidence(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "patient_info": _factual_evidence({
            key: data.get("patient_info", {}).get(key)
            for key in ("age", "gender")
            if key in data.get("patient_info", {})
        }),
        "results": _factual_evidence(data.get("results", {})),
        "disease_risks": _factual_evidence(data.get("disease_risks", [])),
        "prompt": data.get("prompt", "")
    }


def _chat_evidence(data: Dict[str, Any]) -> Dict[str, Any]:
    """Use persisted rule findings when chat sends a report context ID."""
    context_id = data.get("report_context_id")
    persisted = load_report_context(context_id) if context_id else None
    source = persisted or data
    return {
        "patient_info": _factual_evidence(source.get("patient_info", {})),
        "results": _factual_evidence(source.get("results", {})),
        "disease_risks": _factual_evidence(source.get("disease_risks", [])),
        "overall_status": source.get("overall_status"),
        "category": source.get("category"),
        "prompt": data.get("prompt", ""),
        "report_context_id": context_id,
    }


@router.get("/ai/status")
async def get_ai_status():
    """Get AI provider status."""
    try:
        status = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "orchestrator": "active",
            "providers": {
                "groq": {
                    "status": "online" if settings.GROQ_API_KEY else "offline",
                    "model": settings.GROQ_MODEL,
                    "api_key_configured": bool(settings.GROQ_API_KEY)
                },
                "gemini": {
                    "status": "online" if settings.GEMINI_API_KEY else "offline",
                    "model": settings.GEMINI_MODEL or "models/gemini-2.5-flash",
                    "api_key_configured": bool(settings.GEMINI_API_KEY)
                }
            },
            "total_providers": 2,
            "active_providers": sum([
                1 if settings.GROQ_API_KEY else 0,
                1 if settings.GEMINI_API_KEY else 0
            ])
        }
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/analyze")
async def analyze_with_ai(data: Dict[str, Any]):
    """
    Run AI analysis using Groq + Gemini.
    
    Expected input:
    {
        "prompt": "Who are you?",
        "context": "Optional context from report",
        "patient_info": {...},
        "results": {...},
        "disease_risks": [...]
    }
    """
    try:
        # Extract data
        clinical_data = _chat_evidence(data)
        
        # Call AI Orchestrator
        response = ai_orchestrator.analyze(clinical_data)
        
        if response.get("success"):
            return {
                "success": True,
                "response": sanitize_model_output(response.get("final_response", {}).get("text", "")),
                "provider": response.get("models_used", []),
                "agreement_score": response.get("agreement_score", 0),
                "physician_review_required": response.get("physician_review_required", False),
                "report_context_id": clinical_data.get("report_context_id")
            }
        else:
            # Fallback: If AI Orchestrator fails, try direct Groq call
            if settings.GROQ_API_KEY:
                from app.services.groq_provider import GroqProvider
                groq = GroqProvider()
                
                # Build context
                full_context = str(clinical_data)
                
                groq_response = groq.analyze(full_context)
                if groq_response.get("success"):
                    return {
                        "success": True,
                        "response": sanitize_model_output(groq_response.get("response", "")),
                        "provider": ["groq"],
                        "agreement_score": 1.0,
                        "physician_review_required": False
                    }
            
            return {
                "success": False,
                "error": "No AI providers available",
                "message": "AI analysis failed. Please try again later."
            }
            
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "AI analysis failed"
        }


@router.post("/ai/consensus")
async def get_consensus(data: Dict[str, Any]):
    """Get consensus between AI models."""
    try:
        result = ai_orchestrator.analyze(data)
        return {
            "success": True,
            "consensus": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai/audit-logs")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    skip: int = Query(0, ge=0),
    provider: Optional[str] = None
):
    """Get AI audit logs."""
    try:
        from app.core.database import SessionLocal
        from sqlalchemy import text
        
        with SessionLocal() as db:
            query = """
                SELECT analysis_id, model_provider, model_name, 
                       confidence, response_time_ms, created_at
                FROM ai_analysis_logs
            """
            params = {}
            
            if provider:
                query += " WHERE model_provider = :provider"
                params['provider'] = provider
            
            query += " ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
            params['limit'] = limit
            params['skip'] = skip
            
            result = db.execute(text(query), params)
            
            logs = []
            for row in result:
                logs.append({
                    'analysis_id': row[0],
                    'provider': row[1],
                    'model': row[2],
                    'confidence': row[3],
                    'response_time_ms': row[4],
                    'created_at': row[5].isoformat() if row[5] else None
                })
            
            count_query = "SELECT COUNT(*) FROM ai_analysis_logs"
            if provider:
                count_query += " WHERE model_provider = :provider"
            
            total = db.execute(text(count_query), {'provider': provider} if provider else {}).fetchone()[0]
            
            return {
                "success": True,
                "logs": logs,
                "total": total,
                "limit": limit,
                "skip": skip
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
