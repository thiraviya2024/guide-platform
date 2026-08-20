# app/models/schemas/auth_schema.py
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    phone: Optional[str] = None


class UserRegister(UserBase):
    password: str = Field(..., min_length=8)
    role: str = "patient"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(UserBase):
    id: UUID
    role: str
    is_active: bool
    is_email_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
