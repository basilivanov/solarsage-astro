"""Add synastry tables and update products.synastry quota.

Revision ID: 0025_synastry_schema
Revises: 0024_named_promo_campaign
"""

from alembic import op
import sqlalchemy as sa

revision = "0025_synastry_schema"
down_revision = "0024_named_promo_campaign"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create synastry_partners
    op.create_table(
        "synastry_partners",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "relation_type",
            sa.String(length=30),
            server_default="romantic",
            nullable=False,
        ),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("birth_time", sa.Time(), nullable=True),
        sa.Column("birth_city", sa.String(length=200), nullable=True),
        sa.Column("birth_lat", sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column("birth_lon", sa.Numeric(precision=9, scale=5), nullable=True),
        sa.Column("birth_tz", sa.String(length=64), nullable=True),
        sa.Column(
            "precision",
            sa.String(length=20),
            server_default="exact",
            nullable=False,
        ),
        sa.Column("partner_input_hash", sa.String(length=64), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "birth_lat IS NULL OR (birth_lat >= -90 AND birth_lat <= 90)",
            name="ck_synastry_partners_birth_lat_range",
        ),
        sa.CheckConstraint(
            "birth_lon IS NULL OR (birth_lon >= -180 AND birth_lon <= 180)",
            name="ck_synastry_partners_birth_lon_range",
        ),
    )
    op.create_index(
        "ix_synastry_partners_owner_id", "synastry_partners", ["owner_id"]
    )
    op.create_index(
        "ix_synastry_partners_partner_input_hash",
        "synastry_partners",
        ["partner_input_hash"],
    )
    op.create_index(
        "ix_synastry_partners_owner_hash_active",
        "synastry_partners",
        ["owner_id", "partner_input_hash"],
        unique=True,
        postgresql_where=sa.text("invalidated_at IS NULL"),
        sqlite_where=sa.text("invalidated_at IS NULL"),
    )

    # 2. Create synastry_reports
    op.create_table(
        "synastry_reports",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "partner_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("synastry_partners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("owner_profile_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "engine_version",
            sa.String(length=32),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "calculation_version",
            sa.String(length=32),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "prompt_version",
            sa.String(length=32),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "report_schema_version",
            sa.String(length=32),
            server_default="synastry/v1",
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=50), nullable=True),
        sa.Column(
            "attempt_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deterministic_payload_json", sa.Text(), nullable=True),
        sa.Column("narrative_payload_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_synastry_reports_owner_id", "synastry_reports", ["owner_id"]
    )
    op.create_index(
        "ix_synastry_reports_partner_id", "synastry_reports", ["partner_id"]
    )
    op.create_index(
        "ix_synastry_reports_owner_partner_active",
        "synastry_reports",
        [
            "owner_id",
            "partner_id",
            "owner_profile_hash",
            "engine_version",
            "calculation_version",
            "prompt_version",
        ],
        unique=True,
        postgresql_where=sa.text("invalidated_at IS NULL"),
        sqlite_where=sa.text("invalidated_at IS NULL"),
    )

    # 3. Create synastry_aspect_details
    op.create_table(
        "synastry_aspect_details",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "report_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("synastry_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("aspect_id", sa.String(length=64), nullable=False),
        sa.Column(
            "prompt_version",
            sa.String(length=32),
            server_default="1",
            nullable=False,
        ),
        sa.Column(
            "state",
            sa.String(length=32),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "attempt_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "report_id",
            "aspect_id",
            "prompt_version",
            name="uq_synastry_aspect_details_report_aspect_prompt",
        ),
    )
    op.create_index(
        "ix_synastry_aspect_details_report_id",
        "synastry_aspect_details",
        ["report_id"],
    )

    # 4. Create synastry_feedback
    op.create_table(
        "synastry_feedback",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("synastry_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "report_id", name="uq_synastry_feedback_user_report"
        ),
    )
    op.create_index(
        "ix_synastry_feedback_user_id", "synastry_feedback", ["user_id"]
    )
    op.create_index(
        "ix_synastry_feedback_report_id", "synastry_feedback", ["report_id"]
    )

    # 5. Create synastry_credit_spends
    op.create_table(
        "synastry_credit_spends",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "credit_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("horary_credits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "report_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("synastry_reports.id", ondelete="SET NULL"),
            nullable=True,
            unique=True,
        ),
        sa.Column("amount", sa.Integer(), server_default="1", nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "amount = 1", name="ck_synastry_credit_spends_amount_one"
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_synastry_credit_spends_idempotency"
        ),
    )
    op.create_index(
        "ix_synastry_credit_spends_user_id",
        "synastry_credit_spends",
        ["user_id"],
    )
    op.create_index(
        "ix_synastry_credit_spends_credit_id",
        "synastry_credit_spends",
        ["credit_id"],
    )

    # 6. Update products.synastry quota to 1 (keeping is_active=false)
    op.execute(
        "UPDATE products SET horary_quota = 1 WHERE slug = 'synastry';"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE products SET horary_quota = NULL WHERE slug = 'synastry';"
    )
    op.drop_index(
        "ix_synastry_credit_spends_credit_id", table_name="synastry_credit_spends"
    )
    op.drop_index(
        "ix_synastry_credit_spends_user_id", table_name="synastry_credit_spends"
    )
    op.drop_table("synastry_credit_spends")

    op.drop_index(
        "ix_synastry_feedback_report_id", table_name="synastry_feedback"
    )
    op.drop_index(
        "ix_synastry_feedback_user_id", table_name="synastry_feedback"
    )
    op.drop_table("synastry_feedback")

    op.drop_index(
        "ix_synastry_aspect_details_report_id",
        table_name="synastry_aspect_details",
    )
    op.drop_table("synastry_aspect_details")

    op.drop_index(
        "ix_synastry_reports_owner_partner_active",
        table_name="synastry_reports",
    )
    op.drop_index(
        "ix_synastry_reports_partner_id", table_name="synastry_reports"
    )
    op.drop_index(
        "ix_synastry_reports_owner_id", table_name="synastry_reports"
    )
    op.drop_table("synastry_reports")

    op.drop_index(
        "ix_synastry_partners_owner_hash_active",
        table_name="synastry_partners",
    )
    op.drop_index(
        "ix_synastry_partners_partner_input_hash",
        table_name="synastry_partners",
    )
    op.drop_index(
        "ix_synastry_partners_owner_id", table_name="synastry_partners"
    )
    op.drop_table("synastry_partners")
