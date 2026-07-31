# ############################################################################
# AI_HEADER: MODULE_MIGRATION_0029_TODAY-SNAPSHOT-LINEAGE-GUARDS — PostgreSQL lineage immutability.
# ROLE: Replaces the nullable-parent index with a partial unique guard and
#       installs owner/date and immutable-column trigger enforcement.
# ############################################################################

# START_MODULE_CONTRACT: M-MIGRATION-0029-TODAY-SNAPSHOT-LINEAGE-GUARDS
# purpose: Enforce deterministic Today snapshot supersession and first-seen timestamp immutability.
# owns:
#   - apps/api/alembic/versions/0029_today_snapshot_lineage_guards.py
# inputs: Database at revision 0028_today_convergence_snapshots.
# outputs: Partial unique parent index and PostgreSQL lineage trigger/function.
# dependencies: Alembic operations, PostgreSQL PL/pgSQL, today_snapshots from 0028.
# side_effects: Replaces one index and creates/drops one PostgreSQL trigger/function.
# emitted_logs: none.
# invariants: no row/table/column data is removed; SQLite gets index shape only and
#   never substitutes for PostgreSQL trigger semantics.
# failure_policy: Database/migration failures propagate and abort the migration.
# END_MODULE_CONTRACT: M-MIGRATION-0029-TODAY-SNAPSHOT-LINEAGE-GUARDS

# START_MODULE_MAP: M-MIGRATION-0029-TODAY-SNAPSHOT-LINEAGE-GUARDS
# public_entrypoints:
#   - upgrade
#   - downgrade
# semantic_blocks:
#   - SUPERSESSION_INDEX: one direct successor for every non-null parent.
#   - POSTGRES_LINEAGE_GUARD: owner/date insert and immutable update trigger.
#   - LINEAGE_ROLLBACK: trigger/function and index restoration.
# owned_tests:
#   - apps/api/tests/test_today_snapshot_lineage.py
#   - apps/api/tests/test_today_snapshot_lineage_postgres.py
# END_MODULE_MAP: M-MIGRATION-0029-TODAY-SNAPSHOT-LINEAGE-GUARDS

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0029_today_snapshot_lineage"
down_revision = "0028_today_convergence_snapshots"
branch_labels = None
depends_on = None

_INDEX_NAME = "ix_today_snapshots_supersedes_snapshot_id"
_TRIGGER_NAME = "trg_today_snapshots_lineage_guard"
_FUNCTION_NAME = "today_snapshots_lineage_guard"


