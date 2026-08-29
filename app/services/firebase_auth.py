"""Server-side Firebase ID-token verification.

Credentials remain in environment variables and tokens are deliberately never
logged.  The Firebase Admin app is initialized lazily and once per process.
"""
from __future__ import annotations

import base64
import json
import logging
import threading
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)
EXPECTED_FIREBASE_PROJECT_ID = "life-saver-93cc0"


class FirebaseAuthError(Exception):
    """A controlled authentication/configuration error safe for API clients."""


class FirebaseConfigurationError(FirebaseAuthError):
    """Firebase Admin is unavailable or its server configuration is invalid."""


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
    def _project_id(cls) -> str:
        project_id = (settings.FIREBASE_PROJECT_ID or "").strip()
        if not project_id:
            raise FirebaseConfigurationError("Firebase Admin configuration is missing")
        if project_id != EXPECTED_FIREBASE_PROJECT_ID:
            raise FirebaseConfigurationError("Firebase Admin project configuration is invalid")
        return project_id

    @classmethod
    def _credential_data(cls) -> dict[str, Any]:
        project_id = cls._project_id()
        client_email = (settings.FIREBASE_CLIENT_EMAIL or "").strip()
        # Render commonly stores PEM newlines as the two characters "\\n".
        private_key = (settings.FIREBASE_PRIVATE_KEY or "").replace("\\n", "\n")
        if client_email or private_key:
            if not client_email or not private_key.strip():
                raise FirebaseConfigurationError("Firebase Admin configuration is incomplete")
            return {
                "type": "service_account",
                "project_id": project_id,
                "private_key": private_key,
                "client_email": client_email,
                "token_uri": "https://oauth2.googleapis.com/token",
            }

        # Retain the pre-existing local development configuration options.
        raw = settings.FIREBASE_SERVICE_ACCOUNT_JSON
        if not raw and settings.FIREBASE_SERVICE_ACCOUNT_BASE64:
            try:
                raw = base64.b64decode(settings.FIREBASE_SERVICE_ACCOUNT_BASE64, validate=True).decode("utf-8")
            except Exception as exc:
                raise FirebaseConfigurationError("Firebase service-account configuration is invalid") from exc
        if not raw:
            raise FirebaseConfigurationError("Firebase Admin configuration is missing")
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise FirebaseConfigurationError("Firebase service-account configuration is invalid") from exc
        if not isinstance(value, dict):
            raise FirebaseConfigurationError("Firebase service-account configuration is invalid")
        if value.get("project_id") != project_id:
            raise FirebaseConfigurationError("Firebase Admin project configuration is invalid")
        return value

    @classmethod
    def _get_app(cls) -> Any:
        if cls._app is not None:
            return cls._app
        try:
            import firebase_admin
            from firebase_admin import credentials
        except ImportError as exc:
            raise FirebaseConfigurationError("Firebase Admin support is unavailable") from exc
        with cls._lock:
            if cls._app is None:
                try:
                    cls._app = firebase_admin.get_app()
                except ValueError:
                    try:
                        project_id = cls._project_id()
                        cls._app = firebase_admin.initialize_app(
                            credentials.Certificate(cls._credential_data()),
                            options={"projectId": project_id},
                        )
                        logger.info("Firebase Admin initialized for project: %s", project_id)
                    except Exception as exc:
                        project_id = (settings.FIREBASE_PROJECT_ID or "").strip() or "<missing>"
                        logger.error(
                            "Firebase Admin initialization failed for project %s; %s: %s",
                            project_id,
                            type(exc).__name__,
                            str(exc),
                        )
                        raise FirebaseConfigurationError("Firebase Admin initialization failed") from exc
                if getattr(cls._app, "project_id", None) != cls._project_id():
                    raise FirebaseConfigurationError("Firebase Admin project configuration is invalid")
        return cls._app

    @classmethod
    def verify_id_token(cls, id_token: str) -> FirebaseIdentity:
        if not isinstance(id_token, str) or not id_token.strip():
            raise FirebaseAuthError("A Firebase ID token is required")
        try:
            from firebase_admin import auth
            claims = auth.verify_id_token(id_token, app=cls._get_app(), check_revoked=True)
        except FirebaseConfigurationError:
            raise
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
