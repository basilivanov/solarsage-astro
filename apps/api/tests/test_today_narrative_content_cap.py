# ############################################################################
# AI_HEADER: TEST_TODAY-NARRATIVE-CONTENT-CAP — W6 maximum narrative shapes.
# ROLE: Proves that hero and quiet legal payloads stay bounded, claim-bound,
#   token-measured, and atomically rejected when the provider response breaks.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-NARRATIVE-CONTENT-CAP
# purpose: Exercise the production Today narrative service at its maximum legal
#   selected-unit shapes without invoking a real provider or projection layer.
# owns:
#   - apps/api/tests/test_today_narrative_content_cap.py
# inputs: in-memory TodaySnapshot-like rows and deterministic provider envelopes.
# outputs: assertions for bounded prompts, 700-token forwarding, output-token
#   extraction/logging, claim binding, summary boundaries, and truncation.
# dependencies: TodaySnapshot, today_narrative_service, pytest-asyncio.
# side_effects: no network, database, persistence, or projection calls; logs
#   are captured in memory.
# emitted_logs: day.narrative_generation_started,
#   day.narrative_generation_completed, day.narrative_generation_failed.
# invariants: only selected event units enter the prompt; every accepted claim
#   is bound to a selected event; malformed/truncated content is unavailable.
# failure_policy: pytest fails on prompt leakage, cap drift, partial acceptance,
#   token measurement drift, or an incorrect 220/221 boundary.
# END_MODULE_CONTRACT: M-TEST-TODAY-NARRATIVE-CONTENT-CAP

# START_MODULE_MAP: M-TEST-TODAY-NARRATIVE-CONTENT-CAP
# public_entrypoints:
#   - test_max_shapes_are_bounded_and_measured
#   - test_summary_boundary_is_atomic
#   - test_truncated_provider_json_is_schema_invalid
# semantic_blocks:
#   - MAX_SHAPES: hero and quiet selected-unit ceiling snapshots.
#   - CONTENT_CAP: prompt bounds, provider cap, success, claims, and tokens.
#   - BOUNDARY: summary 220/221 atomic validation.
#   - TRUNCATION: malformed mid-response rejection.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-NARRATIVE-CONTENT-CAP

from __future__ import annotations

import copy
import json
from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from app.db.models import TodaySnapshot
from app.services.today_narrative_service import (
    TodayNarrativeFailure,
    TodayNarrativeSuccess,
    generate_today_narrative,
)


USER_ID = UUID("11111111-1111-4111-8111-111111111111")
HERO_SNAPSHOT_ID = UUID("33333333-3333-4333-8333-333333333333")
QUIET_SNAPSHOT_ID = UUID("55555555-5555-4555-8555-555555555555")
TARGET_DATE = date(2026, 7, 31)
PUBLISHED_AT = datetime(2026, 7, 30, 21, 0, tzinfo=timezone.utc)
OUTPUT_TOKENS = 698


