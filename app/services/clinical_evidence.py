"""Canonical clinical evidence and bounded patient-facing fallbacks."""

from __future__ import annotations

import re
from typing import Any, Dict


_ABNORMAL_TERMS = ("high", "low", "critical", "abnormal", "elevated", "decreased")
_GREETING = {"hi", "hello", "hey"}


def is_abnormal(status: Any) -> bool:
    return bool(status) and any(term in str(status).lower() for term in _ABNORMAL_TERMS)


def build_clinical_evidence(
    analysis: Dict[str, Any],
    patient_info: Dict[str, Any] | None = None,
    report_id: str | None = None,
) -> Dict[str, Any]:
    """Build one lossless evidence shape from an existing rule-engine result."""
    results = analysis.get("results", {}) if isinstance(analysis, dict) else {}
    parameters = {
        str(name): dict(details)
        for name, details in results.items()
        if isinstance(details, dict)
    }
    abnormal = [
        {"parameter": name, **details}
        for name, details in parameters.items()
        if is_abnormal(details.get("status"))
    ]
    normal = [
        {"parameter": name, **details}
        for name, details in parameters.items()
        if not is_abnormal(details.get("status"))
    ]
    recommendations = list(dict.fromkeys(
        str(item.get("recommendation"))
        for item in abnormal
        if item.get("recommendation")
    ))
    return {
        "report_id": report_id,
        "patient_info": patient_info or {},
        "module": analysis.get("category"),
        "category": analysis.get("category"),
        "original_values": {name: details.get("value") for name, details in parameters.items()},
        "parameters": parameters,
        "results": parameters,  # Compatibility with current consumers.
        "abnormal_results": abnormal,
        "normal_results": normal,
        "doctor_review_required": bool(abnormal),
        "physician_review_required": bool(abnormal),
        "disease_risks": list(analysis.get("disease_risks", [])),
        "lifestyle_suggestions": recommendations,
        "recommendations": recommendations,
        "clinical_rules_used": analysis.get("clinical_rules_used", []),
        "overall_status": analysis.get("overall_status"),
        "report_summary": analysis.get("message"),
    }


def _parameter_for_question(evidence: Dict[str, Any], message: str) -> tuple[str, Dict[str, Any]] | None:
    words = re.sub(r"[^a-z0-9]+", " ", message.lower())
    aliases = {"ldl cholesterol": "ldl", "hdl cholesterol": "hdl", "total cholesterol": "total_cholesterol"}
    parameters = evidence.get("parameters", {})
    for alias, canonical in aliases.items():
        if alias in message.lower() and canonical in parameters:
            return canonical, parameters[canonical]
    for name, details in parameters.items():
        if name.replace("_", " ") in words and isinstance(details, dict):
            return name, details
    return None


def deterministic_chat_response(evidence: Dict[str, Any], message: str) -> str:
    """Answer safely when no LLM is available or its response is invalid."""
    text = (message or "").strip()
    normalized = text.lower().strip(" !?.")
    parameters = evidence.get("parameters", {})
    if normalized in _GREETING:
        if parameters:
            names = ", ".join(name.replace("_", " ") for name in parameters)
            return f"Hi! I can help you understand this report, including {names}."
        return "Hi! How can I help you understand your medical report?"
    if "thank" in normalized:
        return "You're welcome! Feel free to ask me about any result in your report."
    if "what can you do" in normalized:
        return "I can explain the results in your report, clarify abnormal values, and summarize the clinical recommendations."

    match = _parameter_for_question(evidence, text)
    if match:
        name, details = match
        display = name.replace("_", " ").upper() if name in {"ldl", "hdl"} else name.replace("_", " ")
        if "why" in normalized:
            recommendation = details.get("recommendation")
            suffix = f" The report recommendation is: {recommendation}" if recommendation else ""
            return f"Your {display} is {details.get('value')}, classified as {details.get('status')} in this report. The report alone does not identify a cause.{suffix}"
        return f"Your {display} is {details.get('value')}, classified as {details.get('status')} in your report."

    if "heart disease" in normalized:
        return "Your report shows cholesterol-related findings, but this report alone cannot determine whether you have heart disease. Please discuss these results with a qualified clinician."
    if "vitamin d" in normalized and "vitamin_d" not in parameters:
        return "I don't see a vitamin D result in this report, so I can't determine your vitamin D level from the available data."
    abnormal = evidence.get("abnormal_results", [])
    if "abnormal" in normalized or "concern" in normalized or "normal" in normalized:
        if not abnormal:
            return "The supplied laboratory results do not show an abnormal classification in the available rules."
        findings = "; ".join(
            f"{item.get('parameter', 'Result').replace('_', ' ')} is {item.get('status')} ({item.get('value')})"
            for item in abnormal if isinstance(item, dict)
        )
        return f"The abnormal results in this report are: {findings}. These findings are not a diagnosis; please discuss them with a qualified clinician."
    if "what should" in normalized or "recommend" in normalized:
        recommendations = evidence.get("recommendations", [])
        if recommendations:
            return "The report recommendations are: " + " ".join(recommendations)
    return "I can explain only the findings available in this report. Please ask about a listed result or recommendation."
