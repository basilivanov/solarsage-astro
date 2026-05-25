"""W-1.2: users + user_profiles + sessions (Option A — opaque cookie + server store)

Revision ID: 0001_users
Revises: 0000_baseline
Create Date: 2026-05-25 00:00:00

Introduces the three tables owned jointly by M-AUTH-TG (users + sessions)
and M-PROFILE (user_profiles). See apps/api/app/db/models.py for canonical
column descriptions; this migration mirrors them exactly. Single revision
per W-1.2 ## Decision (atomic upgrade/downgrade).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_users"
down_revision: Union[str, None] = "0000_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("tg_username", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("tg_user_id", name="uq_users_tg_user_id"),
    )
    op.create_index("ix_users_tg_user_id", "users", ["tg_user_id"], unique=False)

    op.create_table(
        "user_profiles",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("first_name", sa.String(length=120), nullable=True),
        sa.Column("birthday", sa.Date(), nullable=True),
        sa.Column("birth_time", sa.Time(), nullable=True),
        sa.Column("birth_city", sa.String(length=200), nullable=True),
        sa.Column("birth_lat", sa.Numeric(precision=8, scale=5), nullable=True),
        sa.Column("birth_lon", sa.Numeric(precision=9, scale=5), nullable=True),
        sa.Column("birth_tz", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "birth_lat IS NULL OR (birth_lat >= -90 AND birth_lat <= 90)",
            name="ck_user_profiles_birth_lat_range",
        ),
        sa.CheckConstraint(
            "birth_lon IS NULL OR (birth_lon >= -180 AND birth_lon <= 180)",
            name="ck_user_profiles_birth_lon_range",
        ),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("token_hash", name="uq_sessions_token_hash"),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index(
        "ix_sessions_expires_at", "sessions", ["expires_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("user_profiles")
    op.drop_index("ix_users_tg_user_id", table_name="users")
    op.drop_table("users")
