# ############################################################################
# AI_HEADER: TEST_TODAY-PREGEN-SERVICE — nightly pre-generation contract tests.
# ROLE: Exercises cohort filtering, deterministic publication, leased narrative
#       warm-up, retry bounds, idempotency, summary counters, and privacy logs.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-PREGEN-SERVICE
# purpose: Prove the P5 service behavior with fake sidecar/LLM, snapshot, lease,
#   access, and clock boundaries.
# owns:
#   - apps/api/tests/test_today_pregen_service.py
# inputs: settings-like values, fake cohort rows, and injected async boundaries.
# outputs: assertions over typed outcomes, calls, logs, and snapshot invariants.
# dependencies: app.services.today_pregen_service, app.core.config.Settings, pytest.
# side_effects: none outside in-memory fakes.
# emitted_logs: captured day.pregen_started, day.pregen_user_finished,
#   day.pregen_completed.
# invariants: no impression boundary is called; no legacy feature flags enter the
#   service; a narrative failure never removes a deterministic snapshot.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TEST-TODAY-PREGEN-SERVICE

# START_MODULE_MAP: M-TEST-TODAY-PREGEN-SERVICE
# public_entrypoints: []
# semantic_blocks:
#   - COHORT: profile/activity/access filtering and cap
#   - DETERMINISTIC: cache hit, publish, and unavailable boundaries
#   - NARRATIVE: selective lease/generation/retry behavior
#   - SUMMARY: typed counters and lifecycle log payloads
# owned_tests: self
# END_MODULE_MAP: M-TEST-TODAY-PREGEN-SERVICE

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services import today_pregen_service as pregen
from app.services.today_narrative_lease_service import (
    NarrativeLeaseClaim,
    NarrativeLeaseCompletion,
    NarrativeLeaseSkip,
)
from app.services.today_narrative_service import TodayNarrativeFailure, TodayNarrativeSuccess


NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
FULL = "full"
PREVIEW = "preview"


