"""Authenticated patient, doctor, appointment, consultation, and health APIs."""
from datetime import datetime, timezone
import os
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.dependencies.auth import current_doctor, current_patient, current_user
from app.core.config import settings
from app.core.database import get_db
from app.database.models.domain import Appointment, AppointmentStatus, Consultation, ConsultationMessage, ConsultationStatus, Doctor, HealthReading, Patient, Report, ReportFinding, User

router = APIRouter(tags=["Care"])

def bmi(height_cm: float, weight_kg: float) -> float:
    if not 50 <= height_cm <= 300 or not 2 <= weight_kg <= 500: raise HTTPException(422, "Height or weight outside accepted manual-entry range")
    return round(weight_kg / ((height_cm / 100) ** 2), 1)
def bmi_category(value: float) -> str:
    return "Underweight" if value < 18.5 else "Healthy weight" if value < 25 else "Overweight" if value < 30 else "Obesity"
def serial_health(x: HealthReading): return {k: getattr(x,k) for k in ("id","systolic_bp","diastolic_bp","spo2","blood_glucose","heart_rate","temperature_c","height_cm","weight_kg","bmi","recorded_at")}
def serial_appt(x: Appointment): return {"id":x.id,"patient_id":x.patient_id,"doctor_id":x.doctor_id,"reason":x.reason,"appointment_at":x.appointment_at,"type":x.appointment_type,"status":x.status.value,"created_at":x.created_at,"updated_at":x.updated_at}
def authorized_doctor_patient(db: Session, doctor: Doctor, patient_id: str):
    appointment = db.query(Appointment).filter(Appointment.doctor_id==doctor.id, Appointment.patient_id==patient_id, Appointment.status.in_([AppointmentStatus.approved, AppointmentStatus.completed])).first()
    consultation = db.query(Consultation).filter(Consultation.doctor_id==doctor.id, Consultation.patient_id==patient_id, Consultation.status.in_([ConsultationStatus.active, ConsultationStatus.closed])).first()
    if not appointment and not consultation: raise HTTPException(403,"No authorized care relationship")

class HealthInput(BaseModel):
    systolic_bp: float|None=None; diastolic_bp: float|None=None; spo2: float|None=None; blood_glucose: float|None=None; heart_rate: float|None=None; temperature_c: float|None=None; height_cm: float|None=None; weight_kg: float|None=None; recorded_at: datetime|None=None
class BMIInput(BaseModel): height_cm: float; weight_kg: float
class AppointmentInput(BaseModel): doctor_id: str; reason: str=Field(min_length=1,max_length=4000); appointment_at: datetime; appointment_type: Literal['online','in-person']
class AppointmentUpdate(BaseModel): status: AppointmentStatus
class ConsultationInput(BaseModel): doctor_id: str; appointment_id: str|None=None
class ConsultationUpdate(BaseModel): status: ConsultationStatus
class MessageInput(BaseModel): body: str=Field(min_length=1,max_length=10000)

@router.get('/doctors')
def doctors(specialty: str|None=None, db: Session=Depends(get_db)):
    q=db.query(Doctor)
    if specialty: q=q.filter(Doctor.specialty.ilike(f'%{specialty}%'))
    rows=q.order_by(Doctor.name).all()
    return {"items":[{"id":d.id,"name":d.name,"specialty":d.specialty,"qualification":d.qualification,"availability_status":d.availability_status} for d in rows],"total":len(rows)}

@router.post('/patients/me/health',status_code=201)
def add_health(data:HealthInput, patient:Patient=Depends(current_patient),db:Session=Depends(get_db)):
    value=bmi(data.height_cm,data.weight_kg) if data.height_cm is not None and data.weight_kg is not None else None
    row=HealthReading(patient_id=patient.id,bmi=value,recorded_at=data.recorded_at or datetime.now(timezone.utc),**data.model_dump(exclude={'recorded_at','height_cm','weight_kg'}),height_cm=data.height_cm,weight_kg=data.weight_kg)
    db.add(row); db.commit(); db.refresh(row); return serial_health(row)
