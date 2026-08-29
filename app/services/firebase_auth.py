"""Server-side Firebase ID-token verification.

Credentials remain in environment variables and tokens are deliberately never
logged.  The Firebase Admin app is initialized lazily and once per process.
"""
from __future__ import annotations

import base64
import json
import threading
from dataclasses import dataclass
from typing import Any

from app.core.config import settings


class FirebaseAuthError(Exception):
    """A controlled authentication/configuration error safe for API clients."""


@dataclass(frozen=True)
class FirebaseIdentity:
    uid: str
    email: str
    name: str | None
    picture: str | None
    email_verified: bool


class FirebaseAuthService:
    _lock = threading.Lock()
    _app: Any = None

    @classmethod
    def _credential_data(cls) -> dict[str, Any]:
        raw = settings.FIREBASE_SERVICE_ACCOUNT_JSON
        if not raw and settings.FIREBASE_SERVICE_ACCOUNT_BASE64:
            try:
                raw = base64.b64decode(settings.FIREBASE_SERVICE_ACCOUNT_BASE64, validate=True).decode("utf-8")
            except Exception as exc:
                raise FirebaseAuthError("Firebase service-account configuration is invalid") from exc
        if not raw:
            raise FirebaseAuthError("Firebase authentication is not configured")
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise FirebaseAuthError("Firebase service-account configuration is invalid") from exc
        if not isinstance(value, dict):
            raise FirebaseAuthError("Firebase service-account configuration is invalid")
        return value

    @classmethod
    def _get_app(cls) -> Any:
        if cls._app is not None:
            return cls._app
        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError as exc:
            raise FirebaseAuthError("Firebase authentication support is unavailable") from exc
        with cls._lock:
            if cls._app is None:
                try:
                    cls._app = firebase_admin.get_app()
                except ValueError:
                    options = {"projectId": settings.FIREBASE_PROJECT_ID} if settings.FIREBASE_PROJECT_ID else None
                    try:
                        cls._app = firebase_admin.initialize_app(credentials.Certificate(cls._credential_data()), options=options)
                    except Exception as exc:
                        raise FirebaseAuthError("Firebase authentication is not configured correctly") from exc
        return cls._app

    @classmethod
    def verify_id_token(cls, id_token: str) -> FirebaseIdentity:
        if not isinstance(id_token, str) or not id_token.strip():
            raise FirebaseAuthError("A Firebase ID token is required")
        try:
            from firebase_admin import auth
            claims = auth.verify_id_token(id_token, app=cls._get_app(), check_revoked=True)
        except FirebaseAuthError:
            raise
        except Exception as exc:
            # Do not surface provider internals or any token material.
            raise FirebaseAuthError("Invalid Firebase ID token") from exc
        uid = claims.get("uid") or claims.get("sub")
        email = claims.get("email")
        if not isinstance(uid, str) or not uid or not isinstance(email, str) or not email.strip():
            raise FirebaseAuthError("Firebase account must have an email address")
        if not claims.get("email_verified", False):
            raise FirebaseAuthError("Firebase email address must be verified")
        return FirebaseIdentity(
            uid=uid,
            email=email.strip().lower(),
            name=claims.get("name") if isinstance(claims.get("name"), str) else None,
            picture=claims.get("picture") if isinstance(claims.get("picture"), str) else None,
            email_verified=True,
        )