def _settings(**overrides):
    values = {
        "day_pregen_active_days": 14,
        "day_pregen_llm_active_days": 7,
        "day_pregen_concurrency": 3,
        "day_pregen_max_users": 500,
        "day_pregen_deterministic_deadline_seconds": 10,
        "day_pregen_llm_deadline_seconds": 45,
        "today_narrative_prompt_version": "today-narrative-v1",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _user(number: int, *, active_days_ago: int = 1):
    user_id = UUID(f"00000000-0000-4000-8000-{number:012d}")
    user = SimpleNamespace(
        id=user_id,
        updated_at=NOW - timedelta(days=active_days_ago),
    )
    profile = SimpleNamespace(
        birthday=date(1990, 1, 1),
        birth_time=None,
        birth_time_mode="unknown",
        birth_time_bucket=None,
        birth_lat=55.75,
        birth_lon=37.62,
        birth_tz="Europe/Moscow",
        current_tz="Europe/Moscow",
        current_lat=None,
        current_lon=None,
        invalid=False,
        profile_hash=f"profile-{number}",
    )
    return user, profile


class FakeBuilt:
    pass


class SnapshotStore:
    def __init__(self):
        self.snapshots: dict[tuple[object, date], object] = {}
        self.narratives: dict[object, str] = {}
        self.publications = 0
        self.supersessions = 0
        self.impression_calls = 0
        self.lease_acquires = 0
        self.lease_completions: list[tuple[str, object]] = []


class FakeSnapshotService:
    def __init__(self, store: SnapshotStore):
        self.store = store

    async def load_current(self, user_id, target_date):
        return self.store.snapshots.get((user_id, target_date))

    async def publish_or_load(self, user_id, document):
        key = (user_id, document.target_date)
        existing = self.store.snapshots.get(key)
        if existing is not None:
            return SimpleNamespace(snapshot=existing, outcome="conflict_reused")
        snapshot = SimpleNamespace(
            id=uuid4(),
            target_date=document.target_date,
            profile_hash=document.profile_hash,
            first_day_seen_at=None,
            first_lookahead_seen_at=None,
            deterministic_result_json={"selected": {"convergences": [{"group_id": "cvg-test"}], "main_event": None, "impulses": []}},
        )
        self.store.snapshots[key] = snapshot
        self.store.publications += 1
        return SimpleNamespace(snapshot=snapshot, outcome="published")

    async def publish_superseding(self, user_id, document, old_snapshot_id):
        key = (user_id, document.target_date)
        snapshot = SimpleNamespace(
            id=uuid4(),
            target_date=document.target_date,
            profile_hash=document.profile_hash,
            supersedes_snapshot_id=old_snapshot_id,
            first_day_seen_at=None,
            first_lookahead_seen_at=None,
            deterministic_result_json={"selected": {"convergences": [{"group_id": "cvg-test"}], "main_event": None, "impulses": []}},
        )
        self.store.snapshots[key] = snapshot
        self.store.supersessions += 1
        return SimpleNamespace(snapshot=snapshot, outcome="published")


class FakeLeaseService:
    def __init__(self, store: SnapshotStore, clock):
        self.store = store
        self.clock = clock

    async def acquire(self, snapshot_id, prompt_version, now, lease_duration):
        self.store.lease_acquires += 1
        if self.store.narratives.get(snapshot_id) == "ready":
            return NarrativeLeaseSkip(
                uuid4(), snapshot_id, prompt_version, "ready", "ready", None
            )
        return NarrativeLeaseClaim(
            uuid4(),
            snapshot_id,
            prompt_version,
            self.store.lease_acquires,
            now + lease_duration,
            "created",
        )

    async def complete_ready(self, claim, content_json):
        self.store.narratives[claim.snapshot_id] = "ready"
        self.store.lease_completions.append(("ready", None))
        return NarrativeLeaseCompletion("completed")

    async def complete_unavailable(self, claim, error_code, next_retry_at):
        self.store.lease_completions.append((error_code, next_retry_at))
        return NarrativeLeaseCompletion("completed")


class AccessFactory:
    def __init__(self, states):
        self.states = states

    def __call__(self, _db):
        states = self.states

        class Access:
            async def can_access_day(self, user_id, _target_date):
                return SimpleNamespace(state=states.get(user_id, FULL))

        return Access()


def _service(
    monkeypatch: pytest.MonkeyPatch,
    rows,
    *,
    store: SnapshotStore | None = None,
    settings_obj=None,
    access_states=None,
    calculate_fn=None,
    generate_fn=None,
    retry_delays=None,
    sleep=None,
):
    store = SnapshotStore() if store is None else store
    settings_obj = _settings() if settings_obj is None else settings_obj
    access_states = {} if access_states is None else access_states
    events = []
    monkeypatch.setattr(pregen, "log_event", lambda event, **kwargs: events.append((event, kwargs)))
    monkeypatch.setattr(pregen, "bind_log_context", lambda **_kwargs: None)
    monkeypatch.setattr(pregen, "hash_user_id", lambda _value: "h1_" + "a" * 24)
    monkeypatch.setattr(pregen, "TodayConvergenceCalculationBuilt", FakeBuilt)

    async def selector(_db, _active_days, _now):
        return rows

    async def default_calculate(profile, _target_date):
        return FakeBuilt()

    async def default_generate(_snapshot, **_kwargs):
        return TodayNarrativeSuccess(
            content_json={"summary": "ok", "meaning": "ok", "action": "ok"},
            output_tokens=3,
            latency_ms=1,
        )

    def build_document(profile, calculation):
        return SimpleNamespace(
            target_date=date(2026, 8, 1),
            profile_hash=profile.profile_hash,
        )

    def snapshots(_db):
        return FakeSnapshotService(store)

    def leases(_db, *, clock):
        return FakeLeaseService(store, clock)

    service = pregen.TodayPregenService(
        object(),
        settings_obj=settings_obj,
        active_selector=selector,
        access_service_factory=AccessFactory(access_states),
        local_date_resolver=lambda _owner, _now: date(2026, 8, 1),
        birth_time_resolver=lambda profile: object() if not profile.invalid else (_ for _ in ()).throw(ValueError("invalid")),
        profile_hash_fn=lambda profile, _resolution: profile.profile_hash,
        calculate_fn=calculate_fn or default_calculate,
        document_builder=build_document,
        snapshot_service_factory=snapshots,
        lease_service_factory=leases,
        generate_fn=generate_fn or default_generate,
        retry_delays=retry_delays,
        sleep=sleep,
        clock=lambda: NOW,
        monotonic=lambda: 1.0,
        run_id_factory=lambda: "h1_" + "b" * 24,
    )
    return service, store, events


# START_BLOCK: COHORT
@pytest.mark.asyncio
async def test_cohort_allows_birth_time_modes_excludes_invalid_locked_and_caps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    users = [_user(index) for index in range(1, 7)]
    users[0][1].birth_time_mode = "exact"
    users[1][1].birth_time_mode = "bucket"
    users[1][1].birth_time_bucket = "morning"
    users[2][1].birth_time_mode = "unknown"
    users[3][1].birthday = None
    users[3][1].invalid = True
    locked_user = users[4][0]
    rows = [
        (users[0][0], users[0][1], NOW - timedelta(days=1)),
        (users[1][0], users[1][1], NOW - timedelta(days=2)),
        (users[2][0], users[2][1], NOW - timedelta(days=3)),
        (users[3][0], users[3][1], NOW - timedelta(days=1)),
        (locked_user, users[4][1], NOW - timedelta(days=1)),
    ]
    service, _store, _events = _service(
        monkeypatch,
        rows,
        settings_obj=_settings(day_pregen_max_users=2),
        access_states={locked_user.id: "locked"},
    )

    selection = await service._select_cohort(NOW)

    assert [member.user.id for member in selection.members] == [users[0][0].id, users[1][0].id]
    assert selection.total_eligible == 3
    assert selection.capped is True


@pytest.mark.asyncio
async def test_invalid_settings_fail_before_cohort_and_emit_typed_log(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = False

    async def selector(_db, _active_days, _now):
        nonlocal selected
        selected = True
        return []

    service, _store, events = _service(
        monkeypatch,
        [],
        settings_obj=_settings(day_pregen_concurrency=0),
    )
    service.active_selector = selector

    with pytest.raises(pregen.PregenConfigurationError) as exc_info:
        await service.run(now=NOW)

    assert exc_info.value.setting_name == "day_pregen_concurrency"
    assert selected is False
    assert events[0][0] == "day.pregen_completed"
    assert events[0][1]["payload"]["outcome"] == "invalid_settings"


def test_settings_fields_reject_non_positive_values() -> None:
    with pytest.raises(ValidationError):
        Settings(DAY_PREGEN_ACTIVE_DAYS=0)

    with pytest.raises(ValidationError):
        Settings(DAY_PREGEN_LLM_DEADLINE_SECONDS=-1)


# END_BLOCK: COHORT


# START_BLOCK: DETERMINISTIC
@pytest.mark.asyncio
async def test_rerun_is_idempotent_and_never_creates_impression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, profile = _user(10)
    rows = [(user, profile, NOW - timedelta(days=1))]
    store = SnapshotStore()
    calculate_calls = []
    generate_calls = []

    async def calculate(_profile, _target_date):
        calculate_calls.append(True)
        return FakeBuilt()

    async def generate(_snapshot, **_kwargs):
        generate_calls.append(True)
        return TodayNarrativeSuccess(
            content_json={"summary": "ok", "meaning": "ok", "action": "ok"},
            output_tokens=1,
            latency_ms=1,
        )

    first, _store, first_events = _service(
        monkeypatch,
        rows,
        store=store,
        calculate_fn=calculate,
        generate_fn=generate,
    )
    first_summary = await first.run(now=NOW)
    second, _store, second_events = _service(
        monkeypatch,
        rows,
        store=store,
        calculate_fn=calculate,
        generate_fn=generate,
    )
    second_summary = await second.run(now=NOW)

    assert first_summary.deterministic_published == 1
    assert first_summary.llm_ready == 1
    assert second_summary.deterministic_hit == 1
    assert second_summary.llm_skipped == 1
    assert len(calculate_calls) == 1
    assert len(generate_calls) == 1
    assert store.publications == 1
    assert store.impression_calls == 0
    snapshot = next(iter(store.snapshots.values()))
    assert snapshot.first_day_seen_at is None
    assert snapshot.first_lookahead_seen_at is None
    summary_payload = [
        kwargs["payload"]
        for event, kwargs in second_events
        if event == "day.pregen_completed"
    ][-1]
    assert summary_payload["deterministic_hit"] == 1
    assert first_events[0][0] == "day.pregen_started"


@pytest.mark.asyncio
async def test_unavailable_deterministic_stage_does_not_start_narrative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, profile = _user(11)
    generate_calls = []

    async def calculate(_profile, _target_date):
        return SimpleNamespace(state="unavailable")

    async def generate(_snapshot, **_kwargs):
        generate_calls.append(True)
        return TodayNarrativeFailure(error_code="provider_error", latency_ms=0)

    service, store, _events = _service(
        monkeypatch,
        [(user, profile, NOW - timedelta(days=1))],
        calculate_fn=calculate,
        generate_fn=generate,
    )

    summary = await service.run(now=NOW)

    assert summary.deterministic_failed == 1
    assert summary.llm_ready == 0
    assert generate_calls == []
    assert store.snapshots == {}


# END_BLOCK: DETERMINISTIC


# START_BLOCK: NARRATIVE
@pytest.mark.asyncio
async def test_llm_warmup_is_selective_for_full_fresh_users(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fresh, fresh_profile = _user(20, active_days_ago=1)
    preview, preview_profile = _user(21, active_days_ago=1)
    stale, stale_profile = _user(22, active_days_ago=8)
    generate_calls = []

    async def generate(_snapshot, **_kwargs):
        generate_calls.append(True)
        return TodayNarrativeSuccess(
            content_json={"summary": "ok", "meaning": "ok", "action": "ok"},
            output_tokens=1,
            latency_ms=1,
        )

    service, _store, _events = _service(
        monkeypatch,
        [
            (fresh, fresh_profile, NOW - timedelta(days=1)),
            (preview, preview_profile, NOW - timedelta(days=1)),
            (stale, stale_profile, NOW - timedelta(days=8)),
        ],
        access_states={preview.id: PREVIEW},
        generate_fn=generate,
    )

    summary = await service.run(now=NOW)
    outcomes = {result.user_id: result.outcome.value for result in summary.user_results}

    assert len(generate_calls) == 1
    assert outcomes[fresh.id] == "llm_ready"
    assert outcomes[preview.id] == "llm_skipped_preview"
    assert outcomes[stale.id] == "llm_skipped_stale"
    assert summary.llm_ready == 1
    assert summary.llm_skipped == 2


@pytest.mark.asyncio
async def test_llm_failure_is_bounded_to_three_attempts_and_keeps_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user, profile = _user(23)
    generate_calls = []
    sleep_calls = []

    async def generate(_snapshot, **_kwargs):
        generate_calls.append(True)
        return TodayNarrativeFailure(error_code="provider_error", latency_ms=0)

    async def fake_sleep(seconds: float):
        sleep_calls.append(seconds)

    service, store, _events = _service(
        monkeypatch,
        [(user, profile, NOW - timedelta(days=1))],
        generate_fn=generate,
        retry_delays=(0, 1, 2),
        sleep=fake_sleep,
    )

    summary = await service.run(now=NOW)

    assert summary.llm_unavailable == 1
    assert len(generate_calls) == 3
    assert sleep_calls == [1.0, 1.0]
    assert len(store.lease_completions) == 3
    assert all(code == "provider_error" for code, _retry_at in store.lease_completions)
    assert store.lease_completions[-1][1] > NOW + timedelta(seconds=2)
    assert len(store.snapshots) == 1
    snapshot = next(iter(store.snapshots.values()))
    assert snapshot.first_day_seen_at is None
    assert snapshot.first_lookahead_seen_at is None


# END_BLOCK: NARRATIVE


# START_BLOCK: SUMMARY
@pytest.mark.asyncio
async def test_one_user_exception_does_not_abort_batch_and_summary_matches_outcomes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad, bad_profile = _user(30)
    good, good_profile = _user(31)

    async def calculate(profile, _target_date):
        if profile is bad_profile:
            raise RuntimeError("not logged")
        return FakeBuilt()

    service, _store, events = _service(
        monkeypatch,
        [
            (bad, bad_profile, NOW - timedelta(days=1)),
            (good, good_profile, NOW - timedelta(days=2)),
        ],
        access_states={bad.id: PREVIEW, good.id: PREVIEW},
        calculate_fn=calculate,
    )

    summary = await service.run(now=NOW)

    assert summary.cohort_size == 2
    assert summary.deterministic_failed == 1
    assert summary.deterministic_published == 1
    assert {result.user_id for result in summary.user_results} == {bad.id, good.id}
    failed_events = [
        kwargs for event, kwargs in events
        if event == "day.pregen_user_finished" and kwargs["payload"]["outcome"] == "failed"
    ]
    assert failed_events[0]["payload"]["error_type"] == "RuntimeError"
    assert "not logged" not in str(events)


# END_BLOCK: SUMMARY
