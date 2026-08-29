"""Report-grounded AI routes."""

from datetime import datetime
import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies.auth import current_patient
from app.core.database import get_db
from app.database.models.domain import Patient, Report, ReportFinding
from app.services.ai_orchestrator import AIOrchestrator
from app.services.clinical_evidence import build_clinical_evidence, is_abnormal
from app.services.food_rule_evidence import food_rules_for_evidence

router = APIRouter()
ai_orchestrator = AIOrchestrator()
logger = logging.getLogger(__name__)


def _is_intake_history_question(message: str) -> bool:
    text = message.casefold()
    return "intake" in text or bool(
        re.search(r"\b(?:did|have)\b.{0,30}\b(?:eat|ate|eating)\b", text)
    )


def _is_food_recommendation_question(message: str) -> bool:
    text = message.casefold()
    food_terms = ("food", "foods", "diet", "eat", "eating", "avoid", "limit")
    request_terms = ("should", "good", "recommend", "recommendation", "avoid", "limit", "what")
    return not _is_intake_history_question(message) and any(term in text for term in food_terms) and any(
        term in text for term in request_terms
    )


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
async def analyze_with_ai(
    data: Dict[str, Any],
    patient: Patient = Depends(current_patient),
    db: Session = Depends(get_db),
):
    """Answer from the authenticated patient's current persisted report only."""
    message = str(data.get("message") or data.get("prompt") or "")
    requested_report_id = data.get("report_id") or data.get("report_context_id")
    if _is_intake_history_question(message):
        logger.info("AI chat report_context=not_needed reason=intake_history_question")
        return {
            "success": True,
            "response": "I do not have a record of what you ate. I can provide report-based food recommendations when a current report is available.",
            "report_id": None,
            "provider": "deterministic",
        }

    query = db.query(Report, ReportFinding).join(ReportFinding, ReportFinding.report_id == Report.id).filter(
        Report.patient_id == patient.id
    )
    if requested_report_id:
        report_and_finding = query.filter(Report.id == requested_report_id).one_or_none()
    else:
        report_and_finding = query.order_by(Report.uploaded_at.desc()).first()
    if report_and_finding is None:
        logger.info("AI chat report_context=not_found requested=%s", bool(requested_report_id))
        # A requested report ID must resolve within this patient's records;
        # do not silently substitute a different current report.
        if requested_report_id:
            raise HTTPException(status_code=404, detail="Report context not found")
        if _is_food_recommendation_question(message):
            return {
                "success": True,
                "response": "I do not have a current report to match with database food recommendations.",
                "report_id": None,
                "provider": "deterministic",
            }
        raise HTTPException(status_code=404, detail="Report context not found")

    report, finding = report_and_finding
    evidence = _normalise_evidence(dict(finding.evidence))
    evidence["report_id"] = report.id
    evidence["module"] = evidence.get("module") or report.module
    if _is_food_recommendation_question(message):
        evidence["food_rules"] = food_rules_for_evidence(db, evidence)
    else:
        evidence["food_rules"] = []
    categories = sorted({item["category"] for item in evidence["food_rules"]})
    logger.info(
        "AI chat report_context=found module=%s abnormal_count=%s food_rule_count=%s food_rule_categories=%s evidence_keys=%s",
        evidence.get("module"),
        len(evidence.get("abnormal_results", [])),
        len(evidence["food_rules"]),
        categories,
        sorted(key for key in evidence if key not in {"patient_info", "original_values", "parameters", "results"}),
    )
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
    report_id = report.id
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
