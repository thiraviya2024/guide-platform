"""align PostgreSQL consultation status values with the application workflow

Revision ID: 20260828_03
Revises: 20260828_02
Create Date: 2026-08-28
"""
from alembic import op

revision = "20260828_03"
down_revision = "20260828_02"
branch_labels = None
depends_on = None


def upgrade():
    # Existing deployments created this type before APPROVED was introduced.
    # PostgreSQL enum changes are additive, so this is safe for populated DBs.
    op.execute("ALTER TYPE consultation_status ADD VALUE IF NOT EXISTS 'APPROVED'")


def downgrade():
    # PostgreSQL cannot remove a value from an enum without rebuilding columns.
    # Keep downgrade non-destructive for production care records.
    pass
