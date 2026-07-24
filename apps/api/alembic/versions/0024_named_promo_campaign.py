"""Add PromoCampaign and PromoRedemption tables.

Revision ID: 0024_named_promo_campaign
Revises: 0023_election
"""

from alembic import op
import sqlalchemy as sa

revision = "0024_named_promo_campaign"
down_revision = "0023_election"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create promo_campaigns
    op.create_table(
        "promo_campaigns",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("activation_starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activation_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_redemptions", sa.Integer(), nullable=False),
        sa.Column("redemptions_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("access_days", sa.Integer(), server_default="30", nullable=False),
        sa.Column("bonus_credits", sa.Integer(), server_default="50", nullable=False),
        sa.Column("unlock_natal", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code_hash", name="uq_promo_campaigns_code_hash"),
        sa.CheckConstraint("activation_ends_at > activation_starts_at", name="ck_promo_campaigns_window"),
        sa.CheckConstraint("max_redemptions > 0", name="ck_promo_campaigns_max_redemptions_pos"),
        sa.CheckConstraint("redemptions_used >= 0 AND redemptions_used <= max_redemptions", name="ck_promo_campaigns_redemptions_used_range"),
        sa.CheckConstraint("access_days >= 0", name="ck_promo_campaigns_access_days_nonneg"),
        sa.CheckConstraint("bonus_credits >= 0", name="ck_promo_campaigns_bonus_credits_nonneg"),
        sa.CheckConstraint("bonus_credits = 0 OR access_days > 0", name="ck_promo_campaigns_credits_require_access"),
        sa.CheckConstraint("access_days > 0 OR bonus_credits > 0 OR unlock_natal = TRUE", name="ck_promo_campaigns_at_least_one_benefit"),
    )

    # 2. Create promo_redemptions
    op.create_table(
        "promo_redemptions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", sa.Uuid(as_uuid=True), sa.ForeignKey("promo_campaigns.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("access_ledger_id", sa.Uuid(as_uuid=True), sa.ForeignKey("access_ledger.id", ondelete="SET NULL"), nullable=True),
        sa.Column("credit_id", sa.Uuid(as_uuid=True), sa.ForeignKey("horary_credits.id", ondelete="SET NULL"), nullable=True),
        sa.Column("natal_purchase_id", sa.Uuid(as_uuid=True), sa.ForeignKey("purchases.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("campaign_id", "user_id", name="uq_promo_redemptions_campaign_user"),
    )
    op.create_index("ix_promo_redemptions_campaign_redeemed", "promo_redemptions", ["campaign_id", "redeemed_at"])
    op.create_index("ix_promo_redemptions_user_id", "promo_redemptions", ["user_id"])


def downgrade() -> None:
    # Drop redemption first, then campaign
    op.drop_index("ix_promo_redemptions_user_id", table_name="promo_redemptions")
    op.drop_index("ix_promo_redemptions_campaign_redeemed", table_name="promo_redemptions")
    op.drop_table("promo_redemptions")
    op.drop_table("promo_campaigns")
