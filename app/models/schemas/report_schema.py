# app/models/schemas/report_schema.py
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class ReportBase(BaseModel):
    patient_id: UUID
    file_name: str
    file_size: int


class ReportCreate(ReportBase):
    uploaded_by: Optional[UUID] = None


class ReportUpdate(BaseModel):
    status: Optional[str] = None
    overall_risk: Optional[str] = None
    summary: Optional[str] = None
    is_active: Optional[bool] = None


class ReportResponse(ReportBase):
    id: UUID
    uploaded_by: Optional[UUID] = None
    status: str
    upload_date: datetime
    overall_risk: Optional[str] = None
    summary: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
