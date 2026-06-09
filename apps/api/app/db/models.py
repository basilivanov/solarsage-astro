# ############################################################################
# AI_HEADER: MODULE_DB_MODELS
# ROLE: ORM models for users, user_profiles, sessions (W-1.2 / Option A),
#       access_ledger, referrals (W-ACCESS.1), today_payloads_cache (W-5.2),
#       semantic_layers (W-4.3), microcopy_misses (W-9.2).
# DEPENDENCIES: sqlalchemy, app.db.session.Base
# GRACE_ANCHORS: [USERS_TABLE, USER_PROFILES_TABLE, SESSIONS_TABLE, ACCESS_LEDGER_TABLE, REFERRALS_TABLE, TODAY_PAYLOADS_CACHE_TABLE, SEMANTIC_LAYERS_TABLE, MICROCOPY_MISSES_TABLE]
# ############################################################################

# START_MODULE_CONTRACT: M-AUTH-TG.models
# purpose: Declarative ORM models for `users`, `user_profiles`, `sessions`,
#   `access_ledger`, `referrals`, `today_payloads_cache`, and `microcopy_misses`.
#   Owned jointly by M-AUTH-TG (users + sessions), M-PROFILE (user_profiles),
#   M-ACCESS (access_ledger, referrals), M-DAY-SERVICE (today_payloads_cache),
#   and M-MICROCOPY-SERVICE (microcopy_misses, W-9.2).
# owns:
#   - apps/api/app/db/models.py
# inputs:
#   - app.db.session.Base (DeclarativeBase singleton)
# outputs:
#   - User: row in `users` keyed by UUID, unique tg_user_id
#   - UserProfile: row in `user_profiles` (1:1 with User), birth data
#   - Session: row in `sessions`, opaque-token-hash → user_id mapping
#   - AccessLedger: row in `access_ledger`, tracks referral_bonus and subscription entries
#   - Referral: row in `referrals`, tracks referrer → invitee relationships
#   - TodayPayloadCache: row in `today_payloads_cache`, cached TodayPayload JSON (W-5.2)
#   - MicrocopyMiss: row in `microcopy_misses`, tracks missing microcopy keys (W-9.2)
# dependencies:
#   - M-DB-SESSION (Base)
#   - alembic 0001_users migration creates users/profiles/sessions tables
#   - alembic W-ACCESS.1 migration creates access_ledger/referrals tables
#   - alembic W-5.2 migration creates today_payloads_cache table
#   - alembic W-9.2 migration creates microcopy_misses table
# side_effects:
#   - importing this module registers tables on Base.metadata
# invariants:
#   - User.id is the natural PK (UUID); tg_user_id is a UNIQUE BIGINT
#   - UserProfile.user_id is both PK and FK -> users.id (1:1)
#   - Session.token_hash is CHAR(64) UNIQUE (sha256-hex of the opaque token)
#   - AccessLedger.entry_type in ("referral_bonus", "subscription")
#   - TodayPayloadCache: unique (user_id, target_date) constraint (W-5.2)
#   - MicrocopyMiss: key is indexed for fast lookup (W-9.2)
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
#   - AccessLedger
#   - Referral
#   - TodayPayloadCache
#   - MicrocopyMiss
# semantic_blocks:
#   - USERS_TABLE: declarative class User -> "users"
#   - USER_PROFILES_TABLE: declarative class UserProfile -> "user_profiles"
#   - SESSIONS_TABLE: declarative class Session -> "sessions"
#   - ACCESS_LEDGER_TABLE: declarative class AccessLedger -> "access_ledger"
#   - REFERRALS_TABLE: declarative class Referral -> "referrals"
#   - TODAY_PAYLOADS_CACHE_TABLE: declarative class TodayPayloadCache -> "today_payloads_cache" (W-5.2)
#   - MICROCOPY_MISSES_TABLE: declarative class MicrocopyMiss -> "microcopy_misses" (W-9.2)
# owned_tests:
#   - apps/api/tests/test_auth_endpoints.py
#   - apps/api/tests/test_profile_endpoints.py
#   - apps/api/tests/test_alembic_roundtrip.py
#   - apps/api/tests/test_access_service.py
#   - apps/api/tests/test_cache.py (W-5.2)
#   - apps/api/tests/test_microcopy_misses.py (W-9.2)
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
    Text,
    Time,
    UniqueConstraint,
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
    access_entries: Mapped[list["AccessLedger"]] = relationship(
        "AccessLedger",
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
        CheckConstraint(
            "current_lat IS NULL OR (current_lat >= -90 AND current_lat <= 90)",
            name="ck_user_profiles_current_lat_range",
        ),
        CheckConstraint(
            "current_lon IS NULL OR (current_lon >= -180 AND current_lon <= 180)",
            name="ck_user_profiles_current_lon_range",
        ),
        CheckConstraint(
            "birthday_lat IS NULL OR (birthday_lat >= -90 AND birthday_lat <= 90)",
            name="ck_user_profiles_birthday_lat_range",
        ),
        CheckConstraint(
            "birthday_lon IS NULL OR (birthday_lon >= -180 AND birthday_lon <= 180)",
            name="ck_user_profiles_birthday_lon_range",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    birth_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    birth_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    birth_lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    birth_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 5), nullable=True)
    birth_tz: Mapped[str | None] = mapped_column(String(64), nullable=True)

    current_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    current_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 5), nullable=True)
    current_tz: Mapped[str | None] = mapped_column(String(64), nullable=True)

    birthday_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    birthday_lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    birthday_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 5), nullable=True)
    birthday_tz: Mapped[str | None] = mapped_column(String(64), nullable=True)

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


