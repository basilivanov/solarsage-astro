# AI_HEADER
# module: M-MIGRATION-0011
# wave: W-HORARY
# purpose: Add horary tables with credit ledgers

"""add horary tables

Revision ID: 0011_add_horary
Revises: 0010_add_profile_locations
Create Date: 2026-06-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_add_horary"
down_revision = "0010_add_profile_locations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. horary_credits
    op.create_table(
        "horary_credits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("used_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("access_week_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_week_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("amount > 0", name="ck_horary_credits_amount_positive"),
        sa.CheckConstraint("used_amount >= 0", name="ck_horary_credits_used_amount_nonnegative"),
        sa.CheckConstraint("used_amount <= amount", name="ck_horary_credits_used_amount_le_amount"),
        sa.CheckConstraint(
            "source IN ('subscription_weekly_free', 'referral_bonus', 'gift', 'paid', 'adjustment')",
            name="ck_horary_credits_source_values",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source", "access_week_start", "access_week_end", name="uq_horary_credits_weekly_free"),
    )
    op.create_index("ix_horary_credits_user_id", "horary_credits", ["user_id"])

    # 2. horary_questions
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
        sa.Column("question_location_name", sa.String(length=200), nullable=True),
        sa.Column("spent_credit_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spent_credit_id"], ["horary_credits.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_horary_questions_idempotency"),
    )
    op.create_index("ix_horary_questions_user_id", "horary_questions", ["user_id"])

    # 3. horary_answers
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

    # 4. horary_credit_spends
    op.create_table(
        "horary_credit_spends",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("credit_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["credit_id"], ["horary_credits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["horary_questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_horary_credit_spends_idempotency"),
        sa.UniqueConstraint("question_id", name="uq_horary_credit_spends_question"),
    )
    op.create_index("ix_horary_credit_spends_user_id", "horary_credit_spends", ["user_id"])
    op.create_index("ix_horary_credit_spends_credit_id", "horary_credit_spends", ["credit_id"])


def downgrade() -> None:
    op.drop_index("ix_horary_credit_spends_credit_id", table_name="horary_credit_spends")
    op.drop_index("ix_horary_credit_spends_user_id", table_name="horary_credit_spends")
    op.drop_table("horary_credit_spends")

    op.drop_table("horary_answers")

    op.drop_index("ix_horary_questions_user_id", table_name="horary_questions")
    op.drop_table("horary_questions")

    op.drop_index("ix_horary_credits_user_id", table_name="horary_credits")
    op.drop_table("horary_credits")
