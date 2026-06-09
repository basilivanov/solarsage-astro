# AI_HEADER
# module: M-MIGRATION-0012
# wave: W-HORARY-ANSWER-QUALITY-V1
# purpose: Add confidence_label and confidence_explanation to horary_answers
#          so the UI can show a human label instead of a probability.

"""add horary answer quality fields

Revision ID: 0012_add_horary_answer_quality
Revises: 0011_add_horary
Create Date: 2026-06-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0012_add_horary_answer_quality"
down_revision = "0011_add_horary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "horary_answers",
        sa.Column(
            "confidence_label",
            sa.String(length=10),
            nullable=False,
            server_default="medium",
        ),
    )
    op.add_column(
        "horary_answers",
        sa.Column(
            "confidence_explanation",
            sa.String(length=500),
            nullable=False,
            server_default="",
        ),
    )
    # Note: the label-check is enforced at the Pydantic boundary and in the
    # SQLAlchemy model. SQLite cannot ALTER existing tables to add a CHECK
    # constraint, so we do not add one at the DB level here. Postgres
    # deployments should rely on the application-layer validation.


def downgrade() -> None:
    op.drop_column("horary_answers", "confidence_explanation")
    op.drop_column("horary_answers", "confidence_label")
