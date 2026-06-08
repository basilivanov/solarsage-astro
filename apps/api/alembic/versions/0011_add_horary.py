# AI_HEADER
# module: M-MIGRATION-0011
# wave: W-HORARY
# purpose: Add horary tables

"""add horary tables

Revision ID: 0011_add_horary
Revises: 0010_add_profile_locations
Create Date: 2026-06-08
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision = "0011_add_horary"
down_revision = "0010_add_profile_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. horary_questions
    op.create_table(
        "horary_questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.String(length=500), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("client_timezone", sa.String(length=100), nullable=False),
        sa.Column("client_local_time", sa.String(length=100), nullable=True),
        sa.Column("question_lat", sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column("question_lon", sa.Numeric(precision=9, scale=5), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_horary_questions_user_id", "horary_questions", ["user_id"])

    # 2. horary_answers
    op.create_table(
        "horary_answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("verdict", sa.String(length=10), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("blocks_json", sa.Text(), nullable=False),
        sa.Column("planets_json", sa.Text(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["question_id"], ["horary_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id"),
    )

    # 3. horary_quotas
    op.create_table(
        "horary_quotas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("questions_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("questions_limit", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("reset_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_horary_quotas_user_id", "horary_quotas", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_horary_quotas_user_id", table_name="horary_quotas")
    op.drop_table("horary_quotas")
    op.drop_table("horary_answers")
    op.drop_index("ix_horary_questions_user_id", table_name="horary_questions")
    op.drop_table("horary_questions")
