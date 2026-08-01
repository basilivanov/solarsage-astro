# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_PROJECTION — deterministic wire projection contract.
# ROLE: Proves the pure TodaySnapshot-to-wire projection and fail-closed matrix.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-PROJECTION
# purpose: Exercise the deterministic Today convergence wire projection from
#   published snapshot rows, narrative rows, and content access state.
# owns:
#   - apps/api/tests/test_today_convergence_projection.py
# inputs: In-memory TodaySnapshot/TodaySnapshotNarrative rows and access models.
# outputs: Assertions for validated TodayConvergencePayload values and errors.
# dependencies: app.services.today_convergence_projection, Today convergence schemas.
# side_effects: none.
# emitted_logs: none.
# invariants: Projection tests use stable input rows and never require HTTP/DB/LLM;
#   exact EventTime assertions cover date-aware absolute instants and midpoint fallback.
# failure_policy: pytest failure on contract or atomic-fallback drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-PROJECTION

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-PROJECTION
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - SNAPSHOT_BUILDERS: stable in-memory source rows for projection tests.
#   - MATRIX: access, narrative, birth-time, and event-time contract cases.
#   - FAIL_CLOSED: invalid references and invalid narrative atomics.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-PROJECTION

from __future__ import annotations

import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from app.db.models import TodaySnapshot, TodaySnapshotNarrative
from app.schemas.access import ContentAccessState
from app.schemas.today_convergence import TodayConvergenceBirthTime
from app.services.today_convergence_projection import (
    TodayConvergenceProjectionError,
    project_empty_payload,
    project_snapshot_payload,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET_DATE = date(2026, 7, 31)
PUBLISHED_AT = datetime(2026, 7, 30, 21, 0, tzinfo=timezone.utc)


def _access(state: str) -> ContentAccessState:
    if state == "full":
        return ContentAccessState(
            state="full",
            reason="active_subscription",
            subscription_active=True,
            access_until="2026-08-31",
        )
    if state == "preview":
        return ContentAccessState(
            state="preview",
            reason="active_referral_days",
            referral_days_left=2,
            subscription_active=False,
            access_until="2026-08-02",
        )
    return ContentAccessState(
        state="locked",
        reason="outside_access_window",
        referral_days_left=0,
        subscription_active=False,
    )


def _factor(
    event_id: str,
    *,
    event_class: str = "aspect",
    source_key: str | None = None,
    target_key: str | None = None,
    target_type: str = "",
    aspect_type: str | None = None,
    polarity: str = "tense",
    exact_at: str | None = "2026-07-31T15:40:00+03:00",
    active_from: str | None = "2026-07-31T13:00:00+03:00",
    active_until: str | None = "2026-07-31T18:00:00+03:00",
) -> dict[str, Any]:
    return {
        "canonical_event_id": event_id,
        "event_class": event_class,
        "technique_horizon": "today",
        "source_key": source_key or f"activation-{event_id}",
        "target_key": target_key or "",
        "target_type": target_type,
        "aspect_type": aspect_type,
        "semantic_key": f"semantic-{event_id}",
        "driver_key": f"driver-{event_id}",
        "product_spheres": ["work"],
        "polarity": polarity,
        "exact_at": exact_at,
        "active_from": active_from,
        "active_until": active_until,
    }


def _hero_result() -> dict[str, Any]:
    return {
        "schema_version": "today-deterministic-result.v1",
        "state": "convergence_today",
        "day_tone": "tense",
        "selected": {
            "convergences": [
                {
                    "group_id": "cvg-hero",
                    "anchor_event_id": "evt-1",
                    "member_event_ids": ["evt-1", "evt-2"],
                    "evidence_event_ids": ["evt-1", "evt-2"],
                    "primary_sphere": "work",
                    "secondary_sphere": "documents",
                    "polarity": "tense",
                    "evidence_level": "high",
                }
            ],
            "main_event": None,
            "impulses": [],
            "selected_unit_ids": ["evt-1", "evt-2"],
            "selected_spheres": ["work", "documents"],
        },
    }


def test_projection_adds_localized_title_and_null_for_unnameable_unit() -> None:
    snapshot = _snapshot(
        _hero_result(),
        [
            _factor(
                "evt-1",
                source_key="TRANSIT_MOON",
                target_key="NATAL_SATURN",
                target_type="natal_planet",
                aspect_type="square",
            ),
            _factor("evt-2"),
        ],
    )

    payload = project_snapshot_payload(snapshot, None, _access("full"))

    assert payload.events[0].title == "Луна в напряжении с твоим Сатурном"
    assert payload.events[1].title is None


def test_projection_does_not_publish_machine_driver_narrative() -> None:
    snapshot = _snapshot(
        _hero_result(),
        [_factor("evt-1"), _factor("evt-2", event_class="structural")],
    )
    narrative = _hero_narrative(snapshot)
    narrative.content_json["convergences"]["cvg-hero"]["summary"]["text"] = (
        "Transit_Mars и Natal_Moon не должны попасть в ответ."
    )

    payload = project_snapshot_payload(snapshot, narrative, _access("full"))
    serialized = json.dumps(payload.model_dump(mode="json"), ensure_ascii=False)

    assert payload.content_state == "unavailable"
    assert "Transit_Mars" not in serialized
    assert "Natal_Moon" not in serialized


def _quiet_result(*, with_main_and_impulses: bool = True) -> dict[str, Any]:
    return {
        "schema_version": "today-deterministic-result.v1",
        "state": "quiet_day",
        "day_tone": "steady",
        "selected": {
            "convergences": [],
            "main_event": (
                {
                    "event_id": "evt-main",
                    "sphere": "work",
                    "polarity": "supportive",
                    "evidence_level": "medium",
                }
                if with_main_and_impulses
                else None
            ),
            "impulses": (
                [
                    {
                        "event_id": "evt-impulse",
                        "sphere": "documents",
                        "polarity": "mixed",
                        "evidence_level": "medium",
                    }
                ]
                if with_main_and_impulses
                else []
            ),
            "selected_unit_ids": ["evt-main", "evt-impulse"] if with_main_and_impulses else [],
            "selected_spheres": ["work", "documents"] if with_main_and_impulses else [],
        },
    }


def _canonical_input(
    *,
    mode: str = "exact",
    bucket: str | None = None,
    range_start: str = "12:34",
    range_end: str = "12:34",
    exact_timing: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": "today-canonical-input.v1",
        "birth_time": {
            "mode": mode,
            "bucket": bucket,
            "range": {"start": range_start, "end": range_end},
            "capabilities": {
                "houses": exact_timing,
                "angles": exact_timing,
                "lots": exact_timing,
                "exact_timing": exact_timing,
            },
        },
    }


def _snapshot(
    result: dict[str, Any],
    factors: list[dict[str, Any]],
    *,
    snapshot_id: str = "snap-hero-2026-07-31",
    mode: str = "exact",
    bucket: str | None = None,
    range_start: str = "12:34",
    range_end: str = "12:34",
    exact_timing: bool = True,
) -> TodaySnapshot:
    canonical_input = _canonical_input(
        mode=mode,
        bucket=bucket,
        range_start=range_start,
        range_end=range_end,
        exact_timing=exact_timing,
    )
    canonical_input["factor_units"] = copy.deepcopy(factors)
    return TodaySnapshot(
        id=snapshot_id,
        user_id="00000000-0000-0000-0000-000000000001",
        target_date=TARGET_DATE,
        timezone="Europe/Moscow",
        profile_hash="profile-hash",
        input_hash="input-hash",
        canon_hash="canon-hash",
        formula_version="today-convergence-2",
        calculation_version="ss-calc-1.3.0",
        ephemeris_artifact_id="ephemeris-1",
        birth_time_mode=mode,
        birth_time_range={"start": range_start, "end": range_end},
        deterministic_result_json=result,
        canonical_input_json=canonical_input,
        published_at=PUBLISHED_AT,
    )


def _narrative(snapshot: TodaySnapshot, status: str, content: dict[str, Any] | None) -> TodaySnapshotNarrative:
    return TodaySnapshotNarrative(
        id="00000000-0000-0000-0000-000000000002",
        snapshot_id=snapshot.id,
        prompt_version="today-prompt-4",
        status=status,
        content_json=content,
    )


def _hero_narrative(snapshot: TodaySnapshot) -> TodaySnapshotNarrative:
    return _narrative(
        snapshot,
        "ready",
        {
            "convergences": {
                "cvg-hero": {
                    "summary": {
                        "text": "Two independent signals converge on work and documents.",
                        "sourceEventIds": ["evt-1", "evt-2"],
                    }
                }
            }
        },
    )


def _empty_birth_time(*, mode: str = "unknown") -> TodayConvergenceBirthTime:
    if mode == "bucket":
        return TodayConvergenceBirthTime(
            mode="bucket",
            bucket="night",
            range_start="00:00",
            range_end="06:00",
            capabilities={"houses": False, "angles": False, "lots": False, "exact_timing": False},
        )
    return TodayConvergenceBirthTime(
        mode="unknown",
        bucket=None,
        range_start="00:00",
        range_end="24:00",
        capabilities={"houses": False, "angles": False, "lots": False, "exact_timing": False},
    )


def _wire_json(payload: Any) -> str:
    return json.dumps(payload.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":"))


