"""Integration coverage for JWT-owned care and persisted report workflows."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.api.routes import analyze


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def register(client, email, role="patient", **extra):
    payload = {"email": email, "password": "a-long-test-password", "role": role, "name": email.split("@")[0], **extra}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_authenticated_upload_analysis_history_download_and_doctor_authorization(client):
    patient_headers = register(client, "patient@example.com")
    other_headers = register(client, "other@example.com")
    doctor_headers = register(client, "doctor@example.com", "doctor", specialty="Cardiology")
    doctors = client.get("/api/v1/doctors").json()["items"]
    doctor_id = doctors[0]["id"]

    uploaded = client.post(
        "/api/v1/upload/report?module=lipid", headers=patient_headers,
        files={"file": ("lipids.txt", b"Total Cholesterol: 220\nLDL: 145\nHDL: 38\nTriglycerides: 180", "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    report_id = uploaded.json()["report_id"]
    assert uploaded.json()["analysis_status"] == "UPLOADED"
    analyzed = client.post(
        f"/api/v1/analyze/file?module=lipid&report_id={report_id}", headers=patient_headers,
    )
    assert analyzed.status_code == 200 and analyzed.json()["report_id"] == report_id

    history = client.get("/api/v1/patients/me/reports", headers=patient_headers)
    assert [item["id"] for item in history.json()["items"]] == [report_id]
    detail = client.get(f"/api/v1/patients/me/reports/{report_id}", headers=patient_headers)
    assert detail.status_code == 200
    assert detail.json()["module"] == "lipid"
    assert detail.json()["analysis_status"] == "COMPLETED"
    assert detail.json()["analysis_result"] and detail.json()["evidence"]
    assert client.get(f"/api/v1/patients/me/reports/{report_id}", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/patients/me/reports/{report_id}/download", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/patients/me/reports/{report_id}/download", headers=patient_headers).status_code == 200

    appointment = client.post("/api/v1/appointments", headers=patient_headers, json={
        "doctor_id": doctor_id, "reason": "Review report", "appointment_at": datetime.now(timezone.utc).isoformat(), "appointment_type": "online",
    })
    assert appointment.status_code == 201
    appointment_id = appointment.json()["id"]
    patient_id = appointment.json()["patient_id"]
    assert client.get("/api/v1/doctors/me/appointments", headers=doctor_headers).status_code == 200
    assert client.patch(f"/api/v1/appointments/{appointment_id}", headers=doctor_headers, json={"status": "APPROVED"}).status_code == 200
    health_history = client.get("/api/v1/patients/me/health", headers=patient_headers)  # verifies patient identity endpoint access
    assert health_history.status_code == 200
    assert client.get(f"/api/v1/doctors/me/patients/{patient_id}/reports/{report_id}", headers=doctor_headers).status_code == 200
    # The doctor is now authorized through the approved appointment, but not
    # by arbitrary report id alone.
    assert client.get(f"/api/v1/doctors/me/patients/{doctor_id}/reports/{report_id}", headers=doctor_headers).status_code == 403


def test_persisted_report_stores_provider_explanation(client, monkeypatch):
    headers = register(client, "ai-report@example.com")
    monkeypatch.setattr(
        analyze.ai_orchestrator,
        "generate_response",
        lambda evidence, message, require_provider: {"success": True, "response": "Provider-grounded explanation.", "provider": "test"},
    )
    upload = client.post(
        "/api/v1/upload/report", headers=headers,
        files={"file": ("lipids.txt", b"LDL: 170\nHDL: 35", "text/plain")},
    )
    report_id = upload.json()["report_id"]
    analyzed = client.post(f"/api/v1/analyze/file?report_id={report_id}", headers=headers)
    assert analyzed.status_code == 200
    detail = client.get(f"/api/v1/patients/me/reports/{report_id}", headers=headers).json()
    assert detail["analysis_status"] == "COMPLETED"
    assert detail["ai_explanation"] == "Provider-grounded explanation."


def test_failed_persisted_analysis_is_terminal_and_does_not_create_a_second_report(client):
    headers = register(client, "failed-report@example.com")
    upload = client.post(
        "/api/v1/upload/report", headers=headers,
        files={"file": ("unrecognized.txt", b"not a supported laboratory result", "text/plain")},
    )
    report_id = upload.json()["report_id"]
    analysis = client.post(f"/api/v1/analyze/file?report_id={report_id}", headers=headers)
    assert analysis.status_code == 200 and analysis.json()["success"] is False
    detail = client.get(f"/api/v1/patients/me/reports/{report_id}", headers=headers).json()
    assert detail["analysis_status"] == "FAILED"
    assert detail["analysis_result"]["safe_error_state"] is True
    history = client.get("/api/v1/patients/me/reports", headers=headers).json()["items"]
    assert [report["id"] for report in history] == [report_id]


def test_health_bmi_consultation_transitions_messages_and_hospital_unavailable(client):
    patient_headers = register(client, "patient2@example.com")
    outsider_headers = register(client, "outsider@example.com")
    doctor_headers = register(client, "doctor2@example.com", "doctor", specialty="General")
    doctor_id = client.get("/api/v1/doctors").json()["items"][0]["id"]

    health = client.post("/api/v1/patients/me/health", headers=patient_headers, json={"systolic_bp": 120, "diastolic_bp": 80, "spo2": 98, "blood_glucose": 90, "height_cm": 180, "weight_kg": 81})
    assert health.status_code == 201 and health.json()["bmi"] == 25.0
    assert client.post("/api/v1/patients/me/health", headers=patient_headers, json={"spo2": 101}).status_code == 422

    consultation = client.post("/api/v1/consultations", headers=patient_headers, json={"doctor_id": doctor_id})
    assert consultation.status_code == 201 and consultation.json()["status"] == "REQUESTED"
    consultation_id = consultation.json()["id"]
    assert client.get(f"/api/v1/consultations/{consultation_id}", headers=outsider_headers).status_code == 403
    assert client.patch(f"/api/v1/consultations/{consultation_id}", headers=patient_headers, json={"status": "APPROVED"}).status_code == 403
    assert client.patch(f"/api/v1/consultations/{consultation_id}", headers=doctor_headers, json={"status": "APPROVED"}).status_code == 200
    assert client.patch(f"/api/v1/consultations/{consultation_id}", headers=doctor_headers, json={"status": "ACTIVE"}).status_code == 200
    assert client.post(f"/api/v1/consultations/{consultation_id}/messages", headers=patient_headers, json={"body": "Hello doctor"}).status_code == 201
    assert client.post(f"/api/v1/consultations/{consultation_id}/messages", headers=outsider_headers, json={"body": "No access"}).status_code == 403
    assert client.patch(f"/api/v1/consultations/{consultation_id}", headers=doctor_headers, json={"status": "CLOSED"}).status_code == 200
    assert client.get("/api/v1/hospitals/search?latitude=12.9&longitude=77.6&specialty=cardiology").status_code == 503
