# ############################################################################
# AI_HEADER: MODULE_TODAY-PREGEN-SERVICE — bounded nightly Today pre-generation.
# ROLE: Selects the active cohort, publishes deterministic tomorrow snapshots,
#       and performs leased, bounded narrative warm-up without impressions.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-PREGEN-SERVICE
# purpose: Run one idempotent nightly Today convergence pre-generation pass for
#   a bounded cohort of active users.
# owns:
#   - apps/api/app/services/today_pregen_service.py
# inputs: Async database session, typed P5 settings, injectable clock/sleep and
#   runtime boundaries for deterministic calculation and narrative generation.
# outputs: PregenRunSummary with typed per-user outcomes and flat counters.
# dependencies: Session/UserProfile activity source, AccessService,
#   user_local_date, Today convergence runtime/document/snapshot services,
#   narrative lease service, narrative generator, and structured logging.
# side_effects: Reads cohort/access rows; calls SolarSage/LLM through existing
#   boundaries; publishes snapshots and narrative lease state; emits lifecycle
#   events. Never creates impressions or legacy payload-cache rows.
# emitted_logs: day.pregen_started, day.pregen_user_finished,
#   day.pregen_completed.
# invariants: settings are validated before cohort selection; locked users are
#   excluded; deterministic data survives every narrative failure; at most
#   three bounded narrative attempts occur per user/run.
# failure_policy: invalid settings raise PregenConfigurationError after a
#   typed completion log; per-user exceptions become type-only failed outcomes;
#   cohort/database boundary failures propagate after the batch log boundary.
# END_MODULE_CONTRACT: M-TODAY-PREGEN-SERVICE

# START_MODULE_MAP: M-TODAY-PREGEN-SERVICE
# public_entrypoints:
#   - PregenConfigurationError
#   - PregenUserOutcome
#   - PregenUserResult
#   - PregenRunSummary
#   - TodayPregenService.run
# semantic_blocks:
#   - COHORT: active-session query, profile validation, local target date, access
#   - DETERMINISTIC: cache identity, convergence calculation, and publication
#   - NARRATIVE: selective leased generation and bounded retry schedule
#   - SUMMARY: typed per-user outcomes and privacy-safe lifecycle logs
# owned_tests:
#   - apps/api/tests/test_today_pregen_service.py
# END_MODULE_MAP: M-TODAY-PREGEN-SERVICE

from __future__ import annotations

import asyncio
import inspect
import re
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Literal

from sqlalchemy import func, select

from app.core.config import Settings, settings
from app.core.log_identity import hash_user_id, new_correlation_id
from app.core.logging import bind_log_context, log_event
from app.db.models import Session, User, UserProfile
from app.services.access_service import AccessService
from app.services.today_birth_time import (
    BirthTimeResolution,
    resolve_profile_birth_time,
)
from app.services.today_convergence_runtime import (
    TodayConvergenceCalculationBuilt,
    calculate_today_convergence,
)
from app.services.today_convergence_snapshot import (
    TodayConvergenceSnapshotDocument,
    build_today_convergence_snapshot_document,
    compute_today_profile_hash,
)
from app.services.today_narrative_lease_service import (
    NarrativeLeaseClaim,
    NarrativeLeaseSkip,
    TodayNarrativeLeaseService,
)
from app.services.today_narrative_service import (
    TodayNarrativeFailure,
    TodayNarrativeSuccess,
    generate_today_narrative,
)
from app.services.today_snapshot_service import TodaySnapshotService
from app.services.user_local_date import resolve_user_local_date


_POSITIVE_SETTINGS = (
    "day_pregen_active_days",
    "day_pregen_llm_active_days",
    "day_pregen_concurrency",
    "day_pregen_max_users",
    "day_pregen_deterministic_deadline_seconds",
    "day_pregen_llm_deadline_seconds",
)
_DEFAULT_RETRY_OFFSETS = (
    timedelta(0),
    timedelta(minutes=5),
    timedelta(minutes=20),
)
_ERROR_CODE_RE = re.compile(r"^[a-z0-9_.-]{1,64}$")


class PregenConfigurationError(ValueError):
    """Raised when the one-shot job cannot safely start with its settings."""

    def __init__(self, setting_name: str):
        self.setting_name = setting_name
        super().__init__(f"invalid_pregen_setting:{setting_name}")