# START_BLOCK: MATRIX
def test_full_hero_ready_projection_matches_frozen_fixture() -> None:
    snapshot = _snapshot(
        _hero_result(),
        [
            _factor("evt-1", source_key="activation-1"),
            _factor(
                "evt-2",
                event_class="structural",
                source_key="activation-2",
                polarity="mixed",
                exact_at="2026-07-31T10:20:00+03:00",
                active_from=None,
                active_until=None,
            ),
        ],
    )

    payload = project_snapshot_payload(snapshot, _hero_narrative(snapshot), _access("full"))
    expected = json.loads(
        (REPO_ROOT / "apps/api/tests/fixtures/contracts/today-convergence-full-hero-ready.json").read_text()
    )

    actual = payload.model_dump(mode="json", by_alias=True)
    # The committed fixture intentionally remains a legacy payload: optional
    # date-aware fields are covered by the dedicated cross-date assertion below.
    for event in actual["events"]:
        for field in ("peakAt", "startAt", "endAt"):
            event["time"].pop(field, None)

    assert actual == expected


def test_exact_event_time_exposes_cross_date_absolute_midpoint_and_bounds() -> None:
    result = _quiet_result(with_main_and_impulses=False) | {
        "selected": {
            "convergences": [],
            "main_event": {
                "event_id": "evt-cross-date",
                "sphere": "work",
                "polarity": "supportive",
                "evidence_level": "medium",
            },
            "impulses": [],
            "selected_unit_ids": ["evt-cross-date"],
            "selected_spheres": ["work"],
        }
    }
    snapshot = _snapshot(
        result,
        [
            _factor(
                "evt-cross-date",
                exact_at=None,
                active_from="2026-07-31T20:30:00+00:00",
                active_until="2026-07-31T22:30:00+00:00",
            )
        ],
        snapshot_id="snap-cross-date-2026-07-31",
    )

    payload = project_snapshot_payload(snapshot, None, _access("full"))
    event_time = payload.events[0].time
    wire_time = event_time.model_dump(mode="json", by_alias=True)

    assert event_time.peak == "00:30"
    assert event_time.start == "23:30"
    assert event_time.end == "01:30"
    assert wire_time["peakAt"] == "2026-08-01T00:30:00+03:00"
    assert wire_time["startAt"] == "2026-07-31T23:30:00+03:00"
    assert wire_time["endAt"] == "2026-08-01T01:30:00+03:00"


