"""Coverage for authenticated, report-grounded food recommendation chat."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes.ai import ai_orchestrator, analyze_with_ai
from app.core.database import Base
from app.database.models.domain import Patient, Report, ReportFinding, User, UserRole
from app.services.clinical_evidence import build_clinical_evidence


@pytest.fixture()
def chat_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        db.execute(text("CREATE TABLE food_rules (id INTEGER PRIMARY KEY, disease_name VARCHAR(128), food_suggestions TEXT, is_active BOOLEAN)"))
        db.execute(text("INSERT INTO food_rules VALUES (1, 'Hyperlipidemia', 'Database Mediterranean guidance', 1)"))
        db.execute(text("INSERT INTO food_rules VALUES (2, 'High LDL Cholesterol', 'Database soluble-fiber guidance', 1)"))
        db.commit()
        yield db
    Base.metadata.drop_all(engine)
    engine.dispose()


def patient_with_lipid_report(db, email: str, suffix: str):
    user = User(email=email, password_hash="x", role=UserRole.patient)
    db.add(user)
    db.flush()
    patient = Patient(user_id=user.id, name="Patient")
    db.add(patient)
    db.flush()
    report = Report(
        patient_id=patient.id, original_filename="lipid.txt", stored_filename=f"lipid-{suffix}.txt",
        storage_path=f"uploads/lipid-{suffix}.txt", module="lipid", analysis_status="COMPLETED",
    )
    db.add(report)
    db.flush()
    evidence = build_clinical_evidence({
        "category": "lipid",
        "results": {"ldl": {"value": 165, "status": "High", "recommendation": "Existing clinical rule."}},
        "disease_risks": [{"disease": "Hyperlipidemia", "confidence": "High"}],
    }, report_id=report.id)
    db.add(ReportFinding(report_id=report.id, evidence=evidence))
    db.commit()
    return patient, report


@pytest.mark.asyncio
async def test_lipid_food_question_includes_database_food_rules(chat_db, monkeypatch):
    patient, _ = patient_with_lipid_report(chat_db, "food@example.com", "a")
    captured = {}
    monkeypatch.setattr(
        ai_orchestrator, "generate_response",
        lambda evidence, message, require_provider: captured.update(evidence=evidence) or {"success": True, "response": "Database-backed guidance", "provider": "test"},
    )

    result = await analyze_with_ai({"message": "What foods should I eat based on my lipid report?"}, patient, chat_db)

    assert result["success"] is True
    assert {rule["rule_name"] for rule in captured["evidence"]["food_rules"]} == {"Hyperlipidemia", "High LDL Cholesterol"}
    assert all(rule["food_suggestions"].startswith("Database") for rule in captured["evidence"]["food_rules"])


@pytest.mark.asyncio
async def test_food_question_without_report_does_not_invent_guidance(chat_db):
    patient = Patient(id="no-report", user_id="no-report-user", name="No Report")
    result = await analyze_with_ai({"message": "Which foods should I avoid?"}, patient, chat_db)
    assert result["success"] is True
    assert "do not have a current report" in result["response"]


@pytest.mark.asyncio
async def test_intake_question_never_fabricates_patient_history(chat_db):
    result = await analyze_with_ai({"message": "What food did I eat?"}, SimpleNamespace(id="any"), chat_db)
    assert "do not have a record of what you ate" in result["response"]


@pytest.mark.asyncio
async def test_patient_cannot_load_another_patients_report_context(chat_db):
    _, report = patient_with_lipid_report(chat_db, "first@example.com", "first")
    other, _ = patient_with_lipid_report(chat_db, "second@example.com", "second")
    with pytest.raises(HTTPException, match="Report context not found") as exc:
        await analyze_with_ai({"report_id": report.id, "message": "What foods should I eat?"}, other, chat_db)
    assert exc.value.status_code == 404
