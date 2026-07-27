"""Add day_score_history table for relative day status baseline calculation.

Revision ID: 0026_day_score_history
Revises: 0025_synastry_schema
"""

from alembic import op
import sqlalchemy as sa

revision = "0026_day_score_history"
down_revision = "0025_synastry_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "day_score_history",
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("target_date", sa.Date(), primary_key=True, nullable=False),
        sa.Column("support_score", sa.Float(), nullable=False),
        sa.Column("tension_score", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_day_score_history_user_id",
        "day_score_history",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_day_score_history_user_id", table_name="day_score_history")
    op.drop_table("day_score_history")
