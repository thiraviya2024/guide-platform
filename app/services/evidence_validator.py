"""Reject provider output that contradicts canonical rule-engine evidence."""

from __future__ import annotations

import re
from typing import Any, Dict


_STATUS_PATTERN = re.compile(
    r"\b(?:VERY\s+HIGH|BORDERLINE\s+HIGH|NEAR\s+OPTIMAL|OPTIMAL|NORMAL|HIGH|LOW|CRITICAL)\b",
    re.IGNORECASE,
)


def _normalise_status(status: Any) -> str:
    return " ".join(str(status or "").upper().split())


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
        expected_status = _normalise_status(details.get("status"))
        # A provider may omit a classification when answering a narrow
        # question, but if it states one for a named parameter it must be the
        # exact deterministic status in the persisted evidence.
        for alias in aliases:
            match = re.search(rf"{re.escape(alias)}[^.;\n]*", lower, re.IGNORECASE)
            if match:
                stated_statuses = {
                    _normalise_status(item.group(0))
                    for item in _STATUS_PATTERN.finditer(match.group(0))
                }
                if any(status != expected_status for status in stated_statuses):
                    return False
        expected_value = details.get("value")
        if expected_value is not None:
            nearby = re.search(rf"(?:{re.escape(name.replace('_', ' '))}|{re.escape(name)})[^.]*?\b(\d+(?:\.\d+)?)\b", lower)
            if nearby and float(nearby.group(1)) != float(expected_value):
                return False
    return True