@pytest.mark.parametrize(
    ("narrative", "expected_state"),
    [
        (None, "pending"),
        ("pending", "pending"),
        ("unavailable", "unavailable"),
    ],
)
def test_narrative_absent_pending_and_unavailable_matrix(
    narrative: str | None, expected_state: str
) -> None:
    snapshot = _snapshot(_hero_result(), [_factor("evt-1"), _factor("evt-2", event_class="structural")])
    row = None if narrative is None else _narrative(snapshot, narrative, None)

    payload = project_snapshot_payload(snapshot, row, _access("full"))

    assert payload.content_state == expected_state
    assert payload.convergences[0].summary is None
    assert payload.convergences[0].meaning is None
    assert payload.convergences[0].action is None


def test_preview_preserves_deterministic_teaser_and_hides_wire_content() -> None:
    result = _hero_result()
    result["day_tone"] = "supportive"
    snapshot = _snapshot(result, [_factor("evt-1"), _factor("evt-2", event_class="structural")], snapshot_id="snap-preview-2026-07-31")

    payload = project_snapshot_payload(snapshot, _hero_narrative(snapshot), _access("preview"))

    assert payload.access.state == "preview"
    assert payload.state == "convergence_today"
    assert payload.day_tone == "supportive"
    assert payload.preview_teaser is not None
    assert payload.preview_teaser.spheres == ["work", "documents"]
    assert payload.convergences == []
    assert payload.events == []
    assert payload.content_state == "not_needed"


