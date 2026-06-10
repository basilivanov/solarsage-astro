# AI_HEADER
# module: M-MIGRATION-0016
# wave: W-NATAL-FULL
# purpose: Add natal_chart_cache and natal_reports tables for persistent
#          natal context caching and full report generation.
#          Also adds profile_hash to today_payloads_cache (cache key
#          must depend on natal context).

"""add natal chart cache, natal reports, profile_hash in today cache

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
    # Partial unique index: only active (invalidated_at IS NULL) rows compete
    # for the slot. Invalidated rows are kept for audit but don't block new inserts.
    # Both PostgreSQL and SQLite 3.8+ support partial indexes with WHERE clause.
    op.execute(
        "CREATE UNIQUE INDEX ix_natal_chart_cache_active "
        "ON natal_chart_cache (user_id, profile_hash, engine_version, calculation_version, house_system) "
        "WHERE invalidated_at IS NULL"
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

    # ── today_payloads_cache: add profile_hash column ──────────────────
    # W-NATAL-FULL: profile_hash ties today cache to natal context.
    # If user changes birth data, hash changes → cache miss → fresh data.
    op.add_column(
        "today_payloads_cache",
        sa.Column("profile_hash", sa.String(64), nullable=False, server_default=""),
    )
    # Drop old unique constraint (user_id, target_date) and replace with
    # (user_id, target_date, profile_hash) so cache key depends on natal context.
    op.drop_constraint("uq_user_date", "today_payloads_cache", type_="unique")
    op.create_unique_constraint(
        "uq_user_date_profile",
        "today_payloads_cache",
        ["user_id", "target_date", "profile_hash"],
    )


def downgrade() -> None:
    # ── today_payloads_cache: revert profile_hash ──────────────────────
    op.drop_constraint("uq_user_date_profile", "today_payloads_cache", type_="unique")
    op.create_unique_constraint("uq_user_date", "today_payloads_cache", ["user_id", "target_date"])
    op.drop_column("today_payloads_cache", "profile_hash")

    # ── natal_reports ──────────────────────────────────────────────────
    op.drop_table("natal_reports")

    # ── natal_chart_cache ──────────────────────────────────────────────
    op.execute("DROP INDEX IF EXISTS ix_natal_chart_cache_active")
    op.drop_table("natal_chart_cache")
