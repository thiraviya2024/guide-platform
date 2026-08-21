"""Persist verified report findings for follow-up AI chat."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.core.database import SessionLocal

_CONTEXT_PROVIDER = "context"
_CONTEXT_MODEL = "report-context"


def save_report_context(context: Dict[str, Any]) -> str:
    """Persist structured rule-engine findings and return a reusable context ID."""
    context_id = str(uuid.uuid4())
    payload = json.dumps(context, default=str)

    with SessionLocal() as db:
        db.execute(
            text(
                """
                INSERT INTO ai_analysis_logs
                    (analysis_id, model_provider, model_name, input_data,
                     output_data, confidence, response_time_ms, created_at)
                VALUES
                    (:analysis_id, :provider, :model, CAST(:payload AS jsonb),
                     CAST(:payload AS jsonb), :confidence, :response_time_ms, NOW())
                """
            ),
            {
                "analysis_id": context_id,
                "provider": _CONTEXT_PROVIDER,
                "model": _CONTEXT_MODEL,
                "payload": payload,
                "confidence": 1.0,
                "response_time_ms": 0,
            },
        )
        db.commit()

    return context_id


def load_report_context(context_id: str) -> Optional[Dict[str, Any]]:
    """Load a previously persisted report context by ID."""
    with SessionLocal() as db:
        row = db.execute(
            text(
                """
                SELECT input_data
                FROM ai_analysis_logs
                WHERE analysis_id = :analysis_id
                  AND model_provider = :provider
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"analysis_id": context_id, "provider": _CONTEXT_PROVIDER},
        ).fetchone()

    if not row or not row.input_data:
        return None
    return dict(row.input_data)
