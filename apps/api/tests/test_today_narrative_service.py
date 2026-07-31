# ############################################################################
# AI_HEADER: TEST_TODAY_NARRATIVE_SERVICE — bounded Today narrative evidence.
# ROLE: Proves prompt bounds, strict response validation, capability gating,
#       deadline behavior, token forwarding, and generation lifecycle logging.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-NARRATIVE
# purpose: Exercise the pure Today narrative producer with fake provider calls.
# owns:
#   - apps/api/tests/test_today_narrative_service.py
# inputs: In-memory TodaySnapshot rows and deterministic fake LLM responses.
# outputs: Assertions for success content_json or typed unavailable failures.
# dependencies: today_narrative_service, TodaySnapshot, pytest-asyncio.
# side_effects: No network or database calls; logging is intercepted in tests.
# emitted_logs: day.narrative_generation_started,
#   day.narrative_generation_completed, day.narrative_generation_failed.
# invariants: Tests never use a real provider and never accept partial narrative.
# failure_policy: pytest failure on prompt leakage, invalid acceptance, or log guard failure.
# END_MODULE_CONTRACT: M-TEST-TODAY-NARRATIVE

# START_MODULE_MAP: M-TEST-TODAY-NARRATIVE
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - FIXTURES: stable snapshots, factors, and fake provider.
#   - HAPPY_PATH: convergence and quiet-day canonical content.
#   - VALIDATION: schema, binding, length, block identity, and capability gates.
#   - OPERATIONS: deadline, provider error, prompt bounds, tokens, and logs.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-NARRATIVE

from __future__ import annotations

import asyncio
import copy
import json
from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from app.db.models import TodaySnapshot
from app.services.today_narrative_service import (
    TodayNarrativeFailure,
    TodayNarrativeSuccess,
    build_today_narrative_prompt,
    generate_today_narrative,
)


SNAPSHOT_ID = UUID("33333333-3333-4333-8333-333333333333")
USER_ID = UUID("11111111-1111-4111-8111-111111111111")
PUBLISHED_AT = datetime(2026, 7, 30, 21, 0, tzinfo=timezone.utc)
TARGET_DATE = date(2026, 7, 31)


class FakeLLM:
    def __init__(self, response: object = None, error: BaseException | None = None) -> None:
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int,
        timeout_seconds: float,
    ) -> object:
        self.calls.append({
            "prompt": prompt,
            "max_output_tokens": max_output_tokens,
            "timeout_seconds": timeout_seconds,
        })
        if self.error is not None:
            raise self.error
        return self.response


def _factor(
    event_id: str,
    *,
    event_class: str = "aspect",
    polarity: str = "tense",
    exact_at: str = "2026-07-31T15:40:00+03:00",
    active_from: str | None = "2026-07-31T13:00:00+03:00",
    active_until: str | None = "2026-07-31T18:00:00+03:00",
) -> dict[str, object]:
    return {
        "canonical_event_id": event_id,
        "event_class": event_class,
        "technique_horizon": "today",
        "source_key": f"activation-{event_id}",
        "semantic_key": f"semantic-{event_id}",
        "driver_key": f"driver-{event_id}",
        "product_spheres": ["work"],
        "polarity": polarity,
        "evidence_level": "high",
        "exact_at": exact_at,
        "active_from": active_from,
        "active_until": active_until,
    }


def _group(group_id: str, event_ids: list[str], *, sphere: str = "work") -> dict[str, object]:
    return {
        "group_id": group_id,
        "anchor_event_id": event_ids[0],
        "member_event_ids": list(event_ids),
        "evidence_event_ids": list(event_ids),
        "primary_sphere": sphere,
        "secondary_sphere": "documents",
        "polarity": "tense",
        "evidence_level": "high",
    }


def _single(event_id: str, *, sphere: str, polarity: str = "supportive") -> dict[str, object]:
    return {
        "event_id": event_id,
        "sphere": sphere,
        "polarity": polarity,
        "evidence_level": "medium",
    }


