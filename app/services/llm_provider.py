"""Common contract used by the AI orchestrator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseLLMProvider(ABC):
    name: str

    @abstractmethod
    def analyze(self, context: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        raise NotImplementedError
