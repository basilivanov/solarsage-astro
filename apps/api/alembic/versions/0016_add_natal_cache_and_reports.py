# AI_HEADER
# module: M-MIGRATION-0016
# wave: W-NATAL-FULL
# purpose: Add natal_chart_cache and natal_reports tables for persistent
#          natal context caching and full report generation.

"""add natal chart cache and natal reports

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── natal_chart_cache ──────────────────────────────────────────────
    op.create_table(
        "natal_chart_cache",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("profile_hash", sa.String(64), nullable=False),
        sa.Column("engine_version", sa.String(32), nullable=False, server_default="1"),
        sa.Column("calculation_version", sa.String(32), nullable=False, server_default="1"),
        sa.Column("house_system", sa.String(32), nullable=False, server_default="placidus"),
        sa.Column("raw_chart_json", sa.Text, nullable=False),
        sa.Column("normalized_context_json", sa.Text, nullable=False),
        sa.Column("summary_json", sa.Text, nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_natal_chart_cache_active",
        "natal_chart_cache",
        ["user_id", "profile_hash", "engine_version", "calculation_version", "house_system"],
        unique=True,
    )

    # ── natal_reports ──────────────────────────────────────────────────
    op.create_table(
        "natal_reports",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "natal_context_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("natal_chart_cache.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "access_state",
            sa.String(32),
            nullable=False,
            server_default="FREE_PREVIEW",
        ),
        sa.Column("prompt_version", sa.String(32), nullable=False, server_default="1"),
        sa.Column(
            "report_schema_version",
            sa.String(32),
            nullable=False,
            server_default="natal/v1",
        ),
        sa.Column("model_provider", sa.String(64), nullable=True),
        sa.Column("model_name", sa.String(128), nullable=True),
        sa.Column("model_params_json", sa.Text, nullable=True),
        sa.Column("sections_json", sa.Text, nullable=True),
        sa.Column("sections_status_json", sa.Text, nullable=True),
        sa.Column("input_context_hash", sa.String(64), nullable=True),
        sa.Column("output_hash", sa.String(64), nullable=True),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column("error_message_sanitized", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "user_id",
            "natal_context_id",
            "prompt_version",
            "report_schema_version",
            name="uq_natal_reports_context_prompt",
        ),
    )


def downgrade() -> None:
    op.drop_table("natal_reports")
    op.drop_index("ix_natal_chart_cache_active", table_name="natal_chart_cache")
    op.drop_table("natal_chart_cache")
