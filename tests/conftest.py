"""Shared test isolation for report-analysis integration tests."""

import pytest

from app.api.routes import analyze


@pytest.fixture(autouse=True)
def unavailable_external_ai(monkeypatch):
    """Tests must not call configured external AI services.

    Provider-success behavior is covered explicitly by tests that replace this
    stub with a verified response.  Production continues to use the configured
    Groq/Gemini orchestration unchanged.
    """
    monkeypatch.setattr(
        analyze.ai_orchestrator,
        "generate_response",
        lambda evidence, message, require_provider: {
            "success": False,
            "error": "AI providers unavailable",
            "details": "test isolation",
        },
    )
