# AI_HEADER
# module: M-MIGRATION-0015
# wave: W-NATAL-PREVIEW-MVP
# purpose: Add gender to user_profiles.

"""add profile gender

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0015"
down_revision = "0014_add_horary_failure_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("gender", sa.String(length=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "gender")
