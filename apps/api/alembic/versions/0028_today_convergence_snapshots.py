# ############################################################################
# AI_HEADER: MODULE_MIGRATION_0028_TODAY-CONVERGENCE-SNAPSHOTS — additive W3 snapshot schema.
# ROLE: Creates published deterministic snapshots, narrative rows, and nullable
#       EveningCheckin lineage without introducing runtime/service behavior.
# ############################################################################

# START_MODULE_CONTRACT: M-MIGRATION-0028-TODAY-CONVERGENCE-SNAPSHOTS
# purpose: Add the P3-A snapshot, narrative, and EveningCheckin lineage schema.
# owns:
#   - apps/api/alembic/versions/0028_today_convergence_snapshots.py
# inputs: Database at revision 0027_birth_time_mode.
# outputs: Portable SQLite/PostgreSQL-compatible additive tables, constraints,
#   indexes, and nullable check-in lineage fields.
# dependencies: Alembic operations and SQLAlchemy Core types only.
# side_effects: Creates snapshot/narrative tables and adds four check-in columns.
# emitted_logs: none.
# invariants: Revision follows 0027; existing check-in uniqueness/streak and rows
#   remain intact; no legacy Today schema, runtime, or service imports.
# failure_policy: Migration errors propagate and abort the Alembic command.
# END_MODULE_CONTRACT: M-MIGRATION-0028-TODAY-CONVERGENCE-SNAPSHOTS

# START_MODULE_MAP: M-MIGRATION-0028-TODAY-CONVERGENCE-SNAPSHOTS
# public_entrypoints:
#   - upgrade
#   - downgrade
# semantic_blocks:
#   - TODAY_SNAPSHOTS_TABLE: published deterministic snapshot table and identity.
#   - TODAY_SNAPSHOT_NARRATIVES_TABLE: versioned narrative lease/content table.
#   - EVENING_CHECKIN_LINEAGE: nullable additive forecast binding fields.
#   - SNAPSHOT_SCHEMA_ROLLBACK: local/CI reverse migration only.
# owned_tests:
#   - apps/api/tests/test_today_convergence_snapshot_schema.py
# END_MODULE_MAP: M-MIGRATION-0028-TODAY-CONVERGENCE-SNAPSHOTS

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0028_today_convergence_snapshots"
down_revision = "0027_birth_time_mode"
branch_labels = None
depends_on = None


# START_BLOCK: TODAY_SNAPSHOTS_TABLE
def upgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0028-TODAY-CONVERGENCE-SNAPSHOTS.upgrade
    # purpose: Apply additive snapshot, narrative, and check-in lineage schema.
    # inputs: Database at revision 0027_birth_time_mode.
    # returns: None; Alembic applies schema changes.
    # side_effects: Creates two tables, indexes/constraints, and four nullable check-in fields.
    # emitted_logs: none
    # error_behavior: Propagates database/migration errors.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0028-TODAY-CONVERGENCE-SNAPSHOTS.upgrade
    op.create_table(
        "today_snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            nullable=False,
        ),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("canon_hash", sa.String(length=64), nullable=False),
        sa.Column("formula_version", sa.String(length=64), nullable=False),
        sa.Column("calculation_version", sa.String(length=64), nullable=False),
        sa.Column("ephemeris_artifact_id", sa.String(length=128), nullable=False),
        sa.Column("birth_time_mode", sa.String(length=16), nullable=False),
        sa.Column("birth_time_range", sa.JSON(), nullable=False),
        sa.Column("deterministic_result_json", sa.JSON(), nullable=False),
        sa.Column("canonical_input_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("first_day_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_lookahead_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("supersedes_snapshot_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_today_snapshots_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_snapshot_id"],
            ["today_snapshots.id"],
            name="fk_today_snapshots_supersedes_snapshot_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "user_id",
            "target_date",
            "input_hash",
            "formula_version",
            "calculation_version",
            "canon_hash",
            name="uq_today_snapshots_identity",
        ),
        sa.CheckConstraint(
            "birth_time_mode IN ('exact', 'bucket', 'unknown')",
            name="ck_today_snapshots_birth_time_mode",
        ),
    )
    op.create_index(
        "ix_today_snapshots_user_date_published",
        "today_snapshots",
        ["user_id", "target_date", "published_at"],
    )
    op.create_index(
        "ix_today_snapshots_supersedes_snapshot_id",
        "today_snapshots",
        ["supersedes_snapshot_id"],
    )
    _create_narratives()
    _add_checkin_lineage()


