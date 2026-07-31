# ############################################################################
# AI_HEADER: TEST_TODAY_BIRTH_TIME — strict mode-aware birth-time resolution tests.
# ROLE: Proves frozen birth-time extraction and deterministic calculation plans.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-BIRTH-TIME
# purpose: Validate strict birth-time canon extraction and pure mode-aware resolution.
# owns:
#   - apps/api/tests/test_today_birth_time.py
# inputs: Frozen W1 canon copies and profile-like birth-time values.
# outputs: pytest assertions for canonical grids, capabilities, rejection, and immutability.
# dependencies: app.services.today_convergence_canon and app.services.today_birth_time.
# side_effects: reads canon files and writes only pytest temporary copies.
# emitted_logs: none.
# invariants: no noon fallback, no normalization of persisted modes, and no mutable plan state.
# failure_policy: typed canon/resolver errors fail closed with stable reason tokens.
# END_MODULE_CONTRACT: M-TEST-TODAY-BIRTH-TIME

# START_MODULE_MAP: M-TEST-TODAY-BIRTH-TIME
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - CANON: complete frozen birth-time section and malformed-copy rejection.
#   - RESOLUTION: exact, bucket, unknown, grids, and capabilities.
#   - VALIDATION: invalid state combinations, profile shape, immutability, and source guard.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-BIRTH-TIME

from __future__ import annotations

import shutil
from dataclasses import FrozenInstanceError
from datetime import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from app.services.today_birth_time import (
    BirthTimeResolution,
    TodayBirthTimeError,
    resolve_birth_time,
    resolve_profile_birth_time,
)
from app.services.today_convergence_canon import TodayConvergenceCanonError, load_today_convergence_canon


REPO_ROOT = Path(__file__).resolve().parents[3]
CANON_DIR = REPO_ROOT / "grace" / "canon"
CANON = load_today_convergence_canon()


def copied_canons(tmp_path: Path) -> Path:
    target = tmp_path / "canon"
    target.mkdir()
    for name in (
        "today_convergence.v1.yml",
        "aspect_rules.v1.yml",
        "today_convergence_themes.v1.yml",
    ):
        shutil.copy(CANON_DIR / name, target / name)
    return target


def write_today_copy(target: Path, mutate) -> None:
    path = target / "today_convergence.v1.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mutate(data["birth_time"])
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def profile(*, mode: object, birth_time: object, bucket: object) -> SimpleNamespace:
    return SimpleNamespace(
        birth_time_mode=mode,
        birth_time=birth_time,
        birth_time_bucket=bucket,
    )


# START_BLOCK: CANON
def test_birth_time_canon_exposes_complete_frozen_section() -> None:
    birth = CANON.birth_time

    assert birth.modes == ("exact", "bucket", "unknown")
    assert dict(birth.buckets_local) == {
        "night": (0, 6),
        "morning": (6, 12),
        "day": (12, 18),
        "evening": (18, 24),
    }
    assert dict(birth.control_grid) == {
        "bucket": "edges_plus_middle",
        "unknown": "every_4h_plus_2359",
    }
    assert birth.orb_margin.rule == "canonical_fixed"
    assert dict(birth.orb_margin.gap_hours) == {"bucket": 3, "unknown": 4}
    assert birth.orb_margin.formula == "speed(target_deg_per_hour) * gap_hours / max_orb(source)"
    assert birth.gate == "published_sparse_subset_of_robust_dense"
    assert birth.capabilities["exact"].angles is True
    assert birth.capabilities["bucket"].angles is False
    assert dict(birth.migration) == {"null_birth_time": "unknown", "non_null": "exact"}

    with pytest.raises(TypeError):
        birth.buckets_local["night"] = (0, 7)  # type: ignore[index]
    with pytest.raises(TypeError):
        birth.capabilities["exact"] = birth.capabilities["bucket"]  # type: ignore[index]
    with pytest.raises(TypeError):
        birth.orb_margin.gap_hours["bucket"] = 4  # type: ignore[index]
    with pytest.raises(TypeError):
        birth.migration["non_null"] = "unknown"  # type: ignore[index]


@pytest.mark.parametrize(
    ("mutation", "reason"),
    [
        (lambda birth: birth.pop("modes"), "today_convergence_canon:birth_time_modes"),
        (lambda birth: birth["buckets_local"].update(night=[0, 7]), "today_convergence_canon:birth_time_bucket_ranges"),
        (lambda birth: birth["control_grid"].update(bucket="every_4h_plus_2359"), "today_convergence_canon:birth_time_control_grid"),
        (lambda birth: birth["orb_margin"]["gap_hours"].update(bucket=4), "today_convergence_canon:birth_time_orb_margin_gap_hours"),
        (lambda birth: birth["orb_margin"].update(formula="other"), "today_convergence_canon:birth_time_orb_margin_formula"),
        (lambda birth: birth.update(gate="other"), "today_convergence_canon:birth_time_gate"),
        (lambda birth: birth["capabilities"]["exact"].update(angles=False), "today_convergence_canon:birth_time_capability_value"),
        (lambda birth: birth["migration"].update(non_null="unknown"), "today_convergence_canon:birth_time_migration"),
    ],
)
def test_malformed_birth_time_canon_copy_fails_closed(tmp_path: Path, mutation, reason: str) -> None:
    target = copied_canons(tmp_path)
    write_today_copy(target, mutation)

    with pytest.raises(TodayConvergenceCanonError, match=reason):
        load_today_convergence_canon(target)


# END_BLOCK: CANON


