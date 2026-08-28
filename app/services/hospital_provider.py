"""Small adapter boundary for an externally configured hospital directory."""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class HospitalProviderUnavailable(RuntimeError):
    pass


class HospitalProviderError(RuntimeError):
    pass


class ConfiguredHospitalProvider:
    """Call a real provider and expose only data returned by that provider.

    Providers are expected to return either a list or ``{"items": [...]}``.
    Each item is left intact, except non-object items are rejected as an
    integration error rather than being converted into invented hospitals.
    """

    def search(self, latitude: float, longitude: float, specialty: str | None) -> list[dict[str, Any]]:
        if not settings.HOSPITAL_PROVIDER_URL:
            raise HospitalProviderUnavailable("Hospital search provider is not configured")
        headers = {"Accept": "application/json"}
        if settings.HOSPITAL_PROVIDER_API_KEY:
            headers["Authorization"] = f"Bearer {settings.HOSPITAL_PROVIDER_API_KEY}"
        try:
            response = httpx.get(
                settings.HOSPITAL_PROVIDER_URL,
                params={"latitude": latitude, "longitude": longitude, "specialty": specialty},
                headers=headers,
                timeout=settings.HOSPITAL_PROVIDER_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HospitalProviderError("Hospital provider request failed") from exc
        items = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise HospitalProviderError("Hospital provider returned an unsupported response")
        return items
