"""Report-grounded AI routes."""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.services.ai_orchestrator import AIOrchestrator
from app.services.clinical_evidence import build_clinical_evidence, is_abnormal
from app.services.report_context import load_report_context

router = APIRouter()
ai_orchestrator = AIOrchestrator()


def _normalise_evidence(data: Dict[str, Any]) -> Dict[str, Any]:
    """Accept legacy result payloads without discarding their rule evidence."""
    if data.get("parameters") and data.get("abnormal_results") is not None:
        evidence = dict(data)
        evidence.setdefault("results", evidence["parameters"])
        evidence.setdefault("doctor_review_required", bool(evidence["abnormal_results"]))
        evidence.setdefault("physician_review_required", evidence["doctor_review_required"])
        evidence.setdefault("recommendations", [
            value.get("recommendation") for value in evidence["parameters"].values()
            if isinstance(value, dict) and is_abnormal(value.get("status")) and value.get("recommendation")
        ])
        return evidence
    analysis = {
        "results": data.get("results", data.get("parameters", {})),
        "disease_risks": data.get("disease_risks", []),
        "category": data.get("category", data.get("module")),
        "overall_status": data.get("overall_status"),
        "message": data.get("report_summary"),
    }
    return build_clinical_evidence(analysis, data.get("patient_info", {}), data.get("report_id"))


def _abnormal_labels(evidence: Dict[str, Any]) -> list[str]:
    return [
        f"{item.get('parameter', 'Result').upper()} is {item.get('status')} ({item.get('value')})"
        for item in evidence.get("abnormal_results", []) if isinstance(item, dict)
    ]


@router.get("/ai/status")
async def get_ai_status():
    providers = ai_orchestrator.provider_status()
    initialized = sum(1 for item in providers.values() if item.get("initialized"))
    reachable = sum(1 for item in providers.values() if item.get("reachable") is True)
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "orchestrator": "active",
        "providers": providers,
        "total_providers": len(providers),
        # Backward-compatible field: active means a provider SDK was actually
        # initialized, not merely that an environment variable exists.
        "active_providers": initialized,
        "initialized_providers": initialized,
        "reachable_providers": reachable,
    }


@router.post("/ai/analyze")
async def analyze_with_ai(data: Dict[str, Any]):
    context_id = data.get("report_id") or data.get("report_context_id")
    persisted = load_report_context(context_id) if context_id else None
    if context_id and persisted is None:
        raise HTTPException(status_code=404, detail="Report context not found")

    source = persisted or data.get("evidence") or data
    evidence = _normalise_evidence(source)
    message = str(data.get("message") or data.get("prompt") or "")
    generated = ai_orchestrator.generate_response(evidence, message, require_provider=True)
    if not generated.get("success"):
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": generated.get("error", "AI providers unavailable"),
                "details": generated.get("details", "No provider returned a usable response"),
            },
        )
    report_id = context_id or evidence.get("report_id")
    abnormal_results = _abnormal_labels(evidence)
    return {
        "success": True,
        "response": generated["response"],
        "explanation": generated["response"],
        "report_id": report_id,
        "provider": generated["provider"],
        "parameters": evidence.get("parameters", {}),
        "abnormal_results": abnormal_results,
        "doctor_review_required": bool(evidence.get("doctor_review_required")),
        "summary": generated["response"],
        "ai_explanation": generated["response"],
        "possible_causes": evidence.get("disease_risks", []),
        "lifestyle_suggestions": evidence.get("recommendations", []),
        "disclaimer": "This explanation is informational and is not a diagnosis or treatment plan.",
    }


@router.post("/ai/consensus")
async def get_consensus(data: Dict[str, Any]):
    evidence = _normalise_evidence(data.get("evidence") or data)
    return {"success": True, "consensus": ai_orchestrator.analyze(evidence)}


@router.get("/ai/audit-logs")
async def get_audit_logs(limit: int = Query(50, ge=1, le=500), skip: int = Query(0, ge=0), provider: Optional[str] = None):
    """Compatibility endpoint; audit persistence remains owned by database workflows."""
    return {"success": True, "logs": [], "total": 0, "limit": limit, "skip": skip, "provider": provider}
