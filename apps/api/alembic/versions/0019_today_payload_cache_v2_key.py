"""add today payload cache v2 key columns

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-09
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("today_payloads_cache") as batch_op:
        batch_op.add_column(sa.Column("cache_key_hash", sa.String(16), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("calculation_version", sa.String(32), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("activation_layer_version", sa.String(32), nullable=True, server_default=None))
        batch_op.add_column(sa.Column("scoring_version", sa.String(32), nullable=False, server_default="1"))
        batch_op.add_column(sa.Column("canon_versions_hash", sa.String(16), nullable=False, server_default=""))
        batch_op.add_column(sa.Column("llm_prompt_version", sa.Integer, nullable=False, server_default=sa.text("2")))
        batch_op.add_column(sa.Column("frontend_payload_version", sa.Integer, nullable=False, server_default=sa.text("1")))
        # Drop old unique constraint, add new versioned one
        batch_op.drop_constraint("uq_user_date_profile", type_="unique")
        batch_op.create_unique_constraint("uq_user_date_profile_key", ["user_id", "target_date", "profile_hash", "cache_key_hash"])


def downgrade() -> None:
    with op.batch_alter_table("today_payloads_cache") as batch_op:
        batch_op.drop_constraint("uq_user_date_profile_key", type_="unique")
        batch_op.create_unique_constraint("uq_user_date_profile", ["user_id", "target_date", "profile_hash"])
        batch_op.drop_column("frontend_payload_version")
        batch_op.drop_column("llm_prompt_version")
        batch_op.drop_column("canon_versions_hash")
        batch_op.drop_column("scoring_version")
        batch_op.drop_column("activation_layer_version")
        batch_op.drop_column("calculation_version")
        batch_op.drop_column("cache_key_hash")
