"""Optional Mistral explanation provider."""

import json
import logging
from typing import Any, Dict

import httpx

from app.core.config import settings
from app.services.llm_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class MistralProvider(BaseLLMProvider):
    name = "mistral"
    def __init__(self) -> None:
        self.api_key = settings.MISTRAL_API_KEY
        self.model = settings.MISTRAL_MODEL

    def analyze(self, context: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"success": False, "provider": self.name, "error": "Provider is not configured"}
        system = (
            "You are a medical information assistant. Use ONLY the supplied structured clinical evidence. "
            "Do not invent values, reference ranges, diagnoses, diseases, medications, treatment plans, "
            "symptoms, or history. Do not change classifications. Explain findings simply, distinguish "
            "explanation from diagnosis, and recommend clinician review when appropriate."
        )
        try:
            response = httpx.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": context},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                },
                timeout=20,
            )
            response.raise_for_status()
            return {
                "success": True,
                "provider": self.name,
                "model": self.model,
                "response": response.json()["choices"][0]["message"]["content"].strip(),
            }
        except Exception as exc:
            logger.warning("Mistral explanation unavailable: %s", exc)
            return {"success": False, "provider": self.name, "error": "Provider request failed"}

    def explain(self, evidence: Dict[str, Any]) -> str | None:
        """Legacy adapter retained for existing callers."""
        result = self.analyze(json.dumps(evidence, separators=(",", ":")))
        return result.get("response") if result.get("success") else None

    def health_check(self) -> Dict[str, Any]:
        if not self.api_key:
            return {"configured": False, "reachable": False, "status": "unconfigured", "model": self.model}
        return {"configured": True, "reachable": None, "status": "configured", "model": self.model}
