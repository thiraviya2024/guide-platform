"""Authentication coverage for local JWT, Firebase mapping, and demo identities."""
from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import auth as auth_dependencies
from app.core.config import settings
from app.core.database import Base, get_db
from app.database.models.domain import Doctor, Patient, User, UserRole
from app.main import app
from app.services.firebase_auth import (
    FirebaseAuthError,
    FirebaseAuthService,
    FirebaseConfigurationError,
    FirebaseIdentity,
)


@pytest.fixture()
def client_and_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def register(client, email: str, role: str = "patient", **extra):
    payload = {"email": email, "password": "a-long-test-password", "role": role, "name": "Test User", **extra}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def identity(uid: str, email: str, name: str = "Firebase User") -> FirebaseIdentity:
    return FirebaseIdentity(uid=uid, email=email, name=name, picture=None, email_verified=True)


def firebase_identity(monkeypatch, value: FirebaseIdentity):
    monkeypatch.setattr(FirebaseAuthService, "verify_id_token", classmethod(lambda cls, token: value))


def test_local_registration_login_invalid_password_and_protected_jwt(client_and_session):
    client, _ = client_and_session
    registered = register(client, "local@example.com")
    login = client.post("/api/v1/auth/login", json={"email": "LOCAL@example.com", "password": "a-long-test-password"})
    assert login.status_code == 200
    assert login.json()["role"] == "patient"
    assert client.post("/api/v1/auth/login", json={"email": "local@example.com", "password": "wrong-password"}).status_code == 401
    headers = {"Authorization": f"Bearer {registered['access_token']}"}
    assert client.get("/api/v1/patients/me/health", headers=headers).status_code == 200


