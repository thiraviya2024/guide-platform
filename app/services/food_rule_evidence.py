"""Retrieve existing food-rule records for verified report evidence."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


_STOP_WORDS = {"cholesterol", "result", "results", "level", "levels", "risk", "risks"}


def _words(value: Any) -> set[str]:
    return {
        word.rstrip("s")
        for word in re.findall(r"[a-z0-9]+", str(value).lower())
        if len(word) > 1 and word.rstrip("s") not in _STOP_WORDS
    }


def food_rules_for_evidence(db: Session, evidence: dict[str, Any]) -> list[dict[str, str]]:
    """Match active database food rules to report risks and abnormal findings.

    The existing schema stores disease-level rule names rather than a module or
    parameter foreign key. Matching therefore uses the rule names already
    present in report evidence; recommendation text always comes from the DB.
    """
    risk_names = [
        str(item.get("disease"))
        for item in evidence.get("disease_risks", [])
        if isinstance(item, dict) and item.get("disease")
    ]
    abnormal_terms = [
        f"{item.get('status', '')} {item.get('parameter', '')}"
        for item in evidence.get("abnormal_results", [])
        if isinstance(item, dict)
    ]
    if not risk_names and not abnormal_terms:
        return []

    rows = db.execute(
        text(
            "SELECT disease_name, food_suggestions FROM food_rules "
            "WHERE is_active = TRUE ORDER BY id"
        )
    ).mappings()
    matches: list[dict[str, str]] = []
    for row in rows:
        rule_name = str(row["disease_name"])
        rule_words = _words(rule_name)
        category = None
        if any(rule_name.casefold() == risk.casefold() for risk in risk_names):
            category = "disease_risk"
        elif any(_words(term) and _words(term).issubset(rule_words) for term in abnormal_terms):
            category = "abnormal_finding"
        if category:
            matches.append(
                {
                    "category": category,
                    "rule_name": rule_name,
                    "food_suggestions": str(row["food_suggestions"]),
                }
            )
    return matches