class ContentCapFakeLLM:
    def __init__(self, response: object, *, output_tokens: int = OUTPUT_TOKENS) -> None:
        self.response = response
        self.output_tokens = output_tokens
        self.calls: list[dict[str, object]] = []

    async def generate(
        self,
        prompt: str,
        *,
        max_output_tokens: int,
        timeout_seconds: float,
    ) -> object:
        self.calls.append(
            {
                "prompt": prompt,
                "max_output_tokens": max_output_tokens,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {
            "text": self.response,
            "output_tokens": self.output_tokens,
        }


def _factor(
    event_id: str,
    *,
    event_class: str = "aspect",
    polarity: str = "supportive",
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
        "exact_at": "2026-07-31T15:40:00+03:00",
        "active_from": "2026-07-31T13:00:00+03:00",
        "active_until": "2026-07-31T18:00:00+03:00",
    }


def _group(group_id: str, event_ids: list[str], *, sphere: str) -> dict[str, object]:
    return {
        "group_id": group_id,
        "anchor_event_id": event_ids[0],
        "member_event_ids": list(event_ids),
        "evidence_event_ids": list(event_ids),
        "primary_sphere": sphere,
        "secondary_sphere": "documents",
        "polarity": "supportive",
        "evidence_level": "high",
    }


def _single(
    event_id: str,
    *,
    sphere: str,
    polarity: str = "supportive",
) -> dict[str, object]:
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
    mode: str,
    snapshot_id: UUID,
    lookahead: bool = False,
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
    if main_event is not None:
        selected_spheres.append(main_event["sphere"])  # type: ignore[arg-type]
    selected_spheres.extend(impulse["sphere"] for impulse in impulses)  # type: ignore[index]
    selected_spheres = list(dict.fromkeys(selected_spheres))

    capabilities = {
        "houses": mode == "exact",
        "angles": mode == "exact",
        "lots": mode == "exact",
        "exact_timing": mode == "exact",
    }
    canonical_input = {
        "schema_version": "today-canonical-input.v1",
        "birth_time": {
            "mode": mode,
            "bucket": "morning" if mode == "bucket" else None,
            "range": (
                {"start": "06:00", "end": "12:00"}
                if mode == "bucket"
                else {"start": "12:34", "end": "12:34"}
            ),
            "capabilities": capabilities,
        },
        # The full ledger is intentionally present only in the snapshot-like
        # input. The production prompt builder must project selected units.
        "factor_units": copy.deepcopy(factors),
    }
    deterministic_result: dict[str, object] = {
        "schema_version": "today-deterministic-result.v1",
        "state": state,
        "day_tone": "steady" if state == "quiet_day" else "supportive",
        "selected": {
            "convergences": copy.deepcopy(convergences),
            "main_event": copy.deepcopy(main_event),
            "impulses": copy.deepcopy(impulses),
            "selected_unit_ids": selected_ids,
            "selected_spheres": selected_spheres,
        },
    }
    if lookahead:
        # Lookahead is a projection-only field, not a Today narrative input.
        deterministic_result["lookahead"] = [{"event_id": "evt_v1_lookahead"}]

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
        birth_time_range=(
            {"start": "06:00", "end": "12:00"}
            if mode == "bucket"
            else {"start": "12:34", "end": "12:34"}
        ),
        deterministic_result_json=deterministic_result,
        canonical_input_json=canonical_input,
        published_at=PUBLISHED_AT,
    )


# START_BLOCK: MAX_SHAPES
def _hero_max() -> TodaySnapshot:
    groups = [
        _group("cvg-1", ["evt_v1_1", "evt_v1_2"], sphere="work"),
        _group("cvg-2", ["evt_v1_3", "evt_v1_4"], sphere="money"),
        _group("cvg-3", ["evt_v1_5", "evt_v1_6"], sphere="relationships"),
    ]
    selected_ids = [
        event_id
        for group in groups
        for event_id in group["evidence_event_ids"]  # type: ignore[index]
    ]
    factors = [_factor(event_id) for event_id in selected_ids]
    factors.extend([_factor("evt_v1_unused_hero_1"), _factor("evt_v1_unused_hero_2")])
    return _snapshot(
        state="convergence_today",
        convergences=groups,
        main_event=None,
        impulses=[],
        factors=factors,
        mode="exact",
        snapshot_id=HERO_SNAPSHOT_ID,
    )


def _quiet_max() -> TodaySnapshot:
    main_event = _single("evt_v1_main", sphere="work")
    impulses = [
        _single("evt_v1_impulse_1", sphere="documents", polarity="mixed"),
        _single("evt_v1_impulse_2", sphere="health", polarity="tense"),
        _single("evt_v1_impulse_3", sphere="study", polarity="supportive"),
    ]
    selected_ids = ["evt_v1_main", "evt_v1_impulse_1", "evt_v1_impulse_2", "evt_v1_impulse_3"]
    factors = [_factor("evt_v1_main", event_class="structural")]
    factors.extend(
        _factor(event_id, event_class="activation")
        for event_id in selected_ids[1:]
    )
    factors.append(_factor("evt_v1_unused_quiet"))
    return _snapshot(
        state="quiet_day",
        convergences=[],
        main_event=main_event,
        impulses=impulses,
        factors=factors,
        mode="bucket",
        snapshot_id=QUIET_SNAPSHOT_ID,
        lookahead=True,
    )


# END_BLOCK: MAX_SHAPES


def _claim(text: str, event_ids: list[str]) -> dict[str, object]:
    return {"text": text, "sourceEventIds": list(event_ids)}


def _summary_text() -> str:
    value = (
        "Собери внимание вокруг выбранной задачи, удерживай спокойный темп и "
        "отмечай один понятный результат без лишней спешки. "
    ) * 8
    return value[:200]


def _full_block(event_ids: list[str]) -> dict[str, object]:
    return {
        "summary": _claim(_summary_text(), event_ids),
        "meaning": _claim("Этот сигнал помогает увидеть устойчивую линию и сохранить ясный фокус.", event_ids),
        "action": _claim("Выбери один ближайший шаг и проверь его спокойным внимательным темпом.", event_ids),
    }


def _max_content(snapshot: TodaySnapshot) -> dict[str, object]:
    selected = snapshot.deterministic_result_json["selected"]  # type: ignore[index]
    if snapshot.deterministic_result_json["state"] == "convergence_today":  # type: ignore[index]
        return {
            "convergences": {
                group["group_id"]: _full_block(group["evidence_event_ids"])  # type: ignore[index]
                for group in selected["convergences"]  # type: ignore[index]
            },
            "main_event": None,
            "impulses": {},
        }

    main_event = selected["main_event"]  # type: ignore[index]
    impulses = selected["impulses"]  # type: ignore[index]
    return {
        "convergences": {},
        "main_event": _full_block([main_event["event_id"]]),  # type: ignore[index]
        "impulses": {
            impulse["event_id"]: _full_block([impulse["event_id"]])  # type: ignore[index]
            for impulse in impulses  # type: ignore[union-attr]
        },
    }


def _assert_claims_bound(snapshot: TodaySnapshot, content: dict[str, object]) -> None:
    selected = snapshot.deterministic_result_json["selected"]  # type: ignore[index]
    selected_ids = set(selected["selected_unit_ids"])  # type: ignore[index]
    blocks = list(content["convergences"].values())  # type: ignore[union-attr]
    if content["main_event"] is not None:
        blocks.append(content["main_event"])
    blocks.extend(content["impulses"].values())  # type: ignore[union-attr]

    assert blocks
    for block in blocks:
        assert set(block) == {"summary", "meaning", "action"}  # type: ignore[arg-type]
        for claim in block.values():  # type: ignore[union-attr]
            assert claim is not None
            assert claim["sourceEventIds"]  # type: ignore[index]
            assert set(claim["sourceEventIds"]).issubset(selected_ids)  # type: ignore[index]


# START_BLOCK: CONTENT_CAP
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("snapshot_factory", "selected_event_count"),
    [(_hero_max, 6), (_quiet_max, 4)],
    ids=["hero-3-groups", "quiet-main-3-impulses"],
)
async def test_max_shapes_are_bounded_and_measured(
    snapshot_factory,
    selected_event_count: int,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = snapshot_factory()
    content = _max_content(snapshot)
    fake = ContentCapFakeLLM(json.dumps(content, ensure_ascii=False))
    events: list[tuple[str, dict[str, object]]] = []

    def capture(event: str, **kwargs: object) -> None:
        events.append((event, kwargs))

    monkeypatch.setattr("app.services.today_narrative_service.log_event", capture)
    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=fake,
        correlation_id="corr_content_cap",
    )

    assert isinstance(result, TodayNarrativeSuccess)
    _assert_claims_bound(snapshot, result.content_json)
    assert json.loads(json.dumps(result.content_json, ensure_ascii=False)) == result.content_json
    assert fake.calls[0]["max_output_tokens"] == 700
    assert result.output_tokens == OUTPUT_TOKENS
    assert 0 <= result.output_tokens <= fake.calls[0]["max_output_tokens"]  # type: ignore[operator]

    prompt = fake.calls[0]["prompt"]
    assert prompt.count("evt_") == selected_event_count
    assert "factor_units" not in prompt
    assert '"audit"' not in prompt
    assert "evt_v1_unused_" not in prompt
    assert "evt_v1_lookahead" not in prompt
    if snapshot.deterministic_result_json["state"] == "quiet_day":  # type: ignore[index]
        assert prompt.count('"partOfDay"') == selected_event_count

    completed = [payload for event, payload in events if event == "day.narrative_generation_completed"]
    assert len(completed) == 1
    assert completed[0]["payload"]["output_tokens"] == OUTPUT_TOKENS  # type: ignore[index]