@router.get('/patients/me/health')
def health(latest:bool=False,patient:Patient=Depends(current_patient),db:Session=Depends(get_db)):
    q=db.query(HealthReading).filter_by(patient_id=patient.id).order_by(HealthReading.recorded_at.desc())
    rows=q.limit(1).all() if latest else q.all(); return {"items":[serial_health(x) for x in rows]}
@router.post('/patients/me/bmi')
def calculate_bmi(data:BMIInput, _:Patient=Depends(current_patient)): 
    value=bmi(data.height_cm,data.weight_kg); return {"bmi":value,"category":bmi_category(value)}
@router.post('/patients/me/diet-guidance')
def diet_guidance(patient:Patient=Depends(current_patient),db:Session=Depends(get_db)):
    latest=db.query(HealthReading).filter_by(patient_id=patient.id).order_by(HealthReading.recorded_at.desc()).first()
    report=db.query(Report).filter_by(patient_id=patient.id).order_by(Report.uploaded_at.desc()).first()
    evidence=db.query(ReportFinding).filter_by(report_id=report.id).first() if report else None
    return {"available":False,"detail":"Diet AI is unavailable until a configured provider returns evidence-grounded guidance.","health_context":serial_health(latest) if latest else None,"report_context_available":bool(evidence)}

@router.get('/patients/me/reports')
def patient_reports(patient:Patient=Depends(current_patient),db:Session=Depends(get_db)):
    rows=db.query(Report).filter_by(patient_id=patient.id).order_by(Report.uploaded_at.desc()).all()
    return {"items":[{"id":r.id,"original_filename":r.original_filename,"module":r.module,"analysis_status":r.analysis_status,"uploaded_at":r.uploaded_at,"download_url":f"/api/v1/patients/me/reports/{r.id}/download"} for r in rows]}
@router.get('/patients/me/reports/{report_id}')
def patient_report(report_id:str,patient:Patient=Depends(current_patient),db:Session=Depends(get_db)):
    r=db.query(Report).filter_by(id=report_id,patient_id=patient.id).one_or_none()
    if not r:raise HTTPException(404,'Report not found')
    finding=db.query(ReportFinding).filter_by(report_id=r.id).one_or_none()
    return {"id":r.id,"original_filename":r.original_filename,"module":r.module,"analysis_status":r.analysis_status,"uploaded_at":r.uploaded_at,"analysis_result":r.analysis_result,"ai_explanation":r.ai_explanation,"evidence":finding.evidence if finding else None,"download_url":f"/api/v1/patients/me/reports/{r.id}/download"}
@router.get('/patients/me/reports/{report_id}/download')
def patient_report_download(report_id:str,patient:Patient=Depends(current_patient),db:Session=Depends(get_db)):
    from fastapi.responses import FileResponse
    r=db.query(Report).filter_by(id=report_id,patient_id=patient.id).one_or_none()
    if not r or not os.path.exists(r.storage_path): raise HTTPException(404,'Report not found')
    return FileResponse(r.storage_path,filename=r.original_filename)

@router.post('/appointments',status_code=201)
def create_appointment(data:AppointmentInput,patient:Patient=Depends(current_patient),db:Session=Depends(get_db)):
    if not db.get(Doctor,data.doctor_id): raise HTTPException(404,'Doctor not found')
    row=Appointment(patient_id=patient.id,doctor_id=data.doctor_id,reason=data.reason,appointment_at=data.appointment_at,appointment_type=data.appointment_type)
    db.add(row);db.commit();db.refresh(row);return serial_appt(row)