def test_empty_locked_and_unavailable_match_state_matrix() -> None:
    locked = project_empty_payload(
        target_date=TARGET_DATE,
        timezone_name="Europe/Moscow",
        birth_time=_empty_birth_time(),
        access_state=_access("locked"),
        unavailable=False,
    )
    unavailable = project_empty_payload(
        target_date=TARGET_DATE,
        timezone_name="Europe/Moscow",
        birth_time=_empty_birth_time(mode="bucket"),
        access_state=_access("full"),
        unavailable=True,
    )

    assert locked.state is None
    assert locked.content_state == "not_needed"
    assert locked.snapshot_id is None
    assert unavailable.state == "unavailable"
    assert unavailable.content_state == "unavailable"
    assert unavailable.birth_time.mode == "bucket"
    assert unavailable.events == []


def test_quiet_day_projects_main_event_impulse_ledger_and_no_convergence() -> None:
    snapshot = _snapshot(
        _quiet_result(),
        [
            _factor("evt-main", event_class="structural", source_key="main-source"),
            _factor(
                "evt-impulse",
                event_class="activation",
                source_key="impulse-source",
                exact_at="2026-07-31T09:10:00+03:00",
                active_from="2026-07-31T08:00:00+03:00",
                active_until="2026-07-31T10:00:00+03:00",
            ),
        ],
        snapshot_id="snap-quiet-2026-07-31",
    )

    payload = project_snapshot_payload(snapshot, None, _access("full"))

    assert payload.state == "quiet_day"
    assert payload.convergences == []
    assert payload.main_event is not None
    assert [impulse.event_id for impulse in payload.impulses] == ["evt-impulse"]
    assert [event.id for event in payload.events] == ["evt-main", "evt-impulse"]
    assert payload.main_event.id == "mev_v1_evt-main"


def test_bucket_and_unknown_event_times_use_contract_modes() -> None:
    bucket_snapshot = _snapshot(
        _quiet_result(),
        [
            _factor("evt-main", exact_at="2026-07-31T07:10:00+03:00"),
            _factor("evt-impulse", exact_at="2026-07-31T08:10:00+03:00"),
        ],
        mode="bucket",
        bucket="morning",
        range_start="06:00",
        range_end="12:00",
        exact_timing=False,
    )
    unknown_snapshot = _snapshot(
        _quiet_result(with_main_and_impulses=False)
        | {
            "selected": {
                "convergences": [],
                "main_event": {
                    "event_id": "evt-date",
                    "sphere": "work",
                    "polarity": "supportive",
                    "evidence_level": "medium",
                },
                "impulses": [],
                "selected_unit_ids": ["evt-date"],
                "selected_spheres": ["work"],
            }
        },
        [_factor("evt-date", exact_at="2026-07-31", active_from=None, active_until=None)],
        mode="unknown",
        range_start="00:00",
        range_end="24:00",
        exact_timing=False,
    )

    bucket_payload = project_snapshot_payload(bucket_snapshot, None, _access("full"))
    unknown_payload = project_snapshot_payload(unknown_snapshot, None, _access("full"))

    assert bucket_payload.events[0].time.mode == "partofday"
    assert bucket_payload.events[0].time.part_of_day == "morning"
    assert unknown_payload.events[0].time.mode == "date"
    assert unknown_payload.events[0].time.mode == "date"


