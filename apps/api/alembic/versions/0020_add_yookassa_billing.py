"""add yookassa billing: products, subscriptions, purchases, payment fields

Revision ID: 0020_add_yookassa_billing
Revises: 0019
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.services.product_catalog import CATALOG

revision = "0020_add_yookassa_billing"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Extend payments with YooKassa columns
    op.add_column("payments", sa.Column("product_slug", sa.String(50), nullable=True))
    op.add_column("payments", sa.Column("idempotence_key", sa.String(64), nullable=True))
    op.add_column("payments", sa.Column("confirmation_token", sa.String(512), nullable=True))
    op.add_column("payments", sa.Column("confirmation_url", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("payment_method_id", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("payment_method_saved", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("payments", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("uq_payments_idempotence_key", "payments", ["idempotence_key"], unique=True)
    op.create_index("uq_payments_provider_payment_id", "payments", ["provider_payment_id"], unique=True)

    # 2. products (catalog seeded from the single source of truth)
    op.create_table(
        "products",
        sa.Column("slug", sa.String(50), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_type", sa.String(30), nullable=False),
        sa.Column("price_kopecks", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("period_days", sa.Integer(), nullable=True),
        sa.Column("horary_quota", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    products_table = sa.table(
        "products",
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("product_type", sa.String),
        sa.column("price_kopecks", sa.Integer),
        sa.column("currency", sa.String),
        sa.column("period_days", sa.Integer),
        sa.column("horary_quota", sa.Integer),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        products_table,
        [
            {
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "product_type": p.product_type,
                "price_kopecks": p.price_kopecks,
                "currency": p.currency,
                "period_days": p.period_days,
                "horary_quota": p.horary_quota,
                "is_active": p.is_active,
            }
            for p in CATALOG
        ],
    )

    # 3. subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_slug", sa.String(50), sa.ForeignKey("products.slug"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("price_kopecks", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="RUB"),
        sa.Column("provider", sa.String(30), nullable=False, server_default="yookassa"),
        sa.Column("payment_method_id", sa.String(255), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_charge_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_subscriptions_user_id_status", "subscriptions", ["user_id", "status"])
    op.create_index("ix_subscriptions_next_charge_at", "subscriptions", ["next_charge_at"])

    # 4. purchases (one-time: horary packs, natal entitlement)
    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_slug", sa.String(50), sa.ForeignKey("products.slug"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("horary_quota_added", sa.Integer(), nullable=True),
        sa.Column("context_hash", sa.String(64), nullable=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_purchases_user_id_status", "purchases", ["user_id", "status"])
    op.create_index("uq_purchases_natal_entitlement", "purchases", ["user_id", "product_slug", "context_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_purchases_natal_entitlement", table_name="purchases")
    op.drop_index("ix_purchases_user_id_status", table_name="purchases")
    op.drop_table("purchases")
    op.drop_index("ix_subscriptions_next_charge_at", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id_status", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("products")
    op.drop_index("uq_payments_provider_payment_id", table_name="payments")
    op.drop_index("uq_payments_idempotence_key", table_name="payments")
    op.drop_column("payments", "canceled_at")
    op.drop_column("payments", "failure_reason")
    op.drop_column("payments", "payment_method_saved")
    op.drop_column("payments", "payment_method_id")
    op.drop_column("payments", "confirmation_url")
    op.drop_column("payments", "confirmation_token")
    op.drop_column("payments", "idempotence_key")
    op.drop_column("payments", "product_slug")