def _snapshot(
    *,
    state: str,
    convergences: list[dict[str, object]],
    main_event: dict[str, object] | None,
    impulses: list[dict[str, object]],
    factors: list[dict[str, object]],
    mode: str = "exact",
    capabilities: dict[str, bool] | None = None,
    snapshot_id: UUID = SNAPSHOT_ID,
) -> TodaySnapshot:
    selected_ids = [
        event_id
        for group in convergences
        for event_id in group["evidence_event_ids"]  # type: ignore[index]
    ]
    if main_event is not None:
        selected_ids.append(main_event["event_id"])  # type: ignore[arg-type]
    selected_ids.extend(impulse["event_id"] for impulse in impulses)  # type: ignore[index]
    selected_spheres = [
        group["primary_sphere"]  # type: ignore[index]
        for group in convergences
    ]
    selected_spheres.extend(
        [main_event["sphere"]] if main_event is not None else []  # type: ignore[index]
    )
    selected_spheres.extend(impulse["sphere"] for impulse in impulses)  # type: ignore[index]
    selected_spheres = list(dict.fromkeys(selected_spheres))
    exact_capabilities = {
        "houses": mode == "exact",
        "angles": mode == "exact",
        "lots": mode == "exact",
        "exact_timing": mode == "exact",
    }
    exact_capabilities.update(capabilities or {})
    canonical_input = {
        "schema_version": "today-canonical-input.v1",
        "birth_time": {
            "mode": mode,
            "bucket": "morning" if mode == "bucket" else None,
            "range": {"start": "06:00", "end": "12:00"} if mode == "bucket" else {"start": "12:34", "end": "12:34"},
            "capabilities": exact_capabilities,
        },
        "factor_units": copy.deepcopy(factors),
    }
    deterministic_result = {
        "schema_version": "today-deterministic-result.v1",
        "state": state,
        "day_tone": "steady" if state == "quiet_day" else "tense",
        "selected": {
            "convergences": copy.deepcopy(convergences),
            "main_event": copy.deepcopy(main_event),
            "impulses": copy.deepcopy(impulses),
            "selected_unit_ids": selected_ids,
            "selected_spheres": selected_spheres,
        },
    }
    return TodaySnapshot(
        id=snapshot_id,
        user_id=USER_ID,
        target_date=TARGET_DATE,
        timezone="Europe/Moscow",
        profile_hash="profile-hash",
        input_hash="input-hash",
        canon_hash="canon-hash",
        formula_version="today-convergence-2",
        calculation_version="ss-calc-1.3.0",
        ephemeris_artifact_id="ephemeris-1",
        birth_time_mode=mode,
        birth_time_range={"start": "06:00", "end": "12:00"} if mode == "bucket" else {"start": "12:34", "end": "12:34"},
        deterministic_result_json=deterministic_result,
        canonical_input_json=canonical_input,
        published_at=PUBLISHED_AT,
    )


def _convergence_snapshot(*, extra_factors: int = 0) -> TodaySnapshot:
    groups = [
        _group("cvg-1", ["evt_v1_1", "evt_v1_2"], sphere="work"),
        _group("cvg-2", ["evt_v1_3", "evt_v1_4"], sphere="money"),
        _group("cvg-3", ["evt_v1_5", "evt_v1_6"], sphere="relationships"),
    ]
    factors = [
        _factor(event_id, event_class="aspect" if index % 2 else "structural")
        for index, event_id in enumerate(
            [event_id for group in groups for event_id in group["evidence_event_ids"]]  # type: ignore[index]
        )
    ]
    factors.extend(_factor(f"evt_v1_unused_{index}") for index in range(extra_factors))
    return _snapshot(
        state="convergence_today",
        convergences=groups,
        main_event=None,
        impulses=[],
        factors=factors,
    )


