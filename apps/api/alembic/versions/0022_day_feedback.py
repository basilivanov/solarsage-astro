"""Add day_feedback table for Telegram bot accuracy feedback.

Revision ID: 0022_day_feedback
Revises: 0021_billing_hardening
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_day_feedback"
down_revision = "0021_billing_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "day_feedback",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column("accuracy", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=20), server_default="tg_bot", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("accuracy >= 1 AND accuracy <= 3", name="ck_day_feedback_accuracy_range"),
        sa.UniqueConstraint("user_id", "target_date", name="uq_day_feedback_user_date"),
    )
    op.create_index("ix_day_feedback_user_id", "day_feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_day_feedback_user_id", table_name="day_feedback")
    op.drop_table("day_feedback")