# END_BLOCK: TODAY_SNAPSHOTS_TABLE


# START_BLOCK: TODAY_SNAPSHOT_NARRATIVES_TABLE
def _create_narratives() -> None:
    op.create_table(
        "today_snapshot_narratives",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["snapshot_id"],
            ["today_snapshots.id"],
            name="fk_today_snapshot_narratives_snapshot_id",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "snapshot_id",
            "prompt_version",
            name="uq_today_snapshot_narratives_version",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'ready', 'unavailable')",
            name="ck_today_snapshot_narratives_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name="ck_today_snapshot_narratives_attempt_count",
        ),
    )
    op.create_index(
        "ix_today_snapshot_narratives_status_retry",
        "today_snapshot_narratives",
        ["status", "next_retry_at"],
    )


# END_BLOCK: TODAY_SNAPSHOT_NARRATIVES_TABLE


# START_BLOCK: EVENING_CHECKIN_LINEAGE
def _add_checkin_lineage() -> None:
    with op.batch_alter_table("evening_checkins") as batch_op:
        batch_op.add_column(sa.Column("forecast_snapshot_id", sa.Uuid(as_uuid=True), nullable=True))
        batch_op.add_column(sa.Column("prediction_seen_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("prediction_seen_surface", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("observed_spheres", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_evening_checkins_forecast_snapshot_id",
            "today_snapshots",
            ["forecast_snapshot_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_check_constraint(
            "ck_evening_checkins_prediction_seen_surface",
            "prediction_seen_surface IS NULL OR prediction_seen_surface IN ('day', 'lookahead')",
        )
    op.create_index(
        "ix_evening_checkins_forecast_snapshot_id",
        "evening_checkins",
        ["forecast_snapshot_id"],
    )


# END_BLOCK: EVENING_CHECKIN_LINEAGE


# START_BLOCK: SNAPSHOT_SCHEMA_ROLLBACK
def downgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0028-TODAY-CONVERGENCE-SNAPSHOTS.downgrade
    # purpose: Remove only the local/CI schema additions from revision 0028.
    # inputs: Database at revision 0028_today_convergence_snapshots.
    # returns: None; legacy check-in columns and uniqueness remain after removal.
    # side_effects: Drops the lineage fields/index, narrative table, and snapshot table.
    # emitted_logs: none
    # error_behavior: Propagates database/migration errors.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0028-TODAY-CONVERGENCE-SNAPSHOTS.downgrade
    op.drop_index("ix_evening_checkins_forecast_snapshot_id", table_name="evening_checkins")
    with op.batch_alter_table("evening_checkins") as batch_op:
        batch_op.drop_constraint("ck_evening_checkins_prediction_seen_surface", type_="check")
        batch_op.drop_constraint("fk_evening_checkins_forecast_snapshot_id", type_="foreignkey")
        batch_op.drop_column("observed_spheres")
        batch_op.drop_column("prediction_seen_surface")
        batch_op.drop_column("prediction_seen_at")
        batch_op.drop_column("forecast_snapshot_id")
    op.drop_index("ix_today_snapshot_narratives_status_retry", table_name="today_snapshot_narratives")
    op.drop_table("today_snapshot_narratives")
    op.drop_index("ix_today_snapshots_supersedes_snapshot_id", table_name="today_snapshots")
    op.drop_index("ix_today_snapshots_user_date_published", table_name="today_snapshots")
    op.drop_table("today_snapshots")


# END_BLOCK: SNAPSHOT_SCHEMA_ROLLBACK