def _quiet_snapshot(*, mode: str = "exact", capabilities: dict[str, bool] | None = None) -> TodaySnapshot:
    main_event = _single("evt_v1_main", sphere="work")
    impulses = [
        _single("evt_v1_impulse_1", sphere="documents", polarity="mixed"),
        _single("evt_v1_impulse_2", sphere="health", polarity="tense"),
        _single("evt_v1_impulse_3", sphere="study", polarity="supportive"),
    ]
    factors = [_factor("evt_v1_main", event_class="structural")]
    factors.extend(_factor(impulse["event_id"], event_class="activation") for impulse in impulses)  # type: ignore[index]
    return _snapshot(
        state="quiet_day",
        convergences=[],
        main_event=main_event,
        impulses=impulses,
        factors=factors,
        mode=mode,
        capabilities=capabilities,
        snapshot_id=UUID("55555555-5555-4555-8555-555555555555"),
    )


def _claim(text: str, event_ids: list[str]) -> dict[str, object]:
    return {"text": text, "sourceEventIds": event_ids}


def _empty_block() -> dict[str, object]:
    return {"summary": None, "meaning": None, "action": None}


def _convergence_content(snapshot: TodaySnapshot) -> dict[str, object]:
    selected = snapshot.deterministic_result_json["selected"]  # type: ignore[index]
    return {
        "convergences": {
            group["group_id"]: {
                "summary": _claim("Собери внимание вокруг главной задачи.", group["evidence_event_ids"]),
                "meaning": None,
                "action": None,
            }
            for group in selected["convergences"]  # type: ignore[index]
        },
        "main_event": None,
        "impulses": {},
    }


def _quiet_content(snapshot: TodaySnapshot, *, text: str = "Выбери один понятный следующий шаг.") -> dict[str, object]:
    selected = snapshot.deterministic_result_json["selected"]  # type: ignore[index]
    main_event = selected["main_event"]  # type: ignore[index]
    impulses = selected["impulses"]  # type: ignore[index]
    return {
        "convergences": {},
        "main_event": {
            "summary": _claim(text, [main_event["event_id"]]),  # type: ignore[index]
            "meaning": None,
            "action": None,
        },
        "impulses": {
            impulse["event_id"]: {
                "summary": _claim("Действуй без спешки и держи фокус.", [impulse["event_id"]]),
                "meaning": None,
                "action": None,
            }
            for impulse in impulses  # type: ignore[union-attr]
        },
    }


# START_BLOCK: HAPPY_PATH
@pytest.mark.asyncio
async def test_convergence_today_three_groups_accepts_bound_claims() -> None:
    snapshot = _convergence_snapshot()
    fake = FakeLLM(json.dumps(_convergence_content(snapshot), ensure_ascii=False))

    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=fake,
        correlation_id="corr_test_convergence",
    )

    assert isinstance(result, TodayNarrativeSuccess)
    assert set(result.content_json["convergences"]) == {"cvg-1", "cvg-2", "cvg-3"}
    assert result.content_json["main_event"] is None
    assert fake.calls[0]["max_output_tokens"] == 700


@pytest.mark.asyncio
async def test_quiet_day_main_event_and_three_impulses_accepts_bound_claims() -> None:
    snapshot = _quiet_snapshot()
    fake = FakeLLM(json.dumps(_quiet_content(snapshot), ensure_ascii=False))

    result = await generate_today_narrative(snapshot, prompt_version="today-narrative-v1", llm=fake)

    assert isinstance(result, TodayNarrativeSuccess)
    assert result.content_json["main_event"]["summary"]["sourceEventIds"] == ["evt_v1_main"]  # type: ignore[index]
    assert set(result.content_json["impulses"]) == {
        "evt_v1_impulse_1",
        "evt_v1_impulse_2",
        "evt_v1_impulse_3",
    }


# END_BLOCK: HAPPY_PATH


