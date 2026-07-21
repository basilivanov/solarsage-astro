"""billing hardening: one live subscription per user + payment attempt anchor

Revision ID: 0021_billing_hardening
Revises: 0020_add_yookassa_billing

- payments.first_attempt_at: anchors the 24h YooKassa Idempotence-Key dedupe
  window; same-key retries are only allowed inside it.
- subscriptions: replace the per-product pending partial unique index with a
  strict ONE LIVE (pending/active/past_due) subscription per user, so
  parallel month+year starts or a new start beside an active/past_due row
  can never create two charge owners.
"""

from alembic import op
import sqlalchemy as sa

revision = "0021_billing_hardening"
down_revision = "0020_add_yookassa_billing"
branch_labels = None
depends_on = None

_LIVE_WHERE = "status IN ('pending', 'active', 'past_due')"


def upgrade() -> None:
    op.add_column("payments", sa.Column("first_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.drop_index("uq_subscriptions_pending_user_product", table_name="subscriptions")
    op.create_index(
        "uq_subscriptions_one_live_per_user",
        "subscriptions",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text(_LIVE_WHERE),
        postgresql_where=sa.text(_LIVE_WHERE),
    )


def downgrade() -> None:
    op.drop_index("uq_subscriptions_one_live_per_user", table_name="subscriptions")
    op.create_index(
        "uq_subscriptions_pending_user_product",
        "subscriptions",
        ["user_id", "product_slug"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_column("payments", "first_attempt_at")
