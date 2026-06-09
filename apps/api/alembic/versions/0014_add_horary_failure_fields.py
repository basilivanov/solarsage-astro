# AI_HEADER
# module: M-MIGRATION-0014
# wave: W-HORARY-UX-GENERATION-REPAIR
# purpose: Persist horary generation failure metadata on horary_questions.

"""add horary failure fields

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0014_add_horary_failure_fields"
down_revision = "0013_add_horary_refund_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "horary_questions",
        sa.Column("failure_stage", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "horary_questions",
        sa.Column("failure_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "horary_questions",
        sa.Column("failure_message", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "horary_questions",
        sa.Column("public_error_code", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "horary_questions",
        sa.Column("public_error_message", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("horary_questions", "public_error_message")
    op.drop_column("horary_questions", "public_error_code")
    op.drop_column("horary_questions", "failure_message")
    op.drop_column("horary_questions", "failure_code")
    op.drop_column("horary_questions", "failure_stage")
