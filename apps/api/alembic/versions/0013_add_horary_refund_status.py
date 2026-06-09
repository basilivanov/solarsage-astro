# AI_HEADER
# module: M-MIGRATION-0013
# wave: W-HORARY-ANSWER-QUALITY-V1-followup-1
# purpose: Persist explicit refund outcome on horary_questions so the UI does
#          not show a misleading "Списание возвращено" for non-refundable
#          credits (e.g. expired weekly-free).

"""add horary question refund_status

Revision ID: 0013_add_horary_refund_status
Revises: 0012_add_horary_answer_quality
Create Date: 2026-06-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0013_add_horary_refund_status"
down_revision = "0012_add_horary_answer_quality"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "horary_questions",
        sa.Column(
            "refund_status",
            sa.String(length=20),
            nullable=False,
            server_default="none",
        ),
    )


def downgrade() -> None:
    op.drop_column("horary_questions", "refund_status")
