from datetime import date
import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.api.dependencies.auth import FirebaseLocalAccountError, create_access_token, current_user, resolve_firebase_user
from app.core.config import settings
from app.core.database import get_db
from app.database.models.domain import Doctor, Patient, User, UserRole
from app.services.firebase_auth import FirebaseAuthError, FirebaseConfigurationError

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)
# PBKDF2-SHA256 avoids the incompatible bcrypt backend currently installed
# with Python 3.13 while retaining salted, adaptive password hashing.
passwords = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: UserRole
    name: str = Field(min_length=1, max_length=255)
    specialty: str | None = None
    qualification: str | None = None
    registration_identifier: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class FirebaseLoginRequest(BaseModel):
    id_token: str = Field(min_length=1)


class DemoLoginRequest(BaseModel):
    role: UserRole


def auth_response(user: User) -> dict:
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value,
    }

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email.lower()).one_or_none()
    if not user or not passwords.verify(request.password, user.password_hash): raise HTTPException(status_code=401, detail="Invalid email or password")
    # A password is not sufficient to restore access to a deactivated account.
    # This matches the protected-route and Firebase identity behaviour.
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return auth_response(user)

@router.post("/register", status_code=201)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == request.email.lower()).first(): raise HTTPException(status_code=409, detail="Email already registered")
    if request.role == UserRole.admin: raise HTTPException(status_code=403, detail="Admin accounts cannot be self-registered")
    if request.role == UserRole.doctor and not request.specialty: raise HTTPException(status_code=422, detail="Doctor specialty is required")
    user = User(email=request.email.lower(), password_hash=passwords.hash(request.password), role=request.role)
    db.add(user); db.flush()
    if request.role == UserRole.patient: db.add(Patient(user_id=user.id, name=request.name, date_of_birth=request.date_of_birth, gender=request.gender))
    else: db.add(Doctor(user_id=user.id, name=request.name, specialty=request.specialty, qualification=request.qualification, registration_identifier=request.registration_identifier))
    db.commit(); db.refresh(user)
    return auth_response(user)


@router.post("/firebase")
async def firebase_login(request: FirebaseLoginRequest, db: Session = Depends(get_db)):
    """Exchange a verified Firebase ID token for the existing local JWT."""
    try:
        user = resolve_firebase_user(request.id_token, db)
    except FirebaseConfigurationError as exc:
        # This is a server deployment problem, not a bad user credential.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except FirebaseLocalAccountError as exc:
        # The token was verified; this is a local persistence problem.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to complete Firebase sign-in") from exc
    except FirebaseAuthError as exc:
        # Verification and account-linking failures are user authentication errors.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    try:
        return auth_response(user)
    except Exception as exc:
        # `user` exists only after Firebase verification and local lookup have
        # succeeded, so this precisely identifies local JWT construction.
        logger.error(
            "Firebase sign-in failed; stage=jwt_creation exception=%s message=%s",
            type(exc).__name__,
            "Unable to create local access token",
        )
        raise


@router.post("/demo-login")
async def demo_login(request: DemoLoginRequest, db: Session = Depends(get_db)):
    """Development-only demo identities backed by real local JWTs and rows."""
    if settings.ENVIRONMENT.lower() != "development" or not settings.ENABLE_DEMO_AUTH:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    email = f"demo.{request.role.value}@lifesaver.local"
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(
            email=email,
            password_hash=passwords.hash(secrets.token_urlsafe(48)),
            role=request.role,
            is_active=True,
        )
        db.add(user)
        db.flush()
        if request.role == UserRole.patient:
            db.add(Patient(user_id=user.id, name="Demo Patient"))
        elif request.role == UserRole.doctor:
            db.add(Doctor(user_id=user.id, name="Demo Doctor", specialty="General Medicine"))
        db.commit()
        db.refresh(user)
    elif user.role != request.role:
        raise HTTPException(status_code=409, detail="Demo account role conflict")
    elif not user.is_active:
        raise HTTPException(status_code=403, detail="Demo account is inactive")
    return auth_response(user)

@router.post("/logout")
async def logout(_: User = Depends(current_user)):
    return {"success": True, "message": "Token logout acknowledged; discard the bearer token client-side."}