# START_BLOCK: RESOLUTION
def test_exact_time_is_one_point_with_all_capabilities() -> None:
    result = resolve_birth_time(mode="exact", birth_time=time(14, 27), bucket=None, canon=CANON)

    assert isinstance(result, BirthTimeResolution)
    assert result.mode == "exact"
    assert result.bucket is None
    assert result.birth_time == "14:27"
    assert result.range_start == result.range_end == "14:27"
    assert result.control_times == ("14:27",)
    assert result.canonical_gap_hours is None
    assert result.capabilities == CANON.birth_time.capabilities["exact"]
    assert all(vars(result.capabilities).values())


@pytest.mark.parametrize(
    ("bucket", "expected"),
    [
        ("night", ("00:00", "03:00", "05:59")),
        ("morning", ("06:00", "09:00", "11:59")),
        ("day", ("12:00", "15:00", "17:59")),
        ("evening", ("18:00", "21:00", "23:59")),
    ],
)
def test_bucket_derives_exact_w1_control_grid(bucket: str, expected: tuple[str, ...]) -> None:
    result = resolve_birth_time(mode="bucket", birth_time=None, bucket=bucket, canon=CANON)

    assert result.mode == "bucket"
    assert result.bucket == bucket
    assert result.birth_time is None
    assert result.control_times == expected
    assert result.range_start == expected[0]
    assert result.range_end == ("06:00" if bucket == "night" else "12:00" if bucket == "morning" else "18:00" if bucket == "day" else "24:00")
    assert result.canonical_gap_hours == 3
    assert vars(result.capabilities) == {"houses": False, "angles": False, "lots": False, "exact_timing": False}


def test_unknown_derives_canonical_gap_grid_and_no_capabilities() -> None:
    result = resolve_birth_time(mode="unknown", birth_time=None, bucket=None, canon=CANON)

    assert result.mode == "unknown"
    assert result.bucket is None
    assert result.birth_time is None
    assert result.range_start == "00:00"
    assert result.range_end == "24:00"
    assert result.control_times == ("00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:59")
    assert result.canonical_gap_hours == 4
    assert vars(result.capabilities) == {"houses": False, "angles": False, "lots": False, "exact_timing": False}


# END_BLOCK: RESOLUTION


# START_BLOCK: VALIDATION
@pytest.mark.parametrize(
    ("mode", "birth_time", "bucket", "canon", "reason"),
    [
        ("exact", None, None, CANON, "today_birth_time:exact_time_required"),
        ("exact", time(12, 0), "day", CANON, "today_birth_time:exact_bucket_forbidden"),
        ("bucket", time(12, 0), None, CANON, "today_birth_time:bucket_time_forbidden"),
        ("bucket", None, None, CANON, "today_birth_time:invalid_bucket"),
        ("bucket", None, "Night", CANON, "today_birth_time:invalid_bucket"),
        ("unknown", time(12, 0), None, CANON, "today_birth_time:unknown_time_forbidden"),
        ("unknown", None, "night", CANON, "today_birth_time:unknown_bucket_forbidden"),
        ("exact", "12:00", None, CANON, "today_birth_time:exact_time_required"),
        (1, None, None, CANON, "today_birth_time:invalid_mode"),
        ("exact", time(12, 0), None, object(), "today_birth_time:invalid_canon"),
    ],
)
def test_invalid_birth_time_state_fails_before_plan(mode, birth_time, bucket, canon, reason: str) -> None:
    with pytest.raises(TodayBirthTimeError, match=reason):
        resolve_birth_time(mode=mode, birth_time=birth_time, bucket=bucket, canon=canon)


@pytest.mark.parametrize("value", [time(12, 1, 1), time(12, 1, 0, 1)])
def test_exact_seconds_and_microseconds_are_rejected(value: time) -> None:
    with pytest.raises(TodayBirthTimeError, match="today_birth_time:exact_time_precision"):
        resolve_birth_time(mode="exact", birth_time=value, bucket=None, canon=CANON)


def test_profile_resolution_matches_field_resolution_and_missing_attributes_fail() -> None:
    field_result = resolve_birth_time(mode="bucket", birth_time=None, bucket="evening", canon=CANON)
    profile_result = resolve_profile_birth_time(
        profile(mode="bucket", birth_time=None, bucket="evening"), CANON
    )

    assert profile_result == field_result

    with pytest.raises(TodayBirthTimeError, match="today_birth_time:profile_attribute"):
        resolve_profile_birth_time(SimpleNamespace(birth_time_mode="exact"), CANON)


def test_profile_sentinel_check_uses_identity_not_arbitrary_equality() -> None:
    class EqualToEverything:
        def __eq__(self, other: object) -> bool:
            return True

    with pytest.raises(TodayBirthTimeError, match="today_birth_time:invalid_mode"):
        resolve_profile_birth_time(
            profile(mode=EqualToEverything(), birth_time=None, bucket=None),
            CANON,
        )


def test_resolution_is_frozen_has_no_aliases_and_does_not_normalize_input() -> None:
    result = resolve_birth_time(mode="exact", birth_time=time(8, 0), bucket=None, canon=CANON)

    with pytest.raises(FrozenInstanceError):
        result.mode = "unknown"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.capabilities.angles = False  # type: ignore[misc]
    assert not hasattr(result, "control_grid")
    assert not hasattr(result, "birth_time_mode")

    with pytest.raises(TodayBirthTimeError, match="today_birth_time:invalid_mode"):
        resolve_birth_time(mode=" Exact ", birth_time=time(8, 0), bucket=None, canon=CANON)


def test_resolver_source_has_no_analysis_import_or_noon_fallback_expression() -> None:
    source = (REPO_ROOT / "apps/api/app/services/today_birth_time.py").read_text(encoding="utf-8")

    assert "from analysis" not in source
    assert "import analysis" not in source
    assert 'birth_time or "12:00"' not in source
    assert "birth_time or '12:00'" not in source


# END_BLOCK: VALIDATION