# END_BLOCK: CONTENT_CAP


# START_BLOCK: BOUNDARY
@pytest.mark.asyncio
@pytest.mark.parametrize(("summary_length", "success"), [(220, True), (221, False)])
async def test_summary_boundary_is_atomic(summary_length: int, success: bool) -> None:
    snapshot = _quiet_max()
    content = _max_content(snapshot)
    content["main_event"]["summary"] = _claim(  # type: ignore[index]
        "x" * summary_length,
        ["evt_v1_main"],
    )
    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=ContentCapFakeLLM(json.dumps(content, ensure_ascii=False)),
    )

    assert isinstance(result, TodayNarrativeSuccess) is success
    if not success:
        assert isinstance(result, TodayNarrativeFailure)
        assert result.error_code == "schema_invalid"
# END_BLOCK: BOUNDARY


# START_BLOCK: TRUNCATION
@pytest.mark.asyncio
async def test_truncated_provider_json_is_schema_invalid() -> None:
    snapshot = _hero_max()
    content = json.dumps(_max_content(snapshot), ensure_ascii=False)
    truncated = content[: len(content) // 2]
    result = await generate_today_narrative(
        snapshot,
        prompt_version="today-narrative-v1",
        llm=ContentCapFakeLLM(truncated, output_tokens=700),
    )

    assert isinstance(result, TodayNarrativeFailure)
    assert result.error_code == "schema_invalid"
# END_BLOCK: TRUNCATION
