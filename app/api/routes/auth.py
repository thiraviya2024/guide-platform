from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.api.dependencies.auth import create_access_token, current_user
from app.core.database import get_db
from app.database.models.domain import Doctor, Patient, User, UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])
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

@router.post("/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email.lower()).one_or_none()
    if not user or not passwords.verify(request.password, user.password_hash): raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer", "role": user.role.value}

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
    return {"access_token": create_access_token(user), "token_type": "bearer", "role": user.role.value}

@router.post("/logout")
async def logout(_: User = Depends(current_user)):
    return {"success": True, "message": "Token logout acknowledged; discard the bearer token client-side."}