class PregenUserOutcome(StrEnum):
    """Closed public enum for the per-user lifecycle event."""

    SNAPSHOT_HIT = "snapshot_hit"
    PUBLISHED = "published"
    DETERMINISTIC_UNAVAILABLE = "deterministic_unavailable"
    LLM_READY = "llm_ready"
    LLM_UNAVAILABLE = "llm_unavailable"
    LLM_SKIPPED_PREVIEW = "llm_skipped_preview"
    LLM_SKIPPED_STALE = "llm_skipped_stale"
    LLM_SKIPPED_READY = "llm_skipped_ready"
    LLM_SKIPPED_IN_FLIGHT = "llm_skipped_in_flight"
    LLM_SKIPPED_COOLDOWN = "llm_skipped_cooldown"
    LLM_SKIPPED_EXHAUSTED = "llm_skipped_exhausted"
    LLM_SKIPPED_NOT_NEEDED = "llm_skipped_not_needed"
    FAILED = "failed"


@dataclass(frozen=True)
class PregenUserResult:
    """Sanitized result retained for tests and the caller's summary."""

    user_id: object
    deterministic_outcome: Literal["hit", "published", "unavailable", "failed"]
    outcome: PregenUserOutcome
    llm_outcome: PregenUserOutcome | None
    duration_ms: float
    error_type: str | None = None