# START_BLOCK: VALIDATION
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_ids",
    [["foreign-event"], [], ["evt_v1_main", "evt_v1_main"]],
)
async def test_claim_binding_rejects_foreign_empty_and_duplicate_ids(source_ids: list[str]) -> None:
    snapshot = _quiet_snapshot()
    content = _quiet_content(snapshot)
    content["main_event"]["summary"] = _claim("Текст", source_ids)  # type: ignore[index]

    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM(json.dumps(content, ensure_ascii=False)),
    )

    assert isinstance(result, TodayNarrativeFailure)
    assert result.error_code == "claim_binding"
    assert result.latency_ms >= 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("length", "expected"),
    [(220, True), (221, False)],
)
async def test_summary_character_boundary_is_atomic(length: int, expected: bool) -> None:
    snapshot = _quiet_snapshot()
    content = _quiet_content(snapshot)
    content["main_event"]["summary"] = _claim("x" * length, ["evt_v1_main"])  # type: ignore[index]

    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM(json.dumps(content, ensure_ascii=False)),
    )

    assert isinstance(result, TodayNarrativeSuccess) is expected
    if not expected:
        assert isinstance(result, TodayNarrativeFailure)
        assert result.error_code == "schema_invalid"


@pytest.mark.asyncio
async def test_unknown_block_id_and_missing_required_block_are_schema_invalid() -> None:
    snapshot = _quiet_snapshot()
    unknown = _quiet_content(snapshot)
    unknown["impulses"]["foreign-event"] = _empty_block()  # type: ignore[index]
    unknown_result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM(json.dumps(unknown, ensure_ascii=False)),
    )
    assert isinstance(unknown_result, TodayNarrativeFailure)
    assert unknown_result.error_code == "schema_invalid"

    missing = _quiet_content(snapshot)
    del missing["main_event"]
    missing_result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM(json.dumps(missing, ensure_ascii=False)),
    )
    assert isinstance(missing_result, TodayNarrativeFailure)
    assert missing_result.error_code == "schema_invalid"


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_response", ["not-json", json.dumps({"convergences": {}})])
async def test_invalid_json_or_shape_is_schema_invalid(raw_response: str) -> None:
    result = await generate_today_narrative(
        _quiet_snapshot(),
        prompt_version="today-narrative-v1",
        llm=FakeLLM(raw_response),
    )

    assert isinstance(result, TodayNarrativeFailure)
    assert result.error_code == "schema_invalid"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "text", "capabilities"),
    [
        ("bucket", "Проверь дом и ASC.", None),
        ("unknown", "В 15:40 сделай шаг.", None),
        ("exact", "В 15:40 сделай шаг.", None),
        ("exact", "Посмотри на дом.", {"houses": False}),
    ],
)
async def test_capability_gate_rejects_time_and_unavailable_details(
    mode: str,
    text: str,
    capabilities: dict[str, bool] | None,
) -> None:
    snapshot = _quiet_snapshot(mode=mode, capabilities=capabilities)
    content = _quiet_content(snapshot, text=text)

    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM(json.dumps(content, ensure_ascii=False)),
    )

    assert isinstance(result, TodayNarrativeFailure)
    assert result.error_code == "capability_violation"


@pytest.mark.asyncio
async def test_exact_capability_allows_house_reference_but_not_clock_text() -> None:
    snapshot = _quiet_snapshot(
        mode="exact",
        capabilities={"houses": True, "angles": True, "lots": True},
    )
    content = _quiet_content(snapshot, text="Посмотри на дом и выбери следующий шаг.")
    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM(json.dumps(content, ensure_ascii=False)),
    )

    assert isinstance(result, TodayNarrativeSuccess)


# END_BLOCK: VALIDATION


