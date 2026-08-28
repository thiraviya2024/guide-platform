"""persist rule-engine results and deduplicate patient document retries

Revision ID: 20260828_02
Revises: 20260828_01
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa

revision = "20260828_02"
down_revision = "20260828_01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("reports", sa.Column("analysis_result", sa.JSON(), nullable=True))
    op.add_column("reports", sa.Column("content_sha256", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_reports_patient_content_sha256", "reports", ["patient_id", "content_sha256"])


def downgrade():
    op.drop_constraint("uq_reports_patient_content_sha256", "reports", type_="unique")
    op.drop_column("reports", "content_sha256")
    op.drop_column("reports", "analysis_result")