@dataclass(frozen=True)
class PregenRunSummary:
    """Typed counters for one completed bounded run."""

    outcome: Literal["completed", "cohort_capped"]
    cohort_size: int
    cohort_total: int
    cohort_capped: bool
    deterministic_published: int
    deterministic_hit: int
    deterministic_failed: int
    llm_ready: int
    llm_unavailable: int
    llm_skipped: int
    duration_ms: float
    user_results: tuple[PregenUserResult, ...] = ()

    @property
    def cohort_processed(self) -> int:
        # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.PregenRunSummary.cohort_processed
        # purpose: Preserve the explicit processed-count name for callers while
        #   cohort_size remains the bounded selected cohort size.
        # inputs: self — immutable run summary.
        # returns: Number of users whose bounded tasks were awaited.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: never raises.
        # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.PregenRunSummary.cohort_processed
        return self.cohort_size

    def as_payload(self) -> dict[str, object]:
        """Return the flat, PII-free summary shape used by structured logs."""

        return {
            "outcome": self.outcome,
            "cohort_size": self.cohort_size,
            "cohort_total": self.cohort_total,
            "cohort_processed": self.cohort_size,
            "cohort_capped": self.cohort_capped,
            "deterministic_published": self.deterministic_published,
            "deterministic_hit": self.deterministic_hit,
            "deterministic_failed": self.deterministic_failed,
            "llm_ready": self.llm_ready,
            "llm_unavailable": self.llm_unavailable,
            "llm_skipped": self.llm_skipped,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class _CohortMember:
    user: User
    profile: UserProfile
    last_active_at: datetime
    target_date: date
    access_state: object
    birth_time: BirthTimeResolution
    profile_hash: str


@dataclass(frozen=True)
class _CohortSelection:
    members: tuple[_CohortMember, ...]
    total_eligible: int
    capped: bool


@dataclass(frozen=True)
class _DeterministicResult:
    snapshot: object | None
    outcome: Literal["hit", "published", "unavailable", "failed"]
    error_type: str | None = None


@dataclass(frozen=True)
class _NarrativeResult:
    outcome: PregenUserOutcome
    error_type: str | None = None


# START_BLOCK: COHORT
async def _select_active_users(
    db: object,
    active_days: int,
    now: datetime,
    max_candidates: int | None = None,
) -> list[tuple[User, UserProfile, datetime]]:
    # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.select_active_users
    # purpose: Read the legacy job's session activity source with deterministic
    # newest-first ordering and the complete birth-location boundary.
    # inputs: Async SQLAlchemy session, positive activity window, aware run time,
    #   and optional bounded candidate limit.
    # returns: User/profile/latest issued session triples, newest first.
    # side_effects: One database SELECT; no writes or logs.
    # emitted_logs: none.
    # error_behavior: Database errors propagate to the run boundary.
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.select_active_users
    since = now - timedelta(days=active_days)
    last_active = func.max(Session.issued_at).label("last_active_at")
    statement = (
        select(User, UserProfile, last_active)
        .join(UserProfile, UserProfile.user_id == User.id)
        .join(Session, Session.user_id == User.id)
        .where(Session.issued_at >= since)
        .where(UserProfile.birthday.is_not(None))
        .where(UserProfile.birth_tz.is_not(None))
        .where(UserProfile.birth_lat.is_not(None))
        .where(UserProfile.birth_lon.is_not(None))
        .group_by(User.id, UserProfile.user_id)
        .order_by(last_active.desc(), User.id.asc())
    )
    if max_candidates is not None:
        statement = statement.limit(max_candidates)
    result = await db.execute(statement)
    return [(row[0], row[1], row[2]) for row in result.all()]


def _normalise_now(value: datetime) -> datetime:
    # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.normalise_now
    # purpose: Enforce the aware UTC clock boundary used by target dates and leases.
    # inputs: datetime supplied by a run or test clock.
    # returns: A timezone-aware UTC datetime.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError for a naive or non-datetime value.
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.normalise_now
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("pregen_now_must_be_aware")
    return value.astimezone(timezone.utc)


def _normalise_activity(value: object, fallback: object, now: datetime) -> datetime:
    # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.normalise_activity
    # purpose: Normalize a latest-session timestamp for freshness and ordering.
    # inputs: query timestamp, optional user fallback, and aware run time.
    # returns: A timezone-aware UTC activity timestamp.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises ValueError when no valid timestamp is available.
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.normalise_activity
    selected = value if value is not None else fallback
    if not isinstance(selected, datetime):
        raise ValueError("activity_timestamp")
    if selected.tzinfo is None or selected.utcoffset() is None:
        return selected.replace(tzinfo=timezone.utc)
    return selected.astimezone(timezone.utc)


def _access_state(access_state: object) -> str:

    # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.access_state
    # purpose: Read the stable state value from a ContentAccessState-like object.
    # inputs: AccessService result.
    # returns: Lowercase state string, or an explicit invalid marker.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: never raises for malformed test doubles.
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.access_state
    value = getattr(access_state, "state", access_state)
    return value.lower() if isinstance(value, str) else "invalid"


def _snapshot_has_selected_blocks(snapshot: object) -> bool:
    # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.has_selected_blocks
    # purpose: Tell whether a snapshot carries any LLM-writable selected block.
    # inputs: snapshot — TodaySnapshot-like row with deterministic_result_json.
    # returns: True when convergences, main_event, or impulses are present.
    # side_effects: none. emitted_logs: none.
    # error_behavior: malformed payloads answer False (fail-closed no-LLM).
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.has_selected_blocks
    result = getattr(snapshot, "deterministic_result_json", None)
    if not isinstance(result, dict):
        return False
    selected = result.get("selected")
    if not isinstance(selected, dict):
        return False
    return bool(selected.get("convergences") or selected.get("main_event") or selected.get("impulses"))


def _validate_settings(config: object) -> None:
    # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.validate_settings
    # purpose: Fail closed on every positive P5 setting before cohort selection.
    # inputs: Settings-like object.
    # returns: None when all six settings are strict positive integers.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: raises PregenConfigurationError with only a setting name.
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.validate_settings
    for name in _POSITIVE_SETTINGS:
        value = getattr(config, name, None)
        if type(value) is not int or value <= 0:
            raise PregenConfigurationError(name)


def _safe_error_code(value: object) -> str:
    # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.safe_error_code
    # purpose: Convert a narrative failure into the lease's bounded error-code contract.
    # inputs: Untrusted/provider-derived error-code value.
    # returns: Lowercase safe code accepted by TodayNarrativeLeaseService.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: malformed values become internal_error.
    # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.safe_error_code
    if not isinstance(value, str):
        return "internal_error"
    code = value.strip().lower().replace(" ", "_")
    code = re.sub(r"[^a-z0-9_.-]", "_", code)[:64]
    return code if _ERROR_CODE_RE.fullmatch(code or "") is not None else "internal_error"


# END_BLOCK: COHORT


class TodayPregenService:
    """Orchestrate one bounded, idempotent P5 pre-generation run."""

    def __init__(
        self,
        db: object,
        *,
        settings_obj: Settings | object | None = None,
        session_factory: Callable[[], object] | None = None,
        clock: Callable[[], datetime] | None = None,
        sleep: Callable[[float], Awaitable[object]] | None = None,
        monotonic: Callable[[], float] | None = None,
        active_selector: Callable[[object, int, datetime], Awaitable[list[tuple[User, UserProfile, datetime]]]] | None = None,
        access_service_factory: Callable[[object], object] | None = None,
        local_date_resolver: Callable[[object, datetime], date] | None = None,
        birth_time_resolver: Callable[[object], BirthTimeResolution] | None = None,
        profile_hash_fn: Callable[[object, BirthTimeResolution], str] | None = None,
        calculate_fn: Callable[..., Awaitable[object]] | None = None,
        document_builder: Callable[..., TodayConvergenceSnapshotDocument] | None = None,
        snapshot_service_factory: Callable[[object], object] | None = None,
        lease_service_factory: Callable[..., object] | None = None,
        generate_fn: Callable[..., Awaitable[object]] | None = None,
        llm: object | None = None,
        retry_delays: Sequence[timedelta | float] | None = None,
        run_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self.db = db
        self.settings = settings if settings_obj is None else settings_obj
        self.session_factory = session_factory
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.sleep = sleep or asyncio.sleep
        self.monotonic = monotonic or time.monotonic
        self.active_selector = active_selector or _select_active_users
        self.access_service_factory = access_service_factory or AccessService
        self.local_date_resolver = local_date_resolver or resolve_user_local_date
        self.birth_time_resolver = birth_time_resolver or resolve_profile_birth_time
        self.profile_hash_fn = profile_hash_fn or compute_today_profile_hash
        self.calculate_fn = calculate_fn or calculate_today_convergence
        self.document_builder = document_builder or build_today_convergence_snapshot_document
        self.snapshot_service_factory = snapshot_service_factory or TodaySnapshotService
        self.lease_service_factory = lease_service_factory or TodayNarrativeLeaseService
        self.generate_fn = generate_fn or generate_today_narrative
        self.llm = llm
        self.retry_delays = self._normalise_retry_delays(retry_delays)
        self.run_id_factory = run_id_factory or new_correlation_id
        self._run_id = ""

    @staticmethod
    def _normalise_retry_delays(
        values: Sequence[timedelta | float] | None,
    ) -> tuple[timedelta, timedelta, timedelta]:
        selected = _DEFAULT_RETRY_OFFSETS if values is None else tuple(values)
        if len(selected) != 3:
            raise ValueError("retry_delays must contain exactly three offsets")
        converted: list[timedelta] = []
        for value in selected:
            delay = value if isinstance(value, timedelta) else timedelta(seconds=float(value))
            if delay.total_seconds() < 0:
                raise ValueError("retry_delays must be non-negative")
            converted.append(delay)
        if converted[0] != timedelta(0) or converted[1] < converted[0] or converted[2] < converted[1]:
            raise ValueError("retry_delays must be [0, +5m, +20m]")
        return converted[0], converted[1], converted[2]

    def _safe_bind(self, **kwargs: str) -> None:
        try:
            bind_log_context(**kwargs)
        except Exception:
            pass

    def _safe_log(
        self,
        event: str,
        *,
        payload: dict[str, object] | None = None,
        level: str = "info",
        error: dict[str, object] | None = None,
        duration_ms: float | None = None,
    ) -> None:
        try:
            log_event(
                event,
                level=level,
                msg="today nightly pregen",
                payload=payload,
                error=error,
                duration_ms=duration_ms,
            )
        except Exception:
            pass

    def _run_now(self, value: datetime | None) -> datetime:
        selected = self.clock() if value is None else value
        return _normalise_now(selected)

    # START_BLOCK: COHORT
    async def _select_cohort(self, now: datetime) -> _CohortSelection:
        # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._select_cohort
        # purpose: Build the valid, access-eligible, newest-first bounded cohort.
        # inputs: aware UTC run time and validated service settings.
        # returns: selected members, total eligible count, and cap marker.
        # side_effects: activity/profile/access reads; no writes.
        # emitted_logs: none.
        # error_behavior: malformed individual candidates are excluded; activity
        #   query failures propagate.
        # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._select_cohort
        try:
            selector_params = inspect.signature(self.active_selector).parameters
        except (TypeError, ValueError):
            selector_params = {}
        accepts_keyword_limit = "max_candidates" in selector_params or any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in selector_params.values()
        )
        accepts_positional_limit = len(selector_params) >= 4
        if accepts_keyword_limit:
            rows = await self.active_selector(
                self.db,
                self.settings.day_pregen_active_days,
                now,
                max_candidates=self.settings.day_pregen_max_users + 1,
            )
        elif accepts_positional_limit:
            rows = await self.active_selector(
                self.db,
                self.settings.day_pregen_active_days,
                now,
                self.settings.day_pregen_max_users + 1,
            )
        else:
            rows = await self.active_selector(
                self.db,
                self.settings.day_pregen_active_days,
                now,
            )
        access_service = self.access_service_factory(self.db)
        members: list[_CohortMember] = []
        for row in rows:
            if len(row) == 2:  # compatibility for the old selector test shape
                user, profile = row  # type: ignore[misc]
                raw_activity = getattr(user, "updated_at", None)
            else:
                user, profile, raw_activity = row
            try:
                if (
                    profile is None
                    or getattr(profile, "birthday", None) is None
                    or getattr(profile, "birth_lat", None) is None
                    or getattr(profile, "birth_lon", None) is None
                    or not isinstance(getattr(profile, "birth_tz", None), str)
                    or not profile.birth_tz.strip()
                ):
                    continue
                last_active = _normalise_activity(raw_activity, getattr(user, "updated_at", None), now)
                birth_time = self.birth_time_resolver(profile)
                try:
                    # The query returns the profile alongside the user. Attach
                    # that already-loaded relation so the canonical resolver
                    # receives the same user-shaped object as the live route.
                    user.profile = profile
                    local_date_owner = user
                except Exception:
                    local_date_owner = type("_LocalDateOwner", (), {"profile": profile})()
                target_date = self.local_date_resolver(local_date_owner, now + timedelta(hours=24))
                access_state = await access_service.can_access_day(user.id, target_date)
                if _access_state(access_state) == "locked":
                    continue
                profile_hash = self.profile_hash_fn(profile, birth_time)
            except Exception:
                # Incomplete or malformed profile/access state is not a batch
                # failure and must never enter the processing cohort.
                continue
            members.append(
                _CohortMember(
                    user=user,
                    profile=profile,
                    last_active_at=last_active,
                    target_date=target_date,
                    access_state=access_state,
                    birth_time=birth_time,
                    profile_hash=profile_hash,
                )
            )

        members.sort(key=lambda item: (-item.last_active_at.timestamp(), str(item.user.id)))
        total = len(members)
        candidate_limit_reached = len(rows) == self.settings.day_pregen_max_users + 1
        capped = total > self.settings.day_pregen_max_users or candidate_limit_reached
        return _CohortSelection(
            members=tuple(members[: self.settings.day_pregen_max_users]),
            total_eligible=total,
            capped=capped,
        )
    # END_BLOCK: COHORT

    @asynccontextmanager
    async def _user_session(self) -> AsyncIterator[object]:
        # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._user_session
        # purpose: Give concurrent users independent DB sessions when production
        # supplies a factory, while keeping injected unit doubles lightweight.
        # inputs: service session_factory or root db.
        # returns: async context containing one user DB boundary.
        # side_effects: opens/closes a session when a factory is configured.
        # emitted_logs: none.
        # error_behavior: session factory errors propagate to that user result.
        # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._user_session
        if self.session_factory is None:
            yield self.db
            return
        async with self.session_factory() as user_db:
            yield user_db

    # START_BLOCK: DETERMINISTIC
    async def _deterministic_stage(
        self,
        member: _CohortMember,
        db: object,
    ) -> _DeterministicResult:
        # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._deterministic_stage
        # purpose: Reuse a matching snapshot or calculate and publish one
        # deterministic target-day document.
        # inputs: validated cohort member and user-scoped DB session.
        # returns: hit, published, or typed unavailable deterministic result.
        # side_effects: optional sidecar call and snapshot publication; no impression.
        # emitted_logs: delegated snapshot boundary events.
        # error_behavior: unavailable runtime becomes typed unavailable; unexpected
        # errors are handled by the per-user boundary.
        # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._deterministic_stage
        snapshot_service = self.snapshot_service_factory(db)
        current = await snapshot_service.load_current(member.user.id, member.target_date)
        if current is not None and current.profile_hash == member.profile_hash:
            return _DeterministicResult(snapshot=current, outcome="hit")

        calculation = await self.calculate_fn(member.profile, member.target_date)
        if not isinstance(calculation, TodayConvergenceCalculationBuilt):
            return _DeterministicResult(
                snapshot=None,
                outcome="unavailable",
                error_type=type(calculation).__name__,
            )
        document = self.document_builder(member.profile, calculation)
        if current is None:
            publication = await snapshot_service.publish_or_load(member.user.id, document)
        else:
            publication = await snapshot_service.publish_superseding(
                member.user.id,
                document,
                current.id,
            )
        publication_outcome = getattr(publication, "outcome", "published")
        stage_outcome: Literal["hit", "published"] = (
            "hit" if publication_outcome == "conflict_reused" else "published"
        )
        return _DeterministicResult(
            snapshot=publication.snapshot,
            outcome=stage_outcome,
        )
    # END_BLOCK: DETERMINISTIC

    # START_BLOCK: NARRATIVE
    async def _narrative_stage(
        self,
        member: _CohortMember,
        snapshot: object,
        now: datetime,
        db: object,
    ) -> _NarrativeResult:
        # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._narrative_stage
        # purpose: Selectively warm a full-access fresh user's narrative via the
        # persistent lease and three scheduled attempts at most.
        # inputs: cohort member, published snapshot, run clock, user DB session.
        # returns: ready, unavailable, or typed skip outcome.
        # side_effects: bounded provider calls and lease transitions; no snapshot
        #   deletion or impression write.
        # emitted_logs: delegated narrative lease/generation events.
        # error_behavior: provider failures are persisted as unavailable; lease or
        #   persistence failures propagate to the per-user exception boundary.
        # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._narrative_stage
        access = _access_state(member.access_state)
        if access != "full":
            skip = (
                PregenUserOutcome.LLM_SKIPPED_PREVIEW
                if access == "preview"
                else PregenUserOutcome(f"llm_skipped_{access}")
                if f"llm_skipped_{access}" in {item.value for item in PregenUserOutcome}
                else PregenUserOutcome.LLM_SKIPPED_PREVIEW
            )
            return _NarrativeResult(skip)

        if not _snapshot_has_selected_blocks(snapshot):
            # Quiet day with no selected blocks: contentState=not_needed —
            # no lease, no provider call (deterministic data already published).
            return _NarrativeResult(PregenUserOutcome.LLM_SKIPPED_NOT_NEEDED)

        cutoff = now - timedelta(days=self.settings.day_pregen_llm_active_days)
        if member.last_active_at < cutoff:
            return _NarrativeResult(PregenUserOutcome.LLM_SKIPPED_STALE)

        prompt_version = getattr(
            self.settings,
            "today_narrative_prompt_version",
            "today-narrative-v1",
        )
        attempt_clock = {"now": now}
        try:
            lease_params = inspect.signature(self.lease_service_factory).parameters
        except (TypeError, ValueError):
            lease_params = {}
        accepts_clock = "clock" in lease_params or any(
            parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in lease_params.values()
        ) or len(lease_params) >= 2
        if accepts_clock:
            lease_service = self.lease_service_factory(
                db,
                clock=lambda: attempt_clock["now"],
            )
        else:
            lease_service = self.lease_service_factory(db)
        lease_duration = timedelta(
            seconds=max(
                60,
                min(
                    3600,
                    self.settings.day_pregen_llm_deadline_seconds + 30,
                ),
            )
        )

        for attempt_index, offset in enumerate(self.retry_delays):
            attempt_now = now + offset
            attempt_clock["now"] = attempt_now
            acquired = await lease_service.acquire(
                snapshot.id,
                prompt_version,
                attempt_now,
                lease_duration,
            )
            if isinstance(acquired, NarrativeLeaseSkip) or not isinstance(acquired, NarrativeLeaseClaim):
                reason = getattr(acquired, "reason", "in_flight")
                mapping = {
                    "ready": PregenUserOutcome.LLM_SKIPPED_READY,
                    "in_flight": PregenUserOutcome.LLM_SKIPPED_IN_FLIGHT,
                    "cooldown": PregenUserOutcome.LLM_SKIPPED_COOLDOWN,
                    "exhausted": PregenUserOutcome.LLM_SKIPPED_EXHAUSTED,
                }
                return _NarrativeResult(mapping.get(reason, PregenUserOutcome.LLM_SKIPPED_IN_FLIGHT))

            try:
                generation = await self._generate_with_deadline(snapshot, prompt_version)
            except asyncio.TimeoutError:
                generation = TodayNarrativeFailure(error_code="timeout", latency_ms=0)
                last_error_type = "TimeoutError"
            except TimeoutError:
                generation = TodayNarrativeFailure(error_code="timeout", latency_ms=0)
                last_error_type = "TimeoutError"
            except Exception as exc:
                generation = TodayNarrativeFailure(
                    error_code="internal_error",
                    latency_ms=0,
                )
                last_error_type = type(exc).__name__
            else:
                last_error_type = None

            if isinstance(generation, TodayNarrativeSuccess):
                completion = await lease_service.complete_ready(
                    acquired,
                    generation.content_json,
                )
                if getattr(completion, "outcome", "completed") == "completed":
                    return _NarrativeResult(PregenUserOutcome.LLM_READY)
                return _NarrativeResult(PregenUserOutcome.LLM_SKIPPED_IN_FLIGHT)

            error_code = _safe_error_code(getattr(generation, "error_code", "internal_error"))
            if attempt_index < len(self.retry_delays) - 1:
                retry_at = now + self.retry_delays[attempt_index + 1]
                if retry_at <= attempt_now:
                    retry_at = attempt_now + timedelta(seconds=1)
                await lease_service.complete_unavailable(acquired, error_code, retry_at)
                await self.sleep(max(0.0, (retry_at - attempt_now).total_seconds()))
                continue

            retry_at = attempt_now + max(self.retry_delays[-1], timedelta(seconds=1))
            await lease_service.complete_unavailable(acquired, error_code, retry_at)
            return _NarrativeResult(
                PregenUserOutcome.LLM_UNAVAILABLE,
                error_type=last_error_type,
            )

        # The retry schedule is validated to contain three entries, so this is
        # unreachable; retaining a typed fallback keeps the batch fail-closed.
        return _NarrativeResult(PregenUserOutcome.LLM_UNAVAILABLE)

    async def _generate_with_deadline(self, snapshot: object, prompt_version: str) -> object:
        # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._generate_with_deadline
        # purpose: Bound one narrative provider call by the P5 per-user deadline.
        # inputs: published snapshot and prompt version.
        # returns: TodayNarrativeSuccess or TodayNarrativeFailure.
        # side_effects: at most one delegated provider call.
        # emitted_logs: delegated narrative generation events.
        # error_behavior: asyncio.TimeoutError propagates to the attempt boundary.
        # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._generate_with_deadline
        kwargs: dict[str, object] = {
            "prompt_version": prompt_version,
            "correlation_id": self._run_id,
            "timeout_seconds": self.settings.day_pregen_llm_deadline_seconds,
        }
        if self.llm is not None:
            kwargs["llm"] = self.llm
        return await asyncio.wait_for(
            self.generate_fn(snapshot, **kwargs),
            timeout=self.settings.day_pregen_llm_deadline_seconds,
        )
    # END_BLOCK: NARRATIVE

    async def _process_user(
        self,
        member: _CohortMember,
        now: datetime,
        semaphore: asyncio.Semaphore,
    ) -> PregenUserResult:
        # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._process_user
        # purpose: Run one user's deterministic and selective narrative stages.
        # inputs: cohort member, fixed run time, and bounded concurrency semaphore.
        # returns: one sanitized typed result; never aborts sibling users.
        # side_effects: per-user session, snapshot/lease/provider operations, log.
        # emitted_logs: day.pregen_user_finished.
        # error_behavior: unexpected exception becomes failed with type-only error.
        # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE._process_user
        async with semaphore:
            started = self.monotonic()
            try:
                try:
                    self._safe_bind(user_id_hash=hash_user_id(member.user.id))
                except Exception:
                    # A telemetry identity failure must not abort a user job.
                    pass
                async with self._user_session() as db:
                    try:
                        deterministic = await asyncio.wait_for(
                            self._deterministic_stage(member, db),
                            timeout=self.settings.day_pregen_deterministic_deadline_seconds,
                        )
                    except asyncio.TimeoutError:
                        deterministic = _DeterministicResult(
                            snapshot=None,
                            outcome="unavailable",
                            error_type="TimeoutError",
                        )
                    except TimeoutError:
                        deterministic = _DeterministicResult(
                            snapshot=None,
                            outcome="unavailable",
                            error_type="TimeoutError",
                        )

                    if deterministic.outcome == "unavailable":
                        result = PregenUserResult(
                            user_id=member.user.id,
                            deterministic_outcome="unavailable",
                            outcome=PregenUserOutcome.DETERMINISTIC_UNAVAILABLE,
                            llm_outcome=None,
                            duration_ms=max(0.0, (self.monotonic() - started) * 1000),
                            error_type=deterministic.error_type,
                        )
                    else:
                        narrative = await self._narrative_stage(
                            member,
                            deterministic.snapshot,
                            now,
                            db,
                        )
                        result = PregenUserResult(
                            user_id=member.user.id,
                            deterministic_outcome=deterministic.outcome,
                            outcome=narrative.outcome,
                            llm_outcome=narrative.outcome,
                            duration_ms=max(0.0, (self.monotonic() - started) * 1000),
                            error_type=narrative.error_type,
                        )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                result = PregenUserResult(
                    user_id=member.user.id,
                    deterministic_outcome="failed",
                    outcome=PregenUserOutcome.FAILED,
                    llm_outcome=None,
                    duration_ms=max(0.0, (self.monotonic() - started) * 1000),
                    error_type=type(exc).__name__,
                )

            payload: dict[str, object] = {
                "outcome": result.outcome.value,
                "deterministic_outcome": result.deterministic_outcome,
                "duration_ms": result.duration_ms,
            }
            if result.llm_outcome is not None:
                payload["llm_outcome"] = result.llm_outcome.value
            if result.error_type is not None:
                payload["error_type"] = result.error_type
            self._safe_log(
                "day.pregen_user_finished",
                payload=payload,
                level="error" if result.outcome == PregenUserOutcome.FAILED else "info",
                error={"type": result.error_type} if result.outcome == PregenUserOutcome.FAILED else None,
                duration_ms=result.duration_ms,
            )
            return result

    # START_BLOCK: SUMMARY
    async def run(self, *, now: datetime | None = None) -> PregenRunSummary:
        # START_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.run
        # purpose: Execute one validated bounded nightly pre-generation pass.
        # inputs: optional aware run clock for production or deterministic tests.
        # returns: typed summary after all bounded user tasks finish.
        # side_effects: cohort reads, snapshot/narrative writes, provider calls,
        #   and three lifecycle event types.
        # emitted_logs: day.pregen_started, day.pregen_user_finished,
        #   day.pregen_completed.
        # error_behavior: invalid settings raise after typed completion log;
        #   per-user failures are swallowed; outer DB/cohort failures propagate.
        # END_FUNCTION_CONTRACT: F-M-TODAY-PREGEN-SERVICE.run
        started = self.monotonic()
        run_now = self._run_now(now)
        self._run_id = self.run_id_factory()
        self._safe_bind(
            correlation_id=self._run_id,
            slice="W-TODAY-CONVERGENCE-P5",
            module="M-TODAY-PREGEN-SERVICE",
            block="SUMMARY",
        )

        try:
            _validate_settings(self.settings)
        except PregenConfigurationError as exc:
            duration_ms = max(0.0, (self.monotonic() - started) * 1000)
            self._safe_log(
                "day.pregen_completed",
                level="error",
                payload={
                    "outcome": "invalid_settings",
                    "invalid_setting": exc.setting_name,
                    "cohort_size": 0,
                    "cohort_total": 0,
                    "cohort_processed": 0,
                    "duration_ms": duration_ms,
                },
                error={"type": type(exc).__name__},
                duration_ms=duration_ms,
            )
            raise

        selection = await self._select_cohort(run_now)
        self._safe_log(
            "day.pregen_started",
            payload={
                "cohort_size": len(selection.members),
                "cohort_total": selection.total_eligible,
                "cohort_processed": len(selection.members),
                "cohort_capped": selection.capped,
                "active_days": self.settings.day_pregen_active_days,
                "llm_active_days": self.settings.day_pregen_llm_active_days,
                "concurrency": self.settings.day_pregen_concurrency,
                "max_users": self.settings.day_pregen_max_users,
                "deterministic_deadline_seconds": self.settings.day_pregen_deterministic_deadline_seconds,
                "llm_deadline_seconds": self.settings.day_pregen_llm_deadline_seconds,
            },
        )

        semaphore = asyncio.Semaphore(self.settings.day_pregen_concurrency)
        results = await asyncio.gather(
            *(
                self._process_user(member, run_now, semaphore)
                for member in selection.members
            )
        )
        duration_ms = max(0.0, (self.monotonic() - started) * 1000)
        summary = PregenRunSummary(
            outcome="cohort_capped" if selection.capped else "completed",
            cohort_size=len(selection.members),
            cohort_total=selection.total_eligible,
            cohort_capped=selection.capped,
            deterministic_published=sum(item.deterministic_outcome == "published" for item in results),
            deterministic_hit=sum(item.deterministic_outcome == "hit" for item in results),
            deterministic_failed=sum(
                item.deterministic_outcome in {"unavailable", "failed"}
                for item in results
            ),
            llm_ready=sum(item.outcome == PregenUserOutcome.LLM_READY for item in results),
            llm_unavailable=sum(item.outcome == PregenUserOutcome.LLM_UNAVAILABLE for item in results),
            llm_skipped=sum(
                item.outcome.value.startswith("llm_skipped_")
                for item in results
            ),
            duration_ms=duration_ms,
            user_results=tuple(results),
        )
        self._safe_log(
            "day.pregen_completed",
            payload=summary.as_payload(),
            duration_ms=duration_ms,
        )
        return summary
    # END_BLOCK: SUMMARY


__all__ = [
    "PregenConfigurationError",
    "PregenRunSummary",
    "PregenUserOutcome",
    "PregenUserResult",
    "TodayPregenService",
]