@router.get('/patients/me/appointments')
def patient_appts(patient:Patient=Depends(current_patient),db:Session=Depends(get_db)): return {"items":[serial_appt(x) for x in db.query(Appointment).filter_by(patient_id=patient.id).order_by(Appointment.appointment_at.desc())]}
@router.get('/doctors/me/appointments')
def doctor_appts(doctor:Doctor=Depends(current_doctor),db:Session=Depends(get_db)): return {"items":[serial_appt(x) for x in db.query(Appointment).filter_by(doctor_id=doctor.id).order_by(Appointment.appointment_at.desc())]}
@router.patch('/appointments/{appointment_id}')
def update_appointment(appointment_id:str,data:AppointmentUpdate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(Appointment,appointment_id)
    if not row: raise HTTPException(404,'Appointment not found')
    patient=db.get(Patient,row.patient_id); doctor=db.get(Doctor,row.doctor_id)
    if user.id==patient.user_id:
        if data.status != AppointmentStatus.cancelled or row.status not in [AppointmentStatus.pending,AppointmentStatus.approved]: raise HTTPException(403,'Patient may only cancel pending or approved appointments')
    elif user.id==doctor.user_id:
        allowed={AppointmentStatus.pending:{AppointmentStatus.approved,AppointmentStatus.rejected},AppointmentStatus.approved:{AppointmentStatus.completed}}
        if data.status not in allowed.get(row.status,set()): raise HTTPException(409,'Invalid doctor appointment transition')
    else: raise HTTPException(403,'Appointment does not belong to authenticated user')
    row.status=data.status;db.commit();db.refresh(row);return serial_appt(row)

@router.get('/doctors/me/patients/{patient_id}')
def doctor_patient(patient_id:str,doctor:Doctor=Depends(current_doctor),db:Session=Depends(get_db)):
    authorized_doctor_patient(db,doctor,patient_id); p=db.get(Patient,patient_id)
    if not p: raise HTTPException(404,'Patient not found')
    return {"id":p.id,"name":p.name,"date_of_birth":p.date_of_birth,"gender":p.gender}
@router.get('/doctors/me/patients/{patient_id}/reports')
def doctor_reports(patient_id:str,doctor:Doctor=Depends(current_doctor),db:Session=Depends(get_db)):
    authorized_doctor_patient(db,doctor,patient_id);return {"items":[{"id":x.id,"original_filename":x.original_filename,"module":x.module,"uploaded_at":x.uploaded_at,"analysis_status":x.analysis_status} for x in db.query(Report).filter_by(patient_id=patient_id)]}
@router.get('/doctors/me/patients/{patient_id}/reports/{report_id}')
def doctor_report(patient_id:str,report_id:str,doctor:Doctor=Depends(current_doctor),db:Session=Depends(get_db)):
    authorized_doctor_patient(db,doctor,patient_id)
    r=db.query(Report).filter_by(id=report_id,patient_id=patient_id).one_or_none()
    if not r: raise HTTPException(404,'Report not found')
    finding=db.query(ReportFinding).filter_by(report_id=r.id).one_or_none()
    return {"id":r.id,"original_filename":r.original_filename,"module":r.module,"uploaded_at":r.uploaded_at,"analysis_status":r.analysis_status,"evidence":finding.evidence if finding else None}
@router.get('/doctors/me/patients/{patient_id}/health')
def doctor_health(patient_id:str,doctor:Doctor=Depends(current_doctor),db:Session=Depends(get_db)):
    authorized_doctor_patient(db,doctor,patient_id);return {"items":[serial_health(x) for x in db.query(HealthReading).filter_by(patient_id=patient_id).order_by(HealthReading.recorded_at.desc())]}

@router.post('/consultations',status_code=201)
def create_consultation(data:ConsultationInput,patient:Patient=Depends(current_patient),db:Session=Depends(get_db)):
    doctor=db.get(Doctor,data.doctor_id)
    if not doctor:raise HTTPException(404,'Doctor not found')
    if data.appointment_id:
        a=db.get(Appointment,data.appointment_id)
        if not a or a.patient_id!=patient.id or a.doctor_id!=doctor.id or a.status!=AppointmentStatus.approved:raise HTTPException(403,'Approved appointment required')
    row=Consultation(patient_id=patient.id,doctor_id=doctor.id,appointment_id=data.appointment_id);db.add(row);db.commit();db.refresh(row);return {"id":row.id,"status":row.status.value}
def consultation_access(db,c,user):
    p=db.get(Patient,c.patient_id);d=db.get(Doctor,c.doctor_id)
    if user.id not in [p.user_id,d.user_id]:raise HTTPException(403,'Consultation access denied')
@router.get('/patients/me/consultations')
def patient_consultations(patient:Patient=Depends(current_patient),db:Session=Depends(get_db)): return {"items":[{"id":x.id,"doctor_id":x.doctor_id,"status":x.status.value} for x in db.query(Consultation).filter_by(patient_id=patient.id)]}
@router.get('/doctors/me/consultations')
def doctor_consultations(doctor:Doctor=Depends(current_doctor),db:Session=Depends(get_db)): return {"items":[{"id":x.id,"patient_id":x.patient_id,"status":x.status.value} for x in db.query(Consultation).filter_by(doctor_id=doctor.id)]}
@router.get('/consultations/{consultation_id}')
def get_consultation(consultation_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=db.get(Consultation,consultation_id)
    if not c:raise HTTPException(404,'Consultation not found')
    consultation_access(db,c,user);return {"id":c.id,"patient_id":c.patient_id,"doctor_id":c.doctor_id,"appointment_id":c.appointment_id,"status":c.status.value,"created_at":c.created_at}
@router.get('/consultations/{consultation_id}/messages')
def consultation_messages(consultation_id:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=db.get(Consultation,consultation_id)
    if not c:raise HTTPException(404,'Consultation not found')
    consultation_access(db,c,user)
    return {"items":[{"id":x.id,"sender_user_id":x.sender_user_id,"body":x.body,"created_at":x.created_at} for x in db.query(ConsultationMessage).filter_by(consultation_id=c.id).order_by(ConsultationMessage.created_at)]}
@router.post('/consultations/{consultation_id}/messages',status_code=201)
def send_message(consultation_id:str,data:MessageInput,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=db.get(Consultation,consultation_id)
    if not c:raise HTTPException(404,'Consultation not found')
    consultation_access(db,c,user)
    if c.status != ConsultationStatus.active:raise HTTPException(409,'Consultation is not active')
    x=ConsultationMessage(consultation_id=c.id,sender_user_id=user.id,body=data.body);db.add(x);db.commit();db.refresh(x);return {"id":x.id,"sender_user_id":x.sender_user_id,"body":x.body,"created_at":x.created_at}
@router.patch('/consultations/{consultation_id}')
def update_consultation(consultation_id:str,data:ConsultationUpdate,user:User=Depends(current_user),db:Session=Depends(get_db)):
    c=db.get(Consultation,consultation_id)
    if not c:raise HTTPException(404,'Consultation not found')
    consultation_access(db,c,user);doctor=db.get(Doctor,c.doctor_id)
    if data.status==ConsultationStatus.active and user.id!=doctor.user_id:raise HTTPException(403,'Only doctor can start consultation')
    if data.status not in [ConsultationStatus.active,ConsultationStatus.closed,ConsultationStatus.rejected]:raise HTTPException(409,'Invalid consultation transition')
    c.status=data.status;c.closed_at=datetime.now(timezone.utc) if data.status in [ConsultationStatus.closed,ConsultationStatus.rejected] else None;db.commit();return {"id":c.id,"status":c.status.value}

@router.get('/hospitals/search')
def hospitals(latitude:float=Query(ge=-90,le=90),longitude:float=Query(ge=-180,le=180),specialty:str|None=None):
    if not getattr(settings,'HOSPITAL_PROVIDER_URL',None): raise HTTPException(503,'Hospital search provider is not configured')
    raise HTTPException(501,'Configured hospital provider adapter has not been implemented')
