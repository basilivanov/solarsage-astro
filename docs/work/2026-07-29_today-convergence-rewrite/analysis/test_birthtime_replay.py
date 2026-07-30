# ############################################################################
# AI_HEADER: TEST-BIRTHTIME-REPLAY — merge/publication contract tests.
# ROLE: Exercises the fail-closed W1 stability rules without Swiss Ephemeris.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-BIRTHTIME-REPLAY
# purpose: Prove control-point aggregation cannot multiply, invent, or
#   publish unstable evidence.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_birthtime_replay.py
# inputs: small deterministic FactorDay-like fixtures.
# outputs: pytest assertions.
# dependencies: birthtime_replay.
# side_effects: none.
# emitted_logs: none.
# invariants: all tests fail closed on missing points, orb profiles, and
#   birth-time-sensitive targets.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TEST-BIRTHTIME-REPLAY

# START_MODULE_MAP: M-TEST-BIRTHTIME-REPLAY
# public_entrypoints: none
# semantic_blocks:
#   - MERGE_TESTS: identity and stability vectors.
#   - PUBLICATION_TESTS: margins, targets, and roles.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_birthtime_replay.py
# END_MODULE_MAP: M-TEST-BIRTHTIME-REPLAY

from __future__ import annotations

from types import SimpleNamespace

from birthtime_replay import merge_factor_days, published_ids, resolve_merged_day


ORB = {"PLUTO": 8.0, "JUPITER": 8.0, "MOON": 8.0}
TIMES = ("00:00", "03:00", "05:59")


def _factor(**overrides):
    value = {
        "semantic_key": "aspect:PLUTO:trine:natal_planet:SATURN",
        "polarity": "favorable",
        "spheres": ["decisions"],
        "source_planet": "PLUTO",
        "aspect_type": "trine",
        "technique_family": "transit",
        "target_type": "natal_planet",
        "target_key": "SATURN",
        "temporal_role": "supporting",
        "orb": 1.0,
        "strength": 0.9,
    }
    value.update(overrides)
    return value


def _day(date: str, factors, *, trigger=(), sect=True):
    return SimpleNamespace(
        target_date=date,
        factors=tuple(factors),
        trigger_keys=frozenset(trigger),
        raw_activation_count=10,
        raw_ledger_count=10,
        invalid_ledger_count=0,
        duplicate_ledger_count=0,
        timing_deferred_count=0,
        sect_is_day=sect,
    )


def test_merge_deduplicates_same_identity_and_requires_all_points():
    merged = merge_factor_days(
        [_day("2026-01-01", [_factor()]), _day("2026-01-01", [_factor()]), _day("2026-01-01", [_factor()])],
        TIMES,
    )
    assert len(merged["factors"]) == 1
    assert merged["factors"][0]["presence"] == [True, True, True]
    assert len(published_ids([merged["factors"][0]])) == 1

    missing = merge_factor_days(
        [_day("2026-01-01", [_factor()]), _day("2026-01-01", []), _day("2026-01-01", [_factor()])],
        TIMES,
    )
    public, excluded = resolve_merged_day(missing, stratum="night", orb_profile=ORB)
    assert public == []
    assert excluded[0]["exclusion_reason"] == "not_present_at_all_control_points"


def test_margin_and_sensitive_targets_fail_closed():
    # Pluto/Saturn margin is small enough to pass.
    merged = merge_factor_days(
        [_day("2026-01-01", [_factor(orb=1.0)]), _day("2026-01-01", [_factor(orb=1.0)]), _day("2026-01-01", [_factor(orb=1.0)])],
        TIMES,
    )
    public, excluded = resolve_merged_day(merged, stratum="night", orb_profile=ORB)
    assert len(public) == 1
    assert excluded == []

    house = merge_factor_days(
        [_day("2026-01-01", [_factor(target_type="house")]) for _ in TIMES],
        TIMES,
    )
    public, excluded = resolve_merged_day(house, stratum="night", orb_profile=ORB)
    assert public == []
    assert excluded[0]["exclusion_reason"] == "birth_time_sensitive_target"

    missing_orb = merge_factor_days(
        [_day("2026-01-01", [_factor(source_planet="CHIRON")]) for _ in TIMES],
        TIMES,
    )
    public, excluded = resolve_merged_day(missing_orb, stratum="night", orb_profile=ORB)
    assert public == []
    assert excluded[0]["exclusion_reason"] == "orb_profile_missing"


def test_sect_crossing_excludes_firdar_only():
    firdar = _factor(
        semantic_key="firdar:major:SUN",
        aspect_type=None,
        source_planet="SUN",
        technique_family="firdar",
    )
    merged = merge_factor_days(
        [_day("2026-01-01", [firdar], sect=True), _day("2026-01-01", [firdar], sect=False), _day("2026-01-01", [firdar], sect=True)],
        TIMES,
    )
    public, excluded = resolve_merged_day(merged, stratum="night", orb_profile=ORB)
    assert public == []
    assert excluded[0]["exclusion_reason"] == "time_sensitive_sect"
# END_BLOCK: PUBLICATION_TESTS