def test_quiet_without_content_gets_honest_no_strong_accent_context() -> None:
    # START_FUNCTION_CONTRACT: F-TEST.no_strong_accent
    # purpose: Quiet day without mainEvent/impulses yields the versioned
    #   no_strong_accent period context instead of a projection failure.
    # END_FUNCTION_CONTRACT: F-TEST.no_strong_accent
    snapshot = _snapshot(_quiet_result(with_main_and_impulses=False), [])

    full_payload = project_snapshot_payload(snapshot, None, _access("full"))
    preview_payload = project_snapshot_payload(snapshot, None, _access("preview"))

    context = full_payload.period_context
    assert context is not None
    assert context.kind == "no_strong_accent"
    assert context.title
    assert context.sphere is None
    assert context.event_ids == []
    assert full_payload.events == []
    assert full_payload.content_state == "not_needed"
    # Preview keeps every content block hidden (04 §3.2) and stays valid.
    assert preview_payload.period_context is None
    assert preview_payload.preview_teaser is not None


# END_BLOCK: MATRIX


# START_BLOCK: FAIL_CLOSED
def test_invalid_ready_narrative_atomically_falls_back_to_unavailable() -> None:
    snapshot = _snapshot(_hero_result(), [_factor("evt-1"), _factor("evt-2", event_class="structural")])
    narrative = _narrative(
        snapshot,
        "ready",
        {
            "convergences": {
                "cvg-hero": {
                    "summary": {
                        "text": "x" * 221,
                        "sourceEventIds": ["foreign-event"],
                    }
                }
            }
        },
    )

    payload = project_snapshot_payload(snapshot, narrative, _access("full"))

    assert payload.content_state == "unavailable"
    assert all(
        claim is None
        for convergence in payload.convergences
        for claim in (convergence.summary, convergence.meaning, convergence.action)
    )
    assert payload.events[0].id == "evt-1"


def test_foreign_selected_event_reference_is_a_typed_projection_error() -> None:
    result = _hero_result()
    result["selected"]["convergences"][0]["evidence_event_ids"] = ["evt-1", "foreign-event"]
    snapshot = _snapshot(result, [_factor("evt-1"), _factor("evt-2", event_class="structural")])

    with pytest.raises(TodayConvergenceProjectionError, match="today_convergence_projection:"):
        project_snapshot_payload(snapshot, None, _access("full"))


def test_exact_event_without_exact_window_fails_closed() -> None:
    snapshot = _snapshot(
        _quiet_result(),
        [_factor("evt-main", exact_at="2026-07-31", active_from=None, active_until=None)],
    )

    with pytest.raises(TodayConvergenceProjectionError, match="today_convergence_projection:"):
        project_snapshot_payload(snapshot, None, _access("full"))


def test_projection_is_non_mutating_and_byte_deterministic() -> None:
    snapshot = _snapshot(_hero_result(), [_factor("evt-1"), _factor("evt-2", event_class="structural")])
    before_result = copy.deepcopy(snapshot.deterministic_result_json)
    before_input = copy.deepcopy(snapshot.canonical_input_json)

    first = project_snapshot_payload(snapshot, _hero_narrative(snapshot), _access("full"))
    second = project_snapshot_payload(snapshot, _hero_narrative(snapshot), _access("full"))

    assert _wire_json(first) == _wire_json(second)
    assert snapshot.deterministic_result_json == before_result
    assert snapshot.canonical_input_json == before_input


# END_BLOCK: FAIL_CLOSED