def test_firebase_provisions_patient_and_local_jwt(client_and_session, monkeypatch):
    client, factory = client_and_session
    firebase_identity(monkeypatch, identity("firebase-new", "New.Firebase@Example.com", "New Firebase"))
    response = client.post("/api/v1/auth/firebase", json={"id_token": "verified-token"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "new.firebase@example.com"
    assert body["role"] == "patient"
    with factory() as db:
        user = db.query(User).filter_by(firebase_uid="firebase-new").one()
        assert user.role == UserRole.patient
        assert db.query(Patient).filter_by(user_id=user.id).one_or_none() is not None
    # The returned application JWT works without Firebase verification.
    monkeypatch.setattr(auth_dependencies, "resolve_firebase_user", lambda *_: pytest.fail("local JWT was treated as Firebase"))
    assert client.get("/api/v1/patients/me/health", headers={"Authorization": f"Bearer {body['access_token']}"}).status_code == 200


def test_firebase_links_existing_email_without_changing_role(client_and_session, monkeypatch):
    client, factory = client_and_session
    existing = register(client, "doctor@example.com", role="doctor", specialty="Cardiology")
    firebase_identity(monkeypatch, identity("firebase-doctor", "DOCTOR@example.com"))
    response = client.post("/api/v1/auth/firebase", json={"id_token": "verified-token"})
    assert response.status_code == 200
    assert response.json()["user_id"] == existing["user_id"]
    assert response.json()["role"] == "doctor"
    with factory() as db:
        user = db.get(User, existing["user_id"])
        assert user.firebase_uid == "firebase-doctor"
        assert db.query(Doctor).filter_by(user_id=user.id).one_or_none() is not None


def test_firebase_uid_conflict_inactive_and_invalid_token_are_rejected(client_and_session, monkeypatch):
    client, factory = client_and_session
    register(client, "linked@example.com")
    firebase_identity(monkeypatch, identity("first-uid", "linked@example.com"))
    assert client.post("/api/v1/auth/firebase", json={"id_token": "first"}).status_code == 200
    # UID lookup takes precedence over email lookup, so an email change in
    # Firebase does not produce a second local account.
    firebase_identity(monkeypatch, identity("first-uid", "changed@example.com"))
    assert client.post("/api/v1/auth/firebase", json={"id_token": "same-uid"}).status_code == 200
    firebase_identity(monkeypatch, identity("second-uid", "linked@example.com"))
    assert client.post("/api/v1/auth/firebase", json={"id_token": "second"}).status_code == 401
    with factory() as db:
        user = db.query(User).filter_by(email="linked@example.com").one()
        user.is_active = False
        db.commit()
    firebase_identity(monkeypatch, identity("first-uid", "linked@example.com"))
    assert client.post("/api/v1/auth/firebase", json={"id_token": "inactive"}).status_code == 401
    monkeypatch.setattr(FirebaseAuthService, "verify_id_token", classmethod(lambda cls, token: (_ for _ in ()).throw(FirebaseAuthError("Invalid Firebase ID token"))))
    assert client.post("/api/v1/auth/firebase", json={"id_token": "invalid"}).status_code == 401


def test_firebase_missing_email_is_rejected(client_and_session, monkeypatch):
    client, _ = client_and_session
    monkeypatch.setattr(FirebaseAuthService, "verify_id_token", classmethod(lambda cls, token: (_ for _ in ()).throw(FirebaseAuthError("Firebase account must have an email address"))))
    assert client.post("/api/v1/auth/firebase", json={"id_token": "missing-email"}).status_code == 401


def test_firebase_configuration_failures_are_server_errors(client_and_session, monkeypatch):
    client, _ = client_and_session
    monkeypatch.setattr(
        FirebaseAuthService,
        "verify_id_token",
        classmethod(lambda cls, token: (_ for _ in ()).throw(FirebaseConfigurationError("Firebase Admin configuration is missing"))),
    )
    response = client.post("/api/v1/auth/firebase", json={"id_token": "valid-shaped-token"})
    assert response.status_code == 500
    assert response.json()["detail"] == "Firebase Admin configuration is missing"


def test_render_firebase_credentials_are_normalized_and_project_bound(monkeypatch):
    monkeypatch.setattr(settings, "FIREBASE_PROJECT_ID", "life-saver-93cc0")
    monkeypatch.setattr(settings, "FIREBASE_CLIENT_EMAIL", "firebase-adminsdk@example.iam.gserviceaccount.com")
    monkeypatch.setattr(settings, "FIREBASE_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\\nvalue\\n-----END PRIVATE KEY-----\\n")
    data = FirebaseAuthService._credential_data()
    assert data["project_id"] == "life-saver-93cc0"
    assert data["private_key"] == "-----BEGIN PRIVATE KEY-----\nvalue\n-----END PRIVATE KEY-----\n"
    monkeypatch.setattr(settings, "FIREBASE_PROJECT_ID", "another-project")
    with pytest.raises(FirebaseConfigurationError):
        FirebaseAuthService._credential_data()


def test_firebase_admin_is_initialized_once_per_process(monkeypatch):
    calls = []
    fake_admin = SimpleNamespace()

    def get_app():
        if not hasattr(fake_admin, "app"):
            raise ValueError("The default Firebase app does not exist")
        return fake_admin.app

    def initialize_app(certificate, options):
        calls.append((certificate, options))
        fake_admin.app = SimpleNamespace(project_id=options["projectId"])
        return fake_admin.app

    fake_admin.get_app = get_app
    fake_admin.initialize_app = initialize_app
    fake_admin.credentials = SimpleNamespace(Certificate=lambda data: data)
    monkeypatch.setitem(sys.modules, "firebase_admin", fake_admin)
    monkeypatch.setattr(settings, "FIREBASE_PROJECT_ID", "life-saver-93cc0")
    monkeypatch.setattr(settings, "FIREBASE_CLIENT_EMAIL", "firebase-adminsdk@example.iam.gserviceaccount.com")
    monkeypatch.setattr(settings, "FIREBASE_PRIVATE_KEY", "private-key")
    monkeypatch.setattr(FirebaseAuthService, "_app", None)

    assert FirebaseAuthService._get_app() is FirebaseAuthService._get_app()
    assert len(calls) == 1
    assert calls[0][1] == {"projectId": "life-saver-93cc0"}


def test_demo_login_is_development_only_and_roles_are_authoritative(client_and_session, monkeypatch):
    client, factory = client_and_session
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "ENABLE_DEMO_AUTH", True)
    patient = client.post("/api/v1/auth/demo-login", json={"role": "patient"})
    doctor = client.post("/api/v1/auth/demo-login", json={"role": "doctor"})
    admin = client.post("/api/v1/auth/demo-login", json={"role": "admin"})
    assert [response.status_code for response in (patient, doctor, admin)] == [200, 200, 200]
    assert [response.json()["role"] for response in (patient, doctor, admin)] == ["patient", "doctor", "admin"]
    assert client.get("/api/v1/doctors/me/appointments", headers={"Authorization": f"Bearer {patient.json()['access_token']}"}).status_code == 403
    with factory() as db:
        assert db.query(Patient).filter_by(user_id=patient.json()["user_id"]).one_or_none() is not None
        assert db.query(Doctor).filter_by(user_id=doctor.json()["user_id"]).one_or_none() is not None
        assert db.query(Patient).filter_by(user_id=admin.json()["user_id"]).one_or_none() is None
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert client.post("/api/v1/auth/demo-login", json={"role": "patient"}).status_code == 404
