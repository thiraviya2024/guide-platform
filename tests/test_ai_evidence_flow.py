import pytest

from app.api.routes.ai import _normalise_evidence, ai_orchestrator


def test_normalise_evidence_keeps_rule_engine_abnormal_findings(monkeypatch):
    monkeypatch.setattr(ai_orchestrator, "providers", {})
    payload = {
        "prompt": "Explain these liver test results in simple language.",
        "context": "LFT analysis completed.",
        "patient_info": {},
        "results": {
            "alt": {
                "value": 75,
                "status": "High",
                "recommendation": "Mild ALT elevation. May indicate liver damage. Consult physician."
            },
            "ast": {
                "value": 65,
                "status": "High",
                "recommendation": "Mild AST elevation. May indicate liver or heart damage. Consult physician."
            },
            "alp": {
                "value": 140,
                "status": "Normal",
                "recommendation": "Good result."
            }
        },
        "disease_risks": [
            {
                "disease": "Hepatitis",
                "confidence": "High",
                "reason": "Elevated ALT and AST (liver enzymes)",
                "recommendation": "Check for viral hepatitis (A, B, C) and autoimmune hepatitis"
            }
        ]
    }

    evidence = _normalise_evidence(payload)
    assert evidence["parameters"]["alt"]["status"] == "High"
    assert len(evidence["abnormal_results"]) == 2
