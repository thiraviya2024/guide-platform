"""add identity and persistent care domain

Revision ID: 20260828_01
Revises:
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "20260828_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    role = sa.Enum("patient", "doctor", "admin", name="user_role")
    appointment_status = sa.Enum("PENDING", "APPROVED", "REJECTED", "CANCELLED", "COMPLETED", name="appointment_status")
    consultation_status = sa.Enum("REQUESTED", "ACTIVE", "CLOSED", "REJECTED", name="consultation_status")
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("email", sa.String(320), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", role, nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table("patients", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("date_of_birth", sa.Date()), sa.Column("gender", sa.String(50)), sa.Column("height_cm", sa.Float()), sa.Column("weight_kg", sa.Float()), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))
    op.create_table("doctors", sa.Column("id", sa.String(36), primary_key=True), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("specialty", sa.String(120), nullable=False), sa.Column("qualification", sa.String(255)), sa.Column("registration_identifier", sa.String(255), unique=True), sa.Column("availability_status", sa.String(50), nullable=False, server_default="AVAILABLE"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))
    op.create_index("ix_doctors_specialty", "doctors", ["specialty"])
    op.create_table("reports", sa.Column("id", sa.String(36), primary_key=True), sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False), sa.Column("original_filename", sa.String(512), nullable=False), sa.Column("stored_filename", sa.String(512), nullable=False, unique=True), sa.Column("storage_path", sa.String(1024), nullable=False), sa.Column("module", sa.String(50), nullable=False), sa.Column("analysis_status", sa.String(50), nullable=False), sa.Column("ai_explanation", sa.Text()), sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))
    op.create_index("ix_reports_patient_id", "reports", ["patient_id"])
    op.create_table("report_findings", sa.Column("id", sa.String(36), primary_key=True), sa.Column("report_id", sa.String(36), sa.ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("evidence", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))
    op.create_table("health_readings", sa.Column("id", sa.String(36), primary_key=True), sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False), sa.Column("systolic_bp", sa.Float()), sa.Column("diastolic_bp", sa.Float()), sa.Column("spo2", sa.Float()), sa.Column("blood_glucose", sa.Float()), sa.Column("heart_rate", sa.Float()), sa.Column("temperature_c", sa.Float()), sa.Column("height_cm", sa.Float()), sa.Column("weight_kg", sa.Float()), sa.Column("bmi", sa.Float()), sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))
    op.create_index("ix_health_readings_patient_id", "health_readings", ["patient_id"])
    op.create_table("appointments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False), sa.Column("doctor_id", sa.String(36), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False), sa.Column("appointment_type", sa.String(20), nullable=False), sa.Column("status", appointment_status, nullable=False, server_default="PENDING"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"]); op.create_index("ix_appointments_doctor_id", "appointments", ["doctor_id"])
    op.create_table("consultations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("patient_id", sa.String(36), sa.ForeignKey("patients.id", ondelete="CASCADE"), nullable=False), sa.Column("doctor_id", sa.String(36), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False), sa.Column("appointment_id", sa.String(36), sa.ForeignKey("appointments.id", ondelete="SET NULL")), sa.Column("status", consultation_status, nullable=False, server_default="REQUESTED"), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")), sa.Column("closed_at", sa.DateTime(timezone=True)))
    op.create_table("consultation_messages", sa.Column("id", sa.String(36), primary_key=True), sa.Column("consultation_id", sa.String(36), sa.ForeignKey("consultations.id", ondelete="CASCADE"), nullable=False), sa.Column("sender_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")))

def downgrade():
    for table in ("consultation_messages", "consultations", "appointments", "health_readings", "report_findings", "reports", "doctors", "patients", "users"): op.drop_table(table)
    sa.Enum(name="consultation_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="appointment_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
