"""add yookassa billing: products, subscriptions, purchases, payment fields

Revision ID: 0020_add_yookassa_billing
Revises: 0019

IMMUTABLE: the product seed below is a literal snapshot of the catalog at
migration time (99/999/399 RUB, horary packs). Runtime code reads the
products table, not this file; future price changes land ONLY as explicit
later migrations. Do NOT import runtime modules here.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0020_add_yookassa_billing"
down_revision = "0019"
branch_labels = None
depends_on = None


_PRODUCTS_SEED = [
    # (slug, name, description, product_type, price_kopecks, currency, period_days, horary_quota, is_active)
    ("subscription_month", "Подписка на 1 месяц", "Полный доступ ко всем разборам и хорарным вопросам на 30 дней", "subscription_recurrent", 9900, "RUB", 30, None, True),
    ("subscription_year", "Подписка на 1 год", "Полный доступ ко всем разборам и хорарным вопросам на 365 дней", "subscription_recurrent", 99900, "RUB", 365, None, True),
    ("natal_full_report", "Полный натальный разбор", "Полный отчёт по натальной карте для текущего контекста (разовая покупка)", "one_time", 39900, "RUB", None, None, True),
    ("horary_1", "1 хорарный вопрос", "Один вопрос к хорарному оракулу", "one_time", 5000, "RUB", None, 1, True),
    ("horary_3", "3 хорарных вопроса", "Три вопроса к хорарному оракулу", "one_time", 12000, "RUB", None, 3, True),
    ("horary_5", "5 хорарных вопросов", "Пять вопросов к хорарному оракулу", "one_time", 18000, "RUB", None, 5, True),
    ("horary_10", "10 хорарных вопросов", "Десять вопросов к хорарному оракулу", "one_time", 30000, "RUB", None, 10, True),
    ("synastry", "Синастрия", "Полный разбор совместимости двух натальных карт (пока не продаётся)", "one_time", 39900, "RUB", None, None, False),
]


def upgrade() -> None:
    # 1. Extend payments with YooKassa columns + strict subscription link
    op.add_column("payments", sa.Column("product_slug", sa.String(50), nullable=True))
    op.add_column("payments", sa.Column("idempotence_key", sa.String(64), nullable=True))
    op.add_column("payments", sa.Column("confirmation_token", sa.String(512), nullable=True))
    op.add_column("payments", sa.Column("confirmation_url", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("payment_method_id", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("payment_method_saved", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("payments", sa.Column("failure_reason", sa.Text(), nullable=True))
    op.add_column("payments", sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("payments", sa.Column("subscription_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("uq_payments_idempotence_key", "payments", ["idempotence_key"], unique=True)
    op.create_index("uq_payments_provider_payment_id", "payments", ["provider_payment_id"], unique=True)
    op.create_index("ix_payments_subscription_id", "payments", ["subscription_id"])

    # 2. products (literal immutable snapshot; runtime reads only the table)
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
                "slug": slug,
                "name": name,
                "description": description,
                "product_type": product_type,
                "price_kopecks": price_kopecks,
                "currency": currency,
                "period_days": period_days,
                "horary_quota": horary_quota,
                "is_active": is_active,
            }
            for (slug, name, description, product_type, price_kopecks, currency, period_days, horary_quota, is_active) in _PRODUCTS_SEED
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
    op.create_index(
        "uq_subscriptions_pending_user_product",
        "subscriptions",
        ["user_id", "product_slug"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )
    # FK added via batch mode: SQLite cannot ALTER existing tables with new
    # constraints; batch is a no-op passthrough on PostgreSQL.
    with op.batch_alter_table("payments") as batch_op:
        batch_op.create_foreign_key(
            "fk_payments_subscription_id",
            "subscriptions",
            ["subscription_id"],
            ["id"],
        )

    # 4. purchases (one-time: horary packs, natal entitlement)
    op.create_table(
        "purchases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_slug", sa.String(50), sa.ForeignKey("products.slug"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("horary_quota_added", sa.Integer(), nullable=True),
        sa.Column("context_hash", sa.String(64), nullable=False, server_default=""),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_purchases_user_id_status", "purchases", ["user_id", "status"])
    op.create_index(
        "uq_purchases_pending_user_product",
        "purchases",
        ["user_id", "product_slug", "context_hash"],
        unique=True,
        sqlite_where=sa.text("status = 'pending'"),
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "uq_purchases_natal_entitlement",
        "purchases",
        ["user_id", "context_hash"],
        unique=True,
        sqlite_where=sa.text("product_slug = 'natal_full_report' AND status IN ('succeeded', 'delivered')"),
        postgresql_where=sa.text("product_slug = 'natal_full_report' AND status IN ('succeeded', 'delivered')"),
    )


def downgrade() -> None:
    op.drop_index("uq_purchases_natal_entitlement", table_name="purchases")
    op.drop_index("uq_purchases_pending_user_product", table_name="purchases")
    op.drop_index("ix_purchases_user_id_status", table_name="purchases")
    op.drop_table("purchases")
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint("fk_payments_subscription_id", type_="foreignkey")
    op.drop_index("uq_subscriptions_pending_user_product", table_name="subscriptions")
    op.drop_index("ix_subscriptions_next_charge_at", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id_status", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_table("products")
    op.drop_index("ix_payments_subscription_id", table_name="payments")
    op.drop_index("uq_payments_provider_payment_id", table_name="payments")
    op.drop_index("uq_payments_idempotence_key", table_name="payments")
    op.drop_column("payments", "subscription_id")
    op.drop_column("payments", "canceled_at")
    op.drop_column("payments", "failure_reason")
    op.drop_column("payments", "payment_method_saved")
    op.drop_column("payments", "payment_method_id")
    op.drop_column("payments", "confirmation_url")
    op.drop_column("payments", "confirmation_token")
    op.drop_column("payments", "idempotence_key")
    op.drop_column("payments", "product_slug")
