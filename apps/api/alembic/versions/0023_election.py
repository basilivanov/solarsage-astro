"""Add election astrology tables (election_requests, election_results, election_credit_spends) and seed election_1 product.

Revision ID: 0023_election
Revises: 0022_day_feedback
"""

from alembic import op
import sqlalchemy as sa

revision = "0023_election"
down_revision = "0022_day_feedback"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create election_requests
    op.create_table(
        "election_requests",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("window_from", sa.Date(), nullable=False),
        sa.Column("window_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("client_timezone", sa.String(length=64), nullable=True),
        sa.Column("spent_credit_id", sa.Uuid(as_uuid=True), sa.ForeignKey("horary_credits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("refund_status", sa.String(length=20), server_default="none", nullable=False),
        sa.Column("failure_stage", sa.String(length=50), nullable=True),
        sa.Column("failure_code", sa.String(length=50), nullable=True),
        sa.Column("failure_message", sa.String(length=500), nullable=True),
        sa.Column("public_error_code", sa.String(length=50), nullable=True),
        sa.Column("public_error_message", sa.String(length=500), nullable=True),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_election_requests_user_idempotency"),
    )
    op.create_index("ix_election_requests_user_id", "election_requests", ["user_id"])

    # 2. Create election_results
    op.create_table(
        "election_results",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.Uuid(as_uuid=True), sa.ForeignKey("election_requests.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # 3. Create election_credit_spends
    op.create_table(
        "election_credit_spends",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("credit_id", sa.Uuid(as_uuid=True), sa.ForeignKey("horary_credits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("election_request_id", sa.Uuid(as_uuid=True), sa.ForeignKey("election_requests.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("amount", sa.Integer(), server_default="1", nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("amount = 1", name="ck_election_credit_spends_amount_one"),
        sa.UniqueConstraint("idempotency_key", name="uq_election_credit_spends_idempotency"),
    )
    op.create_index("ix_election_credit_spends_credit_id", "election_credit_spends", ["credit_id"])

    # 4. Insert election_1 product
    op.execute(
        """
        INSERT INTO products (slug, name, description, product_type, price_kopecks, currency, period_days, horary_quota, is_active)
        VALUES (
            'election_1',
            'Подбор даты (1 событие)',
            'Топ-3 лучших даты для твоего события',
            'one_time',
            5000,
            'RUB',
            NULL,
            1,
            true
        ) ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM products WHERE slug = 'election_1';")
    op.drop_index("ix_election_credit_spends_credit_id", table_name="election_credit_spends")
    op.drop_table("election_credit_spends")
    op.drop_table("election_results")
    op.drop_index("ix_election_requests_user_id", table_name="election_requests")
    op.drop_table("election_requests")
