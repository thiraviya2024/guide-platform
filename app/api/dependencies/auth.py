from datetime import datetime, timedelta, timezone
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.database.models.domain import Doctor, Patient, User, UserRole

bearer = HTTPBearer(auto_error=False)

def create_access_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": user.id, "role": user.role.value, "exp": exp}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try: subject = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]).get("sub")
    except JWTError: subject = None
    user = db.get(User, subject) if subject else None
    if not user or not user.is_active: raise HTTPException(status_code=401, detail="Invalid or inactive authentication token")
    return user

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
