"""Auth coverage for Firebase identity mapping and development demo accounts."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies.auth import resolve_firebase_user
from app.core.config import settings
from app.core.database import Base, get_db
from app.database.models.domain import Doctor, Patient, User, UserRole
from app.main import app
from app.services.firebase_auth import FirebaseAuthError, FirebaseAuthService, FirebaseIdentity


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client, Session
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def identity(uid="firebase-uid", email="firebase@example.com"):
    return FirebaseIdentity(uid=uid, email=email, name="Firebase Person", picture=None, email_verified=True)


def test_firebase_provisions_patient_and_returns_local_jwt(client, monkeypatch):
    test_client, Session = client
    monkeypatch.setattr(FirebaseAuthService, "verify_id_token", classmethod(lambda cls, token: identity()))
    response = test_client.post("/api/v1/auth/firebase", json={"id_token": "verified-token"})
    assert response.status_code == 200
    assert response.json()["role"] == "patient"
    assert response.json()["access_token"]
    with Session() as db:
        user = db.query(User).filter_by(email="firebase@example.com").one()
        assert user.firebase_uid == "firebase-uid"
        assert db.query(Patient).filter_by(user_id=user.id).one()


def test_firebase_links_email_but_never_changes_role(client, monkeypatch):
    test_client, Session = client
    registered = test_client.post("/api/v1/auth/register", json={
        "email": "doctor@example.com", "password": "a-long-test-password", "role": "doctor",
        "name": "Doctor", "specialty": "Cardiology",
    })
    assert registered.status_code == 201
    monkeypatch.setattr(FirebaseAuthService, "verify_id_token", classmethod(lambda cls, token: identity("doctor-firebase", "doctor@example.com")))
    assert test_client.post("/api/v1/auth/firebase", json={"id_token": "verified-token"}).json()["role"] == "doctor"
    with Session() as db:
        user = db.query(User).filter_by(email="doctor@example.com").one()
        assert user.firebase_uid == "doctor-firebase"
        assert user.role == UserRole.doctor
        assert db.query(Doctor).filter_by(user_id=user.id).one()


def test_firebase_uid_is_unique_and_inactive_user_is_rejected(client, monkeypatch):
    _, Session = client
    with Session() as db:
        first = User(email="first@example.com", firebase_uid="shared-uid", password_hash="x", role=UserRole.patient)
        inactive = User(email="inactive@example.com", firebase_uid="inactive-uid", password_hash="x", role=UserRole.patient, is_active=False)
        db.add_all([first, inactive]); db.commit()
        db.add(User(email="duplicate@example.com", firebase_uid="shared-uid", password_hash="x", role=UserRole.patient))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        with pytest.raises(FirebaseAuthError):
            resolve_firebase_user(identity("inactive-uid", "inactive@example.com"), db)


def test_firebase_invalid_or_missing_email_is_rejected(client, monkeypatch):
    test_client, _ = client
    monkeypatch.setattr(FirebaseAuthService, "verify_id_token", classmethod(lambda cls, token: (_ for _ in ()).throw(FirebaseAuthError("Invalid Firebase ID token"))))
    assert test_client.post("/api/v1/auth/firebase", json={"id_token": "bad"}).status_code == 401


@pytest.mark.parametrize("role", ["patient", "doctor", "admin"])
def test_demo_login_creates_role_appropriate_local_identity(client, monkeypatch, role):
    test_client, Session = client
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ENABLE_DEMO_AUTH", True)
    response = test_client.post("/api/v1/auth/demo-login", json={"role": role})
    assert response.status_code == 200
    assert response.json()["role"] == role
    with Session() as db:
        user = db.query(User).filter_by(email=f"demo.{role}@lifesaver.local").one()
        if role == "patient":
            assert db.query(Patient).filter_by(user_id=user.id).one()
        elif role == "doctor":
            assert db.query(Doctor).filter_by(user_id=user.id).one()


def test_demo_login_is_unavailable_outside_enabled_development(client, monkeypatch):
    test_client, _ = client
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "ENABLE_DEMO_AUTH", True)
    assert test_client.post("/api/v1/auth/demo-login", json={"role": "patient"}).status_code == 404
