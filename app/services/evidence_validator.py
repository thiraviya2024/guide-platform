"""Reject provider output that contradicts canonical rule-engine evidence."""

from __future__ import annotations

import re
from typing import Any, Dict


def validate_response(text: str, evidence: Dict[str, Any]) -> bool:
    if not text or not isinstance(text, str):
        return False
    lower = text.lower()
    for name, details in evidence.get("parameters", {}).items():
        if not isinstance(details, dict):
            continue
        aliases = (name.lower(), name.replace("_", " ").lower())
        if not any(alias in lower for alias in aliases):
            continue
        expected_status = str(details.get("status", "")).lower()
        contradictory = "normal" if expected_status != "normal" else None
        if contradictory and re.search(rf"(?:{re.escape(name.replace('_', ' '))}|{re.escape(name)})[^.]*\bnormal\b", lower):
            return False
        expected_value = details.get("value")
        if expected_value is not None:
            nearby = re.search(rf"(?:{re.escape(name.replace('_', ' '))}|{re.escape(name)})[^.]*?\b(\d+(?:\.\d+)?)\b", lower)
            if nearby and float(nearby.group(1)) != float(expected_value):
                return False
    return True
