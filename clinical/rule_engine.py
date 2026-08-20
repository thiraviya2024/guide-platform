# clinical/rule_engine.py
"""
PostgreSQL-based Rule Engine for LipidAI.
All medical thresholds come from the database.

Fixed from the original rule_engine_pg.py: opens a fresh SQLAlchemy
Session per query (and always closes it) instead of one Session held
open for the entire life of the singleton. A long-lived shared Session
is not thread-safe under Streamlit's concurrent users and leaves
"idle in transaction" connections open on the Postgres side, which can
block doctor-side UPDATEs and eventually time out.

Renamed from rule_engine_pg.py -> rule_engine.py and get_pg_rule_engine()
-> get_rule_engine() (get_pg_rule_engine kept as an alias below) to match
the existing API contract (`from clinical.rule_engine import rule_engine`)
so app.py needs no import changes.
"""

from typing import Dict, Any

from sqlalchemy import text

from database.connection import SessionLocal
from utils.logger import logger


class PostgresRuleEngine:
    """
    Stateless with respect to database connections: no Session is held on
    `self`. Each evaluate() call opens its own short-lived Session via a
    context manager and closes it immediately after, which is what makes
    this instance safe to share as a singleton across concurrent
    Streamlit users/threads.
    """

    def evaluate(self, lipid_values: Dict[str, float]) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate lipid values using rules from PostgreSQL.
        """
        results: Dict[str, Dict[str, Any]] = {}

        query = text(
            """
            SELECT status, recommendation, food_suggestions
            FROM lipid_rules
            WHERE parameter = :param
              AND min_value <= :value
              AND max_value >= :value
              AND is_active = TRUE
            ORDER BY id
            LIMIT 1
            """
        )

        # One Session for this whole evaluate() call (covers all
        # parameters in the report), opened fresh and closed at the end --
        # never held across separate evaluate() calls or shared instances.
        with SessionLocal() as db:
            for param, value in lipid_values.items():
                try:
                    numeric_value = float(value)
                except (TypeError, ValueError):
                    results[param] = {
                        "value": value,
                        "status": "Unknown",
                        "recommendation": "No rule found",
                        "food": "",
                    }
                    continue

                try:
                    row = db.execute(query, {"param": param, "value": numeric_value}).fetchone()
                except Exception as exc:  # noqa: BLE001
                    logger.error(f"RuleEngine: query failed for '{param}'={numeric_value}: {exc}")
                    db.rollback()
                    results[param] = {
                        "value": numeric_value,
                        "status": "Unknown",
                        "recommendation": "No rule found",
                        "food": "",
                    }
                    continue

                if row:
                    results[param] = {
                        "value": numeric_value,
                        "status": row.status,
                        "recommendation": row.recommendation,
                        "food": row.food_suggestions or "",
                    }
                else:
                    logger.warning(f"RuleEngine: no matching rule for '{param}'={numeric_value}")
                    results[param] = {
                        "value": numeric_value,
                        "status": "Unknown",
                        "recommendation": "No rule found",
                        "food": "",
                    }

        return results


# ---------------------------------------------------------------------- #
# Singleton -- safe now, because PostgresRuleEngine no longer holds a
# Session on self; every evaluate() call manages its own short-lived one.
# ---------------------------------------------------------------------- #
_pg_engine: "PostgresRuleEngine | None" = None


def get_rule_engine() -> PostgresRuleEngine:
    global _pg_engine
    if _pg_engine is None:
        _pg_engine = PostgresRuleEngine()
    return _pg_engine


# Backward-compatible alias for your original name.
get_pg_rule_engine = get_rule_engine

# Module-level instance, matching the `from clinical.rule_engine import
# rule_engine` import style already used elsewhere in the project.
rule_engine = get_rule_engine()