# ############################################################################
# AI_HEADER: TEST_TODAY_CONVERGENCE_CONTRACT — strict P1-F wire contract tests.
# ROLE: Proves the new TodayConvergencePayload and its nested validation matrix.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-CONTRACT
# purpose: Validate canonical Today Convergence fixtures and fail-closed invariants.
# owns:
#   - apps/api/tests/test_today_convergence_contract.py
# inputs: JSON fixtures and mutation cases.
# outputs: pytest assertions for the P1-F wire contract.
# dependencies: app.schemas.today_convergence, pydantic.
# side_effects: reads committed fixtures only.
# emitted_logs: none.
# invariants: reason-token assertions remain stable while prose stays implementation-free.
# failure_policy: pytest failure on schema drift or invariant violation.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-CONTRACT

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-CONTRACT
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - FIXTURE_ROUNDTRIP: canonical state fixtures and alias serialization.
#   - ROOT_INVARIANTS: state/access/content/ledger validation.
#   - NESTED_INVARIANTS: birth, event-time, period, and narrative validation.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-CONTRACT

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas.today_convergence import (
    TodayConvergenceEventTime,
    TodayConvergencePayload,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "contracts"
FIXTURES = (
    "today-convergence-full-hero-ready.json",
    "today-convergence-full-quiet-not-needed.json",
    "today-convergence-preview.json",
    "today-convergence-locked.json",
    "today-convergence-unavailable.json",
)


def fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def invalid(payload: dict, token: str) -> None:
    with pytest.raises(ValidationError, match=token):
        TodayConvergencePayload.model_validate(payload)


def test_all_canonical_fixtures_validate_and_round_trip_by_alias() -> None:
    for name in FIXTURES:
        payload = TodayConvergencePayload.model_validate(fixture(name))
        dumped = payload.model_dump(by_alias=True, mode="json")
        assert dumped["schemaVersion"] == 1
        assert TodayConvergencePayload.model_validate(dumped) == payload


@pytest.mark.parametrize("content_state", ["unavailable", "pending"])
def test_full_convergence_preserves_deterministic_payload_without_narratives(content_state: str) -> None:
    payload = fixture("today-convergence-full-hero-ready.json")
    for group in payload["convergences"]:
        group["summary"] = None
        group["meaning"] = None
        group["action"] = None
    payload["contentState"] = content_state

    parsed = TodayConvergencePayload.model_validate(payload)

    assert parsed.state == "convergence_today"
    assert parsed.day_tone == "tense"
    assert [group.id for group in parsed.convergences] == ["cvg-hero"]
    assert [event.id for event in parsed.events] == ["evt-1", "evt-2"]
    assert all(
        narrative is None
        for group in parsed.convergences
        for narrative in (group.summary, group.meaning, group.action)
    )


def test_unavailable_state_is_valid_for_preview_access_without_teaser() -> None:
    payload = fixture("today-convergence-unavailable.json")
    payload["access"].update({
        "state": "preview",
        "reason": "active_referral_days",
        "referralDaysLeft": 2,
        "subscriptionActive": False,
        "accessUntil": "2026-08-02",
    })

    parsed = TodayConvergencePayload.model_validate(payload)

    assert parsed.access.state == "preview"
    assert parsed.state == "unavailable"
    assert parsed.preview_teaser is None


def test_locked_projection_is_empty_and_state_is_null() -> None:
    payload = fixture("today-convergence-locked.json")
    payload["state"] = "quiet_day"
    invalid(payload, "locked_state_null")


def test_unavailable_projection_has_no_snapshot_or_published_content() -> None:
    payload = fixture("today-convergence-unavailable.json")
    payload["snapshotId"] = "snap-forbidden"
    invalid(payload, "unavailable_snapshot_null")


def test_preview_projection_requires_published_teaser_and_not_needed_content() -> None:
    payload = fixture("today-convergence-preview.json")
    payload["contentState"] = "ready"
    invalid(payload, "preview_content_state")

    payload = fixture("today-convergence-preview.json")
    payload["events"] = [{"id": "hidden", "kind": "aspect", "sphere": "work", "polarity": "tense", "evidenceLevel": "high", "time": {"mode": "date", "peak": None, "start": None, "end": None, "partOfDay": None}, "sourceIds": []}]
    invalid(payload, "preview_hidden_events")


def test_full_calculated_state_requires_published_snapshot_and_day_metadata() -> None:
    payload = fixture("today-convergence-full-hero-ready.json")
    payload["snapshotId"] = None
    invalid(payload, "calculated_snapshot_required")


def test_convergence_state_has_groups_only() -> None:
    payload = fixture("today-convergence-full-hero-ready.json")
    payload["convergences"] = []
    invalid(payload, "convergence_group_count")

    payload = fixture("today-convergence-full-hero-ready.json")
    payload["mainEvent"] = {
        "id": "main-1",
        "eventId": "evt-1",
        "sphere": "work",
        "polarity": "tense",
        "evidenceLevel": "high",
        "time": {"mode": "exact", "peak": "15:40", "start": None, "end": None, "partOfDay": None},
        "summary": None,
        "meaning": None,
        "action": None,
    }
    invalid(payload, "convergence_main_event_forbidden")


def test_quiet_state_requires_content_and_excludes_main_event_and_impulses_together() -> None:
    payload = fixture("today-convergence-full-quiet-not-needed.json")
    payload["periodContext"] = None
    invalid(payload, "quiet_content_required")

    payload = fixture("today-convergence-full-quiet-not-needed.json")
    payload["events"] = [{"id": "evt-quiet", "kind": "aspect", "sphere": "work", "polarity": "supportive", "evidenceLevel": "medium", "time": {"mode": "partofday", "peak": None, "start": None, "end": None, "partOfDay": "day"}, "sourceIds": []}]
    payload["mainEvent"] = {
        "id": "main-quiet",
        "eventId": "evt-quiet",
        "sphere": "work",
        "polarity": "supportive",
        "evidenceLevel": "medium",
        "time": {"mode": "partofday", "peak": None, "start": None, "end": None, "partOfDay": "day"},
        "summary": None,
        "meaning": None,
        "action": None,
    }
    payload["impulses"] = [{
        "eventId": "evt-quiet",
        "sphere": "work",
        "polarity": "supportive",
        "evidenceLevel": "medium",
        "time": {"mode": "partofday", "peak": None, "start": None, "end": None, "partOfDay": "day"},
        "summary": None,
        "meaning": None,
        "action": None,
    }]
    payload["periodContext"] = None
    invalid(payload, "quiet_main_impulses_exclusive")


def test_content_without_narrative_is_fail_closed() -> None:
    payload = fixture("today-convergence-full-quiet-not-needed.json")
    payload["contentState"] = "pending"
    payload["periodContext"] = None
    payload["events"] = [{"id": "evt-quiet", "kind": "aspect", "sphere": "work", "polarity": "supportive", "evidenceLevel": "medium", "time": {"mode": "partofday", "peak": None, "start": None, "end": None, "partOfDay": "day"}, "sourceIds": []}]
    payload["mainEvent"] = {
        "id": "main-quiet",
        "eventId": "evt-quiet",
        "sphere": "work",
        "polarity": "supportive",
        "evidenceLevel": "medium",
        "time": {"mode": "partofday", "peak": None, "start": None, "end": None, "partOfDay": "day"},
        "summary": {"text": "not allowed", "sourceEventIds": ["evt-quiet"]},
        "meaning": None,
        "action": None,
    }
    invalid(payload, "narrative_content_state")


def test_event_ledger_rejects_dangling_and_unused_ids() -> None:
    payload = fixture("today-convergence-full-hero-ready.json")
    payload["events"].pop()
    invalid(payload, "event_reference_missing")

    payload = fixture("today-convergence-full-hero-ready.json")
    payload["events"].append(copy.deepcopy(payload["events"][0]))
    payload["events"][-1]["id"] = "unused"
    invalid(payload, "event_ledger_mismatch")


def test_narrative_sources_must_reference_selected_events() -> None:
    payload = fixture("today-convergence-full-hero-ready.json")
    payload["convergences"][0]["summary"]["sourceEventIds"] = ["unknown"]
    invalid(payload, "narrative_source_event_unknown")


def test_sphere_projection_is_closed_and_capped() -> None:
    payload = fixture("today-convergence-full-hero-ready.json")
    payload["convergences"][0]["secondarySphere"] = "work"
    invalid(payload, "group_sphere_distinct")

    payload = fixture("today-convergence-full-hero-ready.json")
    payload["events"].extend([
        {"id": "evt-3", "kind": "aspect", "sphere": "documents", "polarity": "tense", "evidenceLevel": "high", "time": {"mode": "exact", "peak": "16:00", "start": None, "end": None, "partOfDay": None}, "sourceIds": []},
        {"id": "evt-4", "kind": "aspect", "sphere": "relationships", "polarity": "tense", "evidenceLevel": "high", "time": {"mode": "exact", "peak": "17:00", "start": None, "end": None, "partOfDay": None}, "sourceIds": []},
    ])
    payload["convergences"].append({
        "id": "cvg-2",
        "primarySphere": "money",
        "secondarySphere": "relationships",
        "polarity": "tense",
        "evidenceLevel": "high",
        "eventIds": ["evt-3", "evt-4"],
        "summary": None,
        "meaning": None,
        "action": None,
    })
    invalid(payload, "sphere_union_cap")


def test_birth_time_modes_and_capabilities_are_canonical() -> None:
    for name, mode in (
        ("today-convergence-full-hero-ready.json", "exact"),
        ("today-convergence-unavailable.json", "bucket"),
        ("today-convergence-locked.json", "unknown"),
    ):
        assert TodayConvergencePayload.model_validate(fixture(name)).birth_time.mode == mode

    payload = fixture("today-convergence-full-hero-ready.json")
    payload["birthTime"]["rangeEnd"] = "13:00"
    invalid(payload, "birth_exact_range")

    payload = fixture("today-convergence-unavailable.json")
    payload["birthTime"]["capabilities"]["houses"] = True
    invalid(payload, "birth_bucket_capabilities")

    payload = fixture("today-convergence-locked.json")
    payload["birthTime"]["rangeEnd"] = "23:59"
    invalid(payload, "birth_unknown_range")

    payload = fixture("today-convergence-unavailable.json")
    payload["birthTime"]["bucket"] = "not-a-bucket"
    invalid(payload, "literal_error")


def test_event_time_modes_and_birth_precision_are_restricted() -> None:
    with pytest.raises(ValidationError, match="event_time_exact_part_of_day"):
        TodayConvergenceEventTime.model_validate({"mode": "exact", "peak": "12:00", "start": None, "end": None, "partOfDay": "day"})
    with pytest.raises(ValidationError, match="event_time_partofday_clock"):
        TodayConvergenceEventTime.model_validate({"mode": "partofday", "peak": "12:00", "start": None, "end": None, "partOfDay": "day"})
    with pytest.raises(ValidationError, match="event_time_date_fields"):
        TodayConvergenceEventTime.model_validate({"mode": "date", "peak": "12:00", "start": None, "end": None, "partOfDay": None})
    with pytest.raises(ValidationError, match="event_time_clock_format"):
        TodayConvergenceEventTime.model_validate({"mode": "exact", "peak": "24:00", "start": None, "end": None, "partOfDay": None})

    payload = fixture("today-convergence-unavailable.json")
    payload["events"] = [{"id": "evt-bucket", "kind": "aspect", "sphere": "work", "polarity": "tense", "evidenceLevel": "high", "time": {"mode": "exact", "peak": "12:00", "start": None, "end": None, "partOfDay": None}, "sourceIds": []}]
    payload["periodContext"] = {"id": "period-1", "kind": "active_period", "sphere": "work", "title": "Period", "activeFrom": "2026-07-01", "activeUntil": "2026-08-01", "eventIds": ["evt-bucket"]}
    payload["state"] = "quiet_day"
    payload["dayTone"] = "steady"
    payload["personal"] = True
    payload["snapshotId"] = "snap-bucket"
    payload["publishedAt"] = "2026-07-31T00:00:00Z"
    payload["contentState"] = "not_needed"
    invalid(payload, "birth_event_time_precision")


def test_period_context_modes_are_deterministic() -> None:
    payload = fixture("today-convergence-full-quiet-not-needed.json")
    payload["periodContext"]["sphere"] = "work"
    invalid(payload, "no_strong_accent_fields")

    payload = fixture("today-convergence-full-quiet-not-needed.json")
    payload["periodContext"] = {"id": "period-1", "kind": "active_period", "sphere": None, "title": None, "activeFrom": None, "activeUntil": None, "eventIds": []}
    invalid(payload, "active_period_fields")


def test_unknown_fields_and_legacy_today_fields_are_rejected() -> None:
    payload = fixture("today-convergence-locked.json")
    payload["futureField"] = True
    invalid(payload, "extra_field_rejected")

    for legacy in ("dayStatus", "focus", "v2"):
        payload = fixture("today-convergence-locked.json")
        payload[legacy] = {}
        invalid(payload, "legacy_field_rejected")


def test_invalid_iana_timezone_is_rejected() -> None:
    payload = fixture("today-convergence-locked.json")
    payload["timezone"] = "Mars/Olympus"
    invalid(payload, "timezone_invalid")


def test_summary_limit_duplicate_ids_and_duplicate_sources_are_rejected() -> None:
    payload = fixture("today-convergence-full-hero-ready.json")
    payload["convergences"][0]["summary"]["text"] = "x" * 221
    invalid(payload, "summary_text_too_long")

    payload = fixture("today-convergence-full-hero-ready.json")
    payload["convergences"][0]["eventIds"] = ["evt-1", "evt-1"]
    invalid(payload, "duplicate_id")

    payload = fixture("today-convergence-full-hero-ready.json")
    payload["convergences"].append(copy.deepcopy(payload["convergences"][0]))
    invalid(payload, "duplicate_id")

    payload = fixture("today-convergence-full-hero-ready.json")
    payload["convergences"][0]["summary"]["sourceEventIds"] = ["evt-1", "evt-1"]
    invalid(payload, "duplicate_id")