# START_BLOCK: OPERATIONS
@pytest.mark.asyncio
async def test_timeout_and_provider_error_return_typed_failures_with_latency() -> None:
    class HangingLLM(FakeLLM):
        async def generate(self, prompt: str, *, max_output_tokens: int, timeout_seconds: float) -> object:
            self.calls.append({"prompt": prompt, "max_output_tokens": max_output_tokens})
            await asyncio.sleep(1)
            return "{}"

    timeout_result = await generate_today_narrative(
        _quiet_snapshot(),
        prompt_version="today-narrative-v1",
        llm=HangingLLM(),
        timeout_seconds=0.001,
    )
    provider_result = await generate_today_narrative(
        _quiet_snapshot(),
        prompt_version="today-narrative-v1",
        llm=FakeLLM(error=RuntimeError("provider down")),
    )

    assert isinstance(timeout_result, TodayNarrativeFailure)
    assert timeout_result.error_code == "timeout"
    assert timeout_result.latency_ms >= 0
    assert isinstance(provider_result, TodayNarrativeFailure)
    assert provider_result.error_code == "provider_error"
    assert provider_result.latency_ms >= 0


@pytest.mark.asyncio
async def test_prompt_is_bounded_to_selected_units_and_forwards_700_tokens() -> None:
    snapshot = _convergence_snapshot(extra_factors=20)
    fake = FakeLLM(json.dumps(_convergence_content(snapshot), ensure_ascii=False), error=None)
    result = await generate_today_narrative(snapshot, prompt_version="today-narrative-v1", llm=fake)
    prompt = fake.calls[0]["prompt"]
    selected_count = len(snapshot.deterministic_result_json["selected"]["selected_unit_ids"])  # type: ignore[index]

    assert isinstance(result, TodayNarrativeSuccess)
    assert prompt.count("evt_v1_") <= selected_count
    assert "factor_units" not in prompt
    assert '"audit"' not in prompt
    assert '"profile"' not in prompt
    assert fake.calls[0]["max_output_tokens"] == 700

    direct_prompt = build_today_narrative_prompt(snapshot, prompt_version="today-narrative-v1")
    assert direct_prompt == prompt


@pytest.mark.asyncio
async def test_three_generation_events_have_safe_fields_and_logger_failure_is_swallowed(monkeypatch) -> None:
    events: list[tuple[str, dict[str, object]]] = []

    def capture(event: str, **kwargs: object) -> None:
        events.append((event, kwargs))

    monkeypatch.setattr("app.services.today_narrative_service.log_event", capture)
    snapshot = _quiet_snapshot()
    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM({"text": json.dumps(_quiet_content(snapshot), ensure_ascii=False), "output_tokens": 19}),
        correlation_id="corr_test_logging",
    )

    assert isinstance(result, TodayNarrativeSuccess)
    assert [event for event, _ in events] == [
        "day.narrative_generation_started",
        "day.narrative_generation_completed",
    ]
    assert events[0][1]["payload"]["convergence_count"] == 0  # type: ignore[index]
    assert events[1][1]["payload"]["output_tokens"] == 19  # type: ignore[index]
    assert events[1][1]["payload"]["claims_count"] == 4  # type: ignore[index]

    failed = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM(error=RuntimeError("provider down")),
    )
    assert isinstance(failed, TodayNarrativeFailure)
    assert failed.error_code == "provider_error"
    assert [event for event, _ in events][-2:] == [
        "day.narrative_generation_started",
        "day.narrative_generation_failed",
    ]
    assert events[-1][1]["payload"]["error_code"] == "provider_error"  # type: ignore[index]
    assert events[-1][1]["payload"]["latency_ms"] >= 0  # type: ignore[index]

    def fail_log(*args: object, **kwargs: object) -> None:
        raise RuntimeError("logger unavailable")

    monkeypatch.setattr("app.services.today_narrative_service.log_event", fail_log)
    swallowed = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=FakeLLM(json.dumps(_quiet_content(snapshot), ensure_ascii=False)),
    )
    assert isinstance(swallowed, TodayNarrativeSuccess)


# END_BLOCK: OPERATIONS