# START_BLOCK: POSTGRES_LINEAGE_GUARD
def _install_postgres_guard() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        sa.text(
            f"""
            CREATE OR REPLACE FUNCTION {_FUNCTION_NAME}()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            DECLARE
                parent_user_id uuid;
                parent_target_date date;
            BEGIN
                IF TG_OP = 'INSERT' AND NEW.supersedes_snapshot_id IS NOT NULL THEN
                    IF NEW.supersedes_snapshot_id = NEW.id THEN
                        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'today snapshot self lineage';
                    END IF;

                    SELECT user_id, target_date
                      INTO parent_user_id, parent_target_date
                      FROM today_snapshots
                     WHERE id = NEW.supersedes_snapshot_id;

                    IF FOUND AND (parent_user_id IS DISTINCT FROM NEW.user_id
                                  OR parent_target_date IS DISTINCT FROM NEW.target_date) THEN
                        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'today snapshot parent scope';
                    END IF;
                END IF;

                IF TG_OP = 'UPDATE' THEN
                    IF OLD.id IS DISTINCT FROM NEW.id
                       OR OLD.user_id IS DISTINCT FROM NEW.user_id
                       OR OLD.target_date IS DISTINCT FROM NEW.target_date
                       OR OLD.timezone IS DISTINCT FROM NEW.timezone
                       OR OLD.profile_hash IS DISTINCT FROM NEW.profile_hash
                       OR OLD.input_hash IS DISTINCT FROM NEW.input_hash
                       OR OLD.canon_hash IS DISTINCT FROM NEW.canon_hash
                       OR OLD.formula_version IS DISTINCT FROM NEW.formula_version
                       OR OLD.calculation_version IS DISTINCT FROM NEW.calculation_version
                       OR OLD.ephemeris_artifact_id IS DISTINCT FROM NEW.ephemeris_artifact_id
                       OR OLD.birth_time_mode IS DISTINCT FROM NEW.birth_time_mode
                       OR OLD.birth_time_range::jsonb IS DISTINCT FROM NEW.birth_time_range::jsonb
                       OR OLD.deterministic_result_json::jsonb IS DISTINCT FROM NEW.deterministic_result_json::jsonb
                       OR OLD.canonical_input_json::jsonb IS DISTINCT FROM NEW.canonical_input_json::jsonb
                       OR OLD.created_at IS DISTINCT FROM NEW.created_at
                       OR OLD.published_at IS DISTINCT FROM NEW.published_at
                       OR OLD.supersedes_snapshot_id IS DISTINCT FROM NEW.supersedes_snapshot_id THEN
                        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'today snapshot immutable';
                    END IF;

                    IF OLD.first_day_seen_at IS NOT NULL
                       AND OLD.first_day_seen_at IS DISTINCT FROM NEW.first_day_seen_at THEN
                        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'today snapshot day impression immutable';
                    END IF;
                    IF OLD.first_lookahead_seen_at IS NOT NULL
                       AND OLD.first_lookahead_seen_at IS DISTINCT FROM NEW.first_lookahead_seen_at THEN
                        RAISE EXCEPTION USING ERRCODE = '23514', MESSAGE = 'today snapshot lookahead impression immutable';
                    END IF;
                END IF;

                RETURN NEW;
            END;
            $$;
            """
        )
    )
    op.execute(
        sa.text(
            f"""
            CREATE TRIGGER {_TRIGGER_NAME}
            BEFORE INSERT OR UPDATE ON today_snapshots
            FOR EACH ROW EXECUTE FUNCTION {_FUNCTION_NAME}();
            """
        )
    )
# END_BLOCK: POSTGRES_LINEAGE_GUARD


# START_BLOCK: SUPERSESSION_INDEX
def upgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0029-TODAY-SNAPSHOT-LINEAGE-GUARDS.upgrade
    # purpose: Install the parent successor guard after revision 0028.
    # inputs: Database at 0028_today_convergence_snapshots.
    # returns: None.
    # side_effects: Replaces one index and installs PostgreSQL trigger/function.
    # emitted_logs: none.
    # error_behavior: Propagates migration/database failures.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0029-TODAY-SNAPSHOT-LINEAGE-GUARDS.upgrade
    op.drop_index(_INDEX_NAME, table_name="today_snapshots")
    op.create_index(
        _INDEX_NAME,
        "today_snapshots",
        ["supersedes_snapshot_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_snapshot_id IS NOT NULL"),
        sqlite_where=sa.text("supersedes_snapshot_id IS NOT NULL"),
    )
    _install_postgres_guard()
# END_BLOCK: SUPERSESSION_INDEX


# START_BLOCK: LINEAGE_ROLLBACK
def downgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0029-TODAY-SNAPSHOT-LINEAGE-GUARDS.downgrade
    # purpose: Remove only revision-0029 guards and restore the 0028 index.
    # inputs: Database at 0029_today_snapshot_lineage.
    # returns: None.
    # side_effects: Drops trigger/function and restores the ordinary index.
    # emitted_logs: none.
    # error_behavior: Propagates migration/database failures.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0029-TODAY-SNAPSHOT-LINEAGE-GUARDS.downgrade
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS {_TRIGGER_NAME} ON today_snapshots"))
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS {_FUNCTION_NAME}()"))
    op.drop_index(_INDEX_NAME, table_name="today_snapshots")
    op.create_index(_INDEX_NAME, "today_snapshots", ["supersedes_snapshot_id"])
# END_BLOCK: LINEAGE_ROLLBACK
