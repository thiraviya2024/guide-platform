"""Deterministic normalization and clinical evidence generation."""

from typing import Any, Dict


LIPID_RULES = {
    "total_cholesterol": {
        "unit": "mg/dL",
        "classify": lambda value: "NORMAL" if value < 200 else "BORDERLINE HIGH" if value < 240 else "HIGH",
        "reference_range": "<200 mg/dL",
    },
    "ldl_cholesterol": {
        "unit": "mg/dL",
        "classify": lambda value: "OPTIMAL" if value < 100 else "NEAR OPTIMAL" if value < 130 else "BORDERLINE HIGH" if value < 160 else "HIGH" if value < 190 else "VERY HIGH",
        "reference_range": "<130 mg/dL",
    },
    "ldl": {
        "unit": "mg/dL",
        "classify": lambda value: "OPTIMAL" if value < 100 else "NEAR OPTIMAL" if value < 130 else "BORDERLINE HIGH" if value < 160 else "HIGH" if value < 190 else "VERY HIGH",
        "reference_range": "<130 mg/dL",
    },
    "hdl_cholesterol": {
        "unit": "mg/dL",
        "classify": lambda value: "NORMAL" if value >= 40 else "LOW",
        "reference_range": ">=40 mg/dL",
    },
    "hdl": {
        "unit": "mg/dL",
        "classify": lambda value: "NORMAL" if value >= 40 else "LOW",
        "reference_range": ">=40 mg/dL",
    },
    "triglycerides": {
        "unit": "mg/dL",
        "classify": lambda value: "NORMAL" if value < 150 else "BORDERLINE HIGH" if value < 200 else "HIGH" if value < 500 else "VERY HIGH",
        "reference_range": "<150 mg/dL",
    },
}


def analyze_clinical_values(module: str, values: Dict[str, Any], patient: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return canonical evidence without calling an external service."""
    normalized_module = module.strip().lower()
    normalized_values: Dict[str, float] = {}
    parameters: Dict[str, Dict[str, Any]] = {}
    abnormal_results = []
    recommendations = []

    for name, raw_value in values.items():
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        normalized_name = name.strip().lower()
        normalized_values[normalized_name] = value
        rule = LIPID_RULES.get(normalized_name) if normalized_module == "lipid" else None
        if rule:
            status = rule["classify"](value)
            reference_range = rule["reference_range"]
            unit = rule["unit"]
        else:
            status = "Unknown"
            reference_range = None
            unit = None
        parameter = {
            "value": value,
            "status": status,
            "unit": unit,
            "reference_range": reference_range,
        }
        parameters[normalized_name] = parameter
        # The endpoint's evidence follows the same canonical definition as
        # persisted report evidence; OPTIMAL and NORMAL remain non-abnormal.
        if _is_abnormal_status(status):
            abnormal_results.append({"parameter": normalized_name, **parameter})
            recommendations.append(f"Discuss the {normalized_name.replace('_', ' ')} result with a qualified clinician.")

    return {
        "module": normalized_module,
        "parameters": parameters,
        "abnormal_results": abnormal_results,
        "physician_review_required": bool(abnormal_results),
        "patient": patient or {},
        "recommendations": list(dict.fromkeys(recommendations)),
        "possible_causes": [],
    }


def _is_abnormal_status(status: Any) -> bool:
    # Import here avoids changing this endpoint's public surface while making
    # canonical evidence the single status policy owner.
    from app.services.clinical_evidence import is_abnormal
    return is_abnormal(status)


def fallback_explanation(evidence: Dict[str, Any]) -> str:
    """Create a bounded explanation from evidence, with no diagnosis claims."""
    abnormal = evidence.get("abnormal_results", [])
    if not abnormal:
        results = evidence.get("results") or evidence.get("parameters") or {}
        abnormal = []
        for parameter_name, item in results.items():
            if isinstance(item, dict):
                status = item.get("status")
                if _is_abnormal_status(status):
                    abnormal.append({
                        "parameter": str(parameter_name),
                        "status": status,
                        "value": item.get("value"),
                        "unit": item.get("unit"),
                    })

    if not abnormal:
        return "The supplied laboratory results do not show an abnormal classification in the available rules."

    findings = "; ".join(
        f"{str(item.get('parameter', 'Result')).replace('_', ' ')} is {item.get('status')} ({item.get('value')} {item.get('unit') or ''})".strip()
        if isinstance(item, dict)
        else str(item)
        for item in abnormal
    )
    return f"The supplied results show: {findings}. These findings are not a diagnosis. Please discuss them with a qualified clinician."
