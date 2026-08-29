from datetime import datetime, timedelta, timezone
from typing import Callable
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext

from app.core.config import settings
from app.core.database import get_db
from app.database.models.domain import Doctor, Patient, User, UserRole
from app.services.firebase_auth import FirebaseAuthError, FirebaseAuthService, FirebaseIdentity

bearer = HTTPBearer(auto_error=False)
passwords = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def create_access_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user.id, "role": user.role.value, "exp": exp}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def _firebase_user(identity: FirebaseIdentity, db: Session) -> User:
    """Resolve a verified Firebase identity without trusting client role data."""
    # Keep the persistence boundary normalized even when this helper is called
    # by a trusted internal verifier other than FirebaseAuthService.
    email = identity.email.strip().lower()
    user = db.query(User).filter(User.firebase_uid == identity.uid).one_or_none()
    if user is None:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user is not None:
            if user.firebase_uid and user.firebase_uid != identity.uid:
                raise FirebaseAuthError("Firebase account is not linked to this user")
            # Linking retains local ID, role, password hash, and profiles.
            user.firebase_uid = identity.uid
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise FirebaseAuthError("Firebase account is already linked") from exc
        else:
            # Firebase cannot create elevated identities.  The random stored
            # hash makes password login unavailable until explicitly managed.
            user = User(
                email=email,
                firebase_uid=identity.uid,
                password_hash=passwords.hash(secrets.token_urlsafe(48)),
                role=UserRole.patient,
                is_active=True,
            )
            db.add(user)
            db.flush()
            display_name = (identity.name or email.split("@", 1)[0]).strip()[:255] or "Firebase patient"
            db.add(Patient(user_id=user.id, name=display_name))
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                raise FirebaseAuthError("Unable to create Firebase user") from exc
    if not user.is_active:
        raise FirebaseAuthError("Firebase account is inactive")
    return user


def resolve_firebase_user(id_token: str, db: Session) -> User:
    """Verify a Firebase token then map it to the PostgreSQL identity."""
    return _firebase_user(FirebaseAuthService.verify_id_token(id_token), db)


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        subject = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]).get("sub")
    except JWTError:
        subject = None
    if subject:
        # This is a valid LIFE SAVER JWT: preserve the previous behavior.
        user = db.get(User, subject)
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="Invalid or inactive authentication token")
        return user
    # Firebase ID tokens are exchanged at /auth/firebase for a LIFE SAVER JWT;
    # they are never accepted as permanent API bearer credentials.
    raise HTTPException(status_code=401, detail="Invalid or inactive authentication token")

def require_role(*roles: UserRole) -> Callable:
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles: raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return dependency

def current_patient(user: User = Depends(require_role(UserRole.patient)), db: Session = Depends(get_db)) -> Patient:
    patient = db.query(Patient).filter(Patient.user_id == user.id).one_or_none()
    if not patient: raise HTTPException(status_code=403, detail="Patient profile is required")
    return patient

def current_doctor(user: User = Depends(require_role(UserRole.doctor)), db: Session = Depends(get_db)) -> Doctor:
    doctor = db.query(Doctor).filter(Doctor.user_id == user.id).one_or_none()
    if not doctor: raise HTTPException(status_code=403, detail="Doctor profile is required")
    return doctor
