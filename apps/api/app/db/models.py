# ############################################################################
# AI_HEADER: MODULE_DB_MODELS
# ROLE: ORM models for users, user_profiles, sessions (W-1.2 / Option A).
# DEPENDENCIES: sqlalchemy, app.db.session.Base
# GRACE_ANCHORS: [USERS_TABLE, USER_PROFILES_TABLE, SESSIONS_TABLE]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.models
# purpose: Declarative ORM models for `users`, `user_profiles`, and
#   `sessions`. Owned jointly by M-AUTH-TG (users + sessions) and
#   M-PROFILE (user_profiles). Single file because they share the same
#   Base and the FKs live on profiles + sessions.
# owns:
#   - apps/api/app/db/models.py
# inputs:
#   - app.db.session.Base (DeclarativeBase singleton)
# outputs:
#   - User: row in `users` keyed by UUID, unique tg_user_id
#   - UserProfile: row in `user_profiles` (1:1 with User), birth data
#   - Session: row in `sessions`, opaque-token-hash → user_id mapping
# dependencies:
#   - M-DB-SESSION (Base)
#   - alembic 0001_users migration creates the corresponding tables
# side_effects:
#   - importing this module registers tables on Base.metadata
# invariants:
#   - User.id is the natural PK (UUID); tg_user_id is a UNIQUE BIGINT
#   - UserProfile.user_id is both PK and FK -> users.id (1:1)
#   - Session.token_hash is CHAR(64) UNIQUE (sha256-hex of the opaque token)
#   - timestamps are always UTC (server_default=now()) and never null
#   - sensitive birth data lives ONLY on UserProfile, never on User
# failure_policy:
#   - schema mismatches surface as alembic drift; this module never papers
#     over them with `extend_existing` or `Column.nullable=True`
# non_goals:
#   - no business logic / no service methods on the models
#   - no relationship cascades beyond the explicit FK ondelete
# END_MODULE_CONTRACT: M-AUTH-TG.models

# START_MODULE_MAP: M-AUTH-TG.models
# public_entrypoints:
#   - User
#   - UserProfile
#   - Session
# semantic_blocks:
#   - USERS_TABLE: declarative class User -> "users"
#   - USER_PROFILES_TABLE: declarative class UserProfile -> "user_profiles"
#   - SESSIONS_TABLE: declarative class Session -> "sessions"
# owned_tests:
#   - apps/api/tests/test_auth_endpoints.py
#   - apps/api/tests/test_profile_endpoints.py
#   - apps/api/tests/test_alembic_roundtrip.py
# END_MODULE_MAP: M-AUTH-TG.models

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Time,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# START_BLOCK: USERS_TABLE
class User(Base):
    """Telegram-identified user. Created on first successful auth callback."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tg_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    tg_username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    profile: Mapped["UserProfile | None"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
# END_BLOCK: USERS_TABLE


# START_BLOCK: USER_PROFILES_TABLE
class UserProfile(Base):
    """Birth data and display preferences. 1:1 with User."""

    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint(
            "birth_lat IS NULL OR (birth_lat >= -90 AND birth_lat <= 90)",
            name="ck_user_profiles_birth_lat_range",
        ),
        CheckConstraint(
            "birth_lon IS NULL OR (birth_lon >= -180 AND birth_lon <= 180)",
            name="ck_user_profiles_birth_lon_range",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    birth_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    birth_lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    birth_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 5), nullable=True)
    birth_tz: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # W-1.3: onboarding status (true when birth data is complete)
    is_onboarded: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="profile")
# END_BLOCK: USER_PROFILES_TABLE


# START_BLOCK: SESSIONS_TABLE
class Session(Base):
    """Server-side session row. Opaque-token-hash keyed (Option A)."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # sha256-hex of the opaque token (64 chars). UNIQUE so a stolen token
    # is single-use and trivially revocable.
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="sessions")
# END_BLOCK: SESSIONS_TABLE