# START_BLOCK: ACCESS_LEDGER_TABLE
class AccessLedger(Base):
    """Access ledger entries (referral_bonus, subscription). W-ACCESS.1."""

    __tablename__ = "access_ledger"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "referral_bonus", "subscription"
    days_granted: Mapped[int] = mapped_column(nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="access_entries")
# END_BLOCK: ACCESS_LEDGER_TABLE


# START_BLOCK: REFERRALS_TABLE
class Referral(Base):
    """Referral tracking. W-ACCESS.1."""

    __tablename__ = "referrals"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    referrer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invitee_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    referrer: Mapped["User"] = relationship(
        "User", foreign_keys=[referrer_id]
    )
    invitee: Mapped["User"] = relationship(
        "User", foreign_keys=[invitee_id]
    )
# END_BLOCK: REFERRALS_TABLE


# START_BLOCK: TODAY_PAYLOADS_CACHE_TABLE
class TodayPayloadCache(Base):
    """Cached TodayPayload entries. W-5.2."""

    __tablename__ = "today_payloads_cache"
    __table_args__ = (
        UniqueConstraint('user_id', 'target_date', name='uq_user_date'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
# END_BLOCK: TODAY_PAYLOADS_CACHE_TABLE


# START_BLOCK: SEMANTIC_LAYERS_TABLE
class SemanticLayerCache(Base):
    """Cached semantic layers. W-4.3."""

    __tablename__ = "semantic_layers"
    __table_args__ = (
        UniqueConstraint('user_id', 'target_date', name='uq_semantic_user_date'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    semantic_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
# END_BLOCK: SEMANTIC_LAYERS_TABLE


# START_BLOCK: MICROCOPY_MISSES_TABLE
class MicrocopyMiss(Base):
    """Missed microcopy keys. W-9.2."""

    __tablename__ = "microcopy_misses"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    hit_count: Mapped[int] = mapped_column(default=1, nullable=False)
# END_BLOCK: MICROCOPY_MISSES_TABLE


# START_BLOCK: PAYMENTS_TABLE
class Payment(Base):
    """Payment transactions. W-6.1."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[int] = mapped_column(nullable=False)  # In cents
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # "pending", "succeeded", "failed"
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="telegram")
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship("User")
# END_BLOCK: PAYMENTS_TABLE


# START_BLOCK: EVENING_CHECKINS_TABLE
class EveningCheckin(Base):
    """Evening checkin entries. W-8.1."""

    __tablename__ = "evening_checkins"
    __table_args__ = (
        UniqueConstraint('user_id', 'target_date', name='uq_checkin_user_date'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mood: Mapped[str] = mapped_column(String(50), nullable=False)  # "great", "good", "neutral", "bad"
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
# END_BLOCK: EVENING_CHECKINS_TABLE


# START_BLOCK: CHAT_THREADS_TABLE
class ChatThread(Base):
    """Chat thread. W-CHAT-1."""

    __tablename__ = "chat_threads"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="thread", cascade="all, delete-orphan"
    )
# END_BLOCK: CHAT_THREADS_TABLE


# START_BLOCK: CHAT_MESSAGES_TABLE
class ChatMessage(Base):
    """Chat message. W-CHAT-1."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user", "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    thread: Mapped["ChatThread"] = relationship("ChatThread", back_populates="messages")
# END_BLOCK: CHAT_MESSAGES_TABLE


# START_BLOCK: CHAT_QUOTAS_TABLE
class ChatQuota(Base):
    """Chat quota tracking. W-CHAT-4."""

    __tablename__ = "chat_quotas"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    messages_used: Mapped[int] = mapped_column(default=0, nullable=False)
    messages_limit: Mapped[int] = mapped_column(default=10, nullable=False)  # Free tier: 10 messages
    reset_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
# END_BLOCK: CHAT_QUOTAS_TABLE


# START_BLOCK: HORARY_TABLES
class HoraryQuestion(Base):
    __tablename__ = "horary_questions"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_horary_questions_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    client_timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    client_local_time: Mapped[str | None] = mapped_column(String(100), nullable=True)
    question_lat: Mapped[Decimal | None] = mapped_column(Numeric(8, 5), nullable=True)
    question_lon: Mapped[Decimal | None] = mapped_column(Numeric(9, 5), nullable=True)
    question_location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    spent_credit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("horary_credits.id", ondelete="SET NULL"),
        nullable=True,
    )
    refund_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="none"
    )  # none|refunded|not_refundable
    failure_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    public_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    public_error_message: Mapped[str | None] = mapped_column(String(200), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
    spent_credit: Mapped["HoraryCredit | None"] = relationship("HoraryCredit")
    answer: Mapped["HoraryAnswer | None"] = relationship(
        "HoraryAnswer",
        back_populates="question",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class HoraryAnswer(Base):
    __tablename__ = "horary_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("horary_questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    verdict: Mapped[str] = mapped_column(String(10), nullable=False)  # yes/no/maybe
    confidence: Mapped[float] = mapped_column(nullable=False)
    confidence_label: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium"
    )  # low/medium/high
    confidence_explanation: Mapped[str] = mapped_column(
        String(500), nullable=False, default=""
    )
    blocks_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list[HoraryBlock]
    planets_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON list[str]
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    question: Mapped["HoraryQuestion"] = relationship("HoraryQuestion", back_populates="answer")


class HoraryCredit(Base):
    __tablename__ = "horary_credits"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_horary_credits_amount_positive"),
        CheckConstraint("used_amount >= 0", name="ck_horary_credits_used_amount_nonnegative"),
        CheckConstraint("used_amount <= amount", name="ck_horary_credits_used_amount_le_amount"),
        CheckConstraint(
            "source IN ('subscription_weekly_free', 'referral_bonus', 'gift', 'paid', 'adjustment')",
            name="ck_horary_credits_source_values",
        ),
        UniqueConstraint("user_id", "source", "access_week_start", "access_week_end", name="uq_horary_credits_weekly_free"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[int] = mapped_column(nullable=False, default=1)
    used_amount: Mapped[int] = mapped_column(nullable=False, default=0)
    access_week_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_week_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")


class HoraryCreditSpend(Base):
    __tablename__ = "horary_credit_spends"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_horary_credit_spends_idempotency"),
        UniqueConstraint("question_id", name="uq_horary_credit_spends_question"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("horary_credits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("horary_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(nullable=False, default=1)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")
    credit: Mapped["HoraryCredit"] = relationship("HoraryCredit")
    question: Mapped["HoraryQuestion"] = relationship("HoraryQuestion")
# END_BLOCK: HORARY_TABLES
