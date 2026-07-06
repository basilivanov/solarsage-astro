"""add horary chart snapshot

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-06
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("horary_questions") as batch_op:
        batch_op.add_column(sa.Column("chart_snapshot_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("horary_questions") as batch_op:
        batch_op.drop_column("chart_snapshot_json")
