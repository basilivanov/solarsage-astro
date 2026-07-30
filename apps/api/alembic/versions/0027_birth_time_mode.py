# ############################################################################
# AI_HEADER: MODULE_MIGRATION_0027_BIRTH_TIME_MODE — persist birth-time mode.
# ROLE: Adds additive birth-time precision fields and deterministically
#       backfills legacy user_profiles rows.
# ############################################################################

# START_MODULE_CONTRACT: M-MIGRATION-0027-BIRTH-TIME-MODE
# purpose: Add birth_time_mode, birth_time_bucket, and
#   birth_time_prompt_dismissed to user_profiles and backfill legacy rows.
# owns:
#   - apps/api/alembic/versions/0027_birth_time_mode.py
# inputs: Existing user_profiles.birth_time values.
# outputs: Constrained persistence fields with deterministic legacy values.
# dependencies: Alembic operations and SQLAlchemy Core expressions.
# side_effects: Alters user_profiles schema and updates existing rows.
# emitted_logs: none
# invariants:
#   - Revision 0027 follows 0026_day_score_history.
#   - Existing non-NULL birth_time becomes exact and not dismissed.
#   - Existing NULL birth_time becomes unknown and dismissed.
#   - New rows default to unknown, NULL bucket, and false dismissal.
#   - Downgrade removes only the three added fields and their constraints.
# failure_policy: Migration errors propagate and abort the Alembic command.
# END_MODULE_CONTRACT: M-MIGRATION-0027-BIRTH-TIME-MODE

# START_MODULE_MAP: M-MIGRATION-0027-BIRTH-TIME-MODE
# public_entrypoints:
#   - upgrade
#   - downgrade
# semantic_blocks:
#   - BIRTH_TIME_COLUMNS: add constrained additive fields
#   - LEGACY_BACKFILL: map old birth_time values to mode/dismissal
#   - BIRTH_TIME_ROLLBACK: remove only this migration's schema additions
# owned_tests:
#   - apps/api/tests/test_birth_time_mode_migration.py
# END_MODULE_MAP: M-MIGRATION-0027-BIRTH-TIME-MODE

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0027_birth_time_mode"
down_revision = "0026_day_score_history"
branch_labels = None
depends_on = None


# START_BLOCK: BIRTH_TIME_COLUMNS
def upgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0027-BIRTH-TIME-MODE.upgrade
    # purpose: Add the three birth-time persistence fields and backfill legacy rows.
    # inputs: Existing user_profiles table.
    # returns: None; Alembic applies the schema/data change.
    # side_effects: Alters user_profiles and updates legacy rows.
    # emitted_logs: none
    # error_behavior: Propagates database/migration errors.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0027-BIRTH-TIME-MODE.upgrade
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.add_column(
            sa.Column(
                "birth_time_mode",
                sa.String(length=16),
                server_default="unknown",
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("birth_time_bucket", sa.String(length=16), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "birth_time_prompt_dismissed",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_user_profiles_birth_time_mode",
            "birth_time_mode IN ('exact', 'bucket', 'unknown')",
        )
        batch_op.create_check_constraint(
            "ck_user_profiles_birth_time_bucket",
            "birth_time_bucket IS NULL OR birth_time_bucket IN ('night', 'morning', 'day', 'evening')",
        )

    # START_BLOCK: LEGACY_BACKFILL
    user_profiles = sa.table(
        "user_profiles",
        sa.column("birth_time"),
        sa.column("birth_time_mode"),
        sa.column("birth_time_bucket"),
        sa.column("birth_time_prompt_dismissed"),
    )
    op.execute(
        sa.update(user_profiles).values(
            birth_time_mode=sa.case(
                (user_profiles.c.birth_time.is_not(None), "exact"),
                else_="unknown",
            ),
            birth_time_bucket=None,
            birth_time_prompt_dismissed=sa.case(
                (user_profiles.c.birth_time.is_(None), sa.true()),
                else_=sa.false(),
            ),
        )
    )
    # END_BLOCK: LEGACY_BACKFILL


# END_BLOCK: BIRTH_TIME_COLUMNS


# START_BLOCK: BIRTH_TIME_ROLLBACK
def downgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0027-BIRTH-TIME-MODE.downgrade
    # purpose: Remove only the 0027 birth-time fields and their constraints.
    # inputs: user_profiles table at revision 0027.
    # returns: None; legacy profile columns remain intact.
    # side_effects: Alters user_profiles schema.
    # emitted_logs: none
    # error_behavior: Propagates database/migration errors.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0027-BIRTH-TIME-MODE.downgrade
    with op.batch_alter_table("user_profiles") as batch_op:
        batch_op.drop_constraint(
            "ck_user_profiles_birth_time_bucket", type_="check"
        )
        batch_op.drop_constraint("ck_user_profiles_birth_time_mode", type_="check")
        batch_op.drop_column("birth_time_prompt_dismissed")
        batch_op.drop_column("birth_time_bucket")
        batch_op.drop_column("birth_time_mode")


# END_BLOCK: BIRTH_TIME_ROLLBACK
