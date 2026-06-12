# AI_HEADER
# module: M-MIGRATION-0017
# wave: W-FEATURE-INTAKE
# purpose: Add features and feature_planning_runs tables for business feature
#          intake and planning pipeline observability.

"""add features and feature_planning_runs tables

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-12
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── features ────────────────────────────────────────────────────────
    op.create_table(
        "features",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_repo_root", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, index=True, server_default="NOT_STARTED"),
        sa.Column("mode", sa.String(32), nullable=False, server_default="draft_plan"),
        sa.Column("origin", sa.String(32), nullable=False, server_default="business"),
        sa.Column("self_improvement", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("spec_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_features_status", "features", ["status"])
    op.create_index("ix_features_created_at", "features", ["created_at"])

    # ── feature_planning_runs ───────────────────────────────────────────
    op.create_table(
        "feature_planning_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("feature_id", sa.String(64), sa.ForeignKey("features.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stage", sa.String(32), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("executor_id", sa.String(128), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("stdout_path", sa.String(512), nullable=True),
        sa.Column("stderr_path", sa.String(512), nullable=True),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fpr_feature_id", "feature_planning_runs", ["feature_id"])
    op.create_index("ix_fpr_stage", "feature_planning_runs", ["stage"])
    op.create_index("ix_fpr_status", "feature_planning_runs", ["status"])
    op.create_index("ix_fpr_trace_id", "feature_planning_runs", ["trace_id"])


def downgrade() -> None:
    op.drop_table("feature_planning_runs")
    op.drop_table("features")
