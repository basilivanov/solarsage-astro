"""Add request_hash column to synastry_credit_spends table.

Revision ID: 0026_synastry_spend_request_hash
Revises: 0025_synastry_schema
"""

from alembic import op
import sqlalchemy as sa

revision = "0026_synastry_spend_request_hash"
down_revision = "0025_synastry_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "synastry_credit_spends",
        sa.Column("request_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("synastry_credit_spends", "request_hash")
