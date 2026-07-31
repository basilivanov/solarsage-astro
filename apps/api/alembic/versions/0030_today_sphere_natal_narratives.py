# ############################################################################
# AI_HEADER: MODULE_MIGRATION_0030_TODAY-SPHERE-NATAL-NARRATIVES — static sphere cache.
# ROLE: Adds the additive profile/sphere/prompt keyed table used by the static
#   sphere page natal narrative layer.
# ############################################################################

# START_MODULE_CONTRACT: M-MIGRATION-0030-TODAY-SPHERE-NATAL-NARRATIVES
# purpose: Create and remove the successful static sphere natal narrative cache.
# owns:
#   - apps/api/alembic/versions/0030_today_sphere_natal_narratives.py
# inputs: Database at revision 0029_today_snapshot_lineage.
# outputs: today_sphere_natal_narratives table, unique identity constraint, and
#   user/sphere lookup index.
# dependencies: Alembic operations and SQLAlchemy Core types only.
# side_effects: Additive table/index creation; downgrade drops only this table.
# emitted_logs: none.
# invariants: null content is allowed at the schema boundary but the runtime
#   never persists a null-content failure row; user deletion cascades.
# failure_policy: migration/database errors propagate and abort the migration.
# END_MODULE_CONTRACT: M-MIGRATION-0030-TODAY-SPHERE-NATAL-NARRATIVES

# START_MODULE_MAP: M-MIGRATION-0030-TODAY-SPHERE-NATAL-NARRATIVES
# public_entrypoints:
#   - upgrade
#   - downgrade
# semantic_blocks:
#   - SPHERE_NATAL_TABLE: additive cache table and identity/index constraints.
#   - SPHERE_NATAL_ROLLBACK: local/CI reverse migration.
# owned_tests:
#   - apps/api/tests/test_today_sphere_natal_postgres.py
# END_MODULE_MAP: M-MIGRATION-0030-TODAY-SPHERE-NATAL-NARRATIVES

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0030_sphere_natal_narr"
down_revision = "0029_today_snapshot_lineage"
branch_labels = None
depends_on = None


# START_BLOCK: SPHERE_NATAL_TABLE
def upgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0030-TODAY-SPHERE-NATAL-NARRATIVES.upgrade
    # purpose: Apply the additive static sphere natal narrative cache schema.
    # inputs: Database at 0029_today_snapshot_lineage.
    # returns: None.
    # side_effects: Creates one table, one unique constraint, and one lookup index.
    # emitted_logs: none.
    # error_behavior: Propagates database/migration errors.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0030-TODAY-SPHERE-NATAL-NARRATIVES.upgrade
    op.create_table(
        "today_sphere_natal_narratives",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("profile_hash", sa.String(length=64), nullable=False),
        sa.Column("sphere_key", sa.String(length=24), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("content_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_today_sphere_natal_narratives_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "profile_hash",
            "sphere_key",
            "prompt_version",
            name="uq_sphere_natal_identity",
        ),
    )
    op.create_index(
        "ix_today_sphere_natal_narratives_user_sphere",
        "today_sphere_natal_narratives",
        ["user_id", "sphere_key"],
    )
# END_BLOCK: SPHERE_NATAL_TABLE


# START_BLOCK: SPHERE_NATAL_ROLLBACK
def downgrade() -> None:
    # START_FUNCTION_CONTRACT: F-M-MIGRATION-0030-TODAY-SPHERE-NATAL-NARRATIVES.downgrade
    # purpose: Remove only the static sphere natal narrative cache additions.
    # inputs: Database at 0030_today_sphere_natal_narratives.
    # returns: None.
    # side_effects: Drops the lookup index and cache table.
    # emitted_logs: none.
    # error_behavior: Propagates database/migration errors.
    # END_FUNCTION_CONTRACT: F-M-MIGRATION-0030-TODAY-SPHERE-NATAL-NARRATIVES.downgrade
    op.drop_index(
        "ix_today_sphere_natal_narratives_user_sphere",
        table_name="today_sphere_natal_narratives",
    )
    op.drop_table("today_sphere_natal_narratives")
# END_BLOCK: SPHERE_NATAL_ROLLBACK
