# ############################################################################
# AI_HEADER: MODULE_MIGRATION_0032_PENDING_PROMO_TOKEN — add pending_promo_token to users.
# ROLE: Schema migration for storing Telegram WebApp start_param promo token on User model.
# ############################################################################

# START_MODULE_CONTRACT: M-MIGRATION-0032-PENDING-PROMO-TOKEN
# purpose: Add nullable pending_promo_token varchar(16) column to users table.
# owns:
#   - apps/api/alembic/versions/0032_pending_promo_token.py
# inputs: Database at revision 0031_checkin_observed_spheres.
# outputs: Added pending_promo_token column on users table.
# dependencies: Alembic operations and SQLAlchemy Core.
# side_effects: Alters users table schema.
# emitted_logs: none.
# invariants: nullable column without defaults; fully reversible on downgrade.
# failure_policy: alembic operation error propagates.
# END_MODULE_CONTRACT: M-MIGRATION-0032-PENDING-PROMO-TOKEN

# START_MODULE_MAP: M-MIGRATION-0032-PENDING-PROMO-TOKEN
# public_entrypoints:
#   - upgrade
#   - downgrade
# semantic_blocks:
#   - SCHEMA_MIGRATION: add/drop pending_promo_token column on users table.
# owned_tests:
#   - apps/api/tests/test_alembic_roundtrip.py
# END_MODULE_MAP: M-MIGRATION-0032-PENDING-PROMO-TOKEN

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0032_pending_promo_token"
down_revision = "0031_checkin_observed_spheres"
branch_labels = None
depends_on = None


# START_BLOCK: SCHEMA_MIGRATION
def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("pending_promo_token", sa.String(16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "pending_promo_token")
# END_BLOCK: SCHEMA_MIGRATION
