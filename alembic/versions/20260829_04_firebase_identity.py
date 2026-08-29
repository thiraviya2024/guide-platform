"""add Firebase identity mapping to users

Revision ID: 20260829_04
Revises: 20260828_03
Create Date: 2026-08-29
"""
from alembic import op
import sqlalchemy as sa


revision = "20260829_04"
down_revision = "20260828_03"
branch_labels = None
depends_on = None


def upgrade():
    # Nullable preserves every deployed local-password account unchanged.
    op.add_column("users", sa.Column("firebase_uid", sa.String(length=128), nullable=True))
    op.create_index("ix_users_firebase_uid", "users", ["firebase_uid"], unique=True)


def downgrade():
    op.drop_index("ix_users_firebase_uid", table_name="users")
    op.drop_column("users", "firebase_uid")
