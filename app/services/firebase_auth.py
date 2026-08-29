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


class FirebaseTokenError(FirebaseAuthError):
    """The supplied Firebase ID token is invalid for this Firebase project."""


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
    # A named app prevents an unrelated default Firebase app from being used
    # accidentally by this authentication boundary.
    _app_name = "life-saver-auth"

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
                    cls._app = firebase_admin.get_app(cls._app_name)
                except ValueError:
                    try:
                        project_id = cls._project_id()
                        cls._app = firebase_admin.initialize_app(
                            credentials.Certificate(cls._credential_data()),
                            options={"projectId": project_id},
                            name=cls._app_name,
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
    def _token_metadata(cls, id_token: str) -> tuple[str | None, str | None]:
        """Return only safe, untrusted JWT routing claims for diagnostics.

        This is intentionally not token verification. Firebase Admin remains
        the sole authority that authenticates signatures and expiry.
        """
        try:
            parts = id_token.split(".")
            if len(parts) != 3:
                return None, None
            payload = parts[1] + "=" * (-len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
            if not isinstance(claims, dict):
                return None, None
            issuer = claims.get("iss")
            audience = claims.get("aud")
            return issuer if isinstance(issuer, str) else None, audience if isinstance(audience, str) else None
        except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return None, None

    @classmethod
    def _log_token_failure(cls, issuer: str | None, audience: str | None, exc: Exception) -> None:
        logger.warning(
            "Firebase ID token verification failed; project=%s issuer=%s audience=%s exception=%s message=%s",
            (settings.FIREBASE_PROJECT_ID or "").strip() or "<missing>",
            issuer or "<unavailable>",
            audience or "<unavailable>",
            type(exc).__name__,
            str(exc),
        )

    @classmethod
    def verify_id_token(cls, id_token: str) -> FirebaseIdentity:
        if not isinstance(id_token, str) or not id_token.strip():
            raise FirebaseTokenError("A Firebase ID token is required")
        issuer, audience = cls._token_metadata(id_token)
        project_id = cls._project_id()
        expected_issuer = f"https://securetoken.google.com/{project_id}"
        if issuer != expected_issuer or audience != project_id:
            exc = FirebaseTokenError("Firebase token project does not match this backend")
            cls._log_token_failure(issuer, audience, exc)
            raise exc
        try:
            app = cls._get_app()
            from firebase_admin import auth
            claims = auth.verify_id_token(id_token, app=app, check_revoked=True)
        except FirebaseConfigurationError:
            raise
        except Exception as exc:
            # Do not surface provider internals or any token material to clients.
            cls._log_token_failure(issuer, audience, exc)
            raise FirebaseTokenError("Invalid Firebase ID token") from exc
        # Admin verifies these claims as part of ID-token validation. Keep the
        # explicit check as a defence-in-depth assertion and for clear logs.
        if claims.get("iss") != expected_issuer or claims.get("aud") != project_id:
            exc = FirebaseTokenError("Firebase token project does not match this backend")
            cls._log_token_failure(issuer, audience, exc)
            raise exc
        uid = claims.get("uid") or claims.get("sub")
        email = claims.get("email")
        if not isinstance(uid, str) or not uid or not isinstance(email, str) or not email.strip():
            raise FirebaseTokenError("Firebase account must have an email address")
        return FirebaseIdentity(
            uid=uid,
            email=email.strip().lower(),
            name=claims.get("name") if isinstance(claims.get("name"), str) else None,
            picture=claims.get("picture") if isinstance(claims.get("picture"), str) else None,
            # Firebase email/password sign-up does not set this claim until the
            # user completes a separate verification email flow. It is not a
            # prerequisite for exchanging a valid Firebase ID token.
            email_verified=bool(claims.get("email_verified", False)),
        )
