# ############################################################################
# AI_HEADER: TEST_HORIZON_TIMING_SERVICE — B2A timing classification matrix.
# ROLE: Proves pure target-clock timing semantics, preferred horizons, and typed fallback boundaries.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-TIMING-SERVICE
# purpose: Cover date/instant timing parsing, containment, state, eligibility, and error propagation.
# owns:
#   - apps/api/tests/test_horizon_timing_service.py
# inputs: Synthetic ActivationEvidence and explicit target-clock strings.
# outputs: Deterministic timing assessment assertions without server-clock reliance.
# dependencies: pytest, activation schema, horizon timing service.
# side_effects: monkeypatches scoped to individual tests only.
# emitted_logs: none.
# invariants:
#   - ordinary evidence errors return typed ineligible timing assessments.
#   - unexpected programming exceptions propagate.
# failure_policy: test failures identify a timing contract regression.
# END_MODULE_CONTRACT: M-TEST-HORIZON-TIMING-SERVICE

# START_MODULE_MAP: M-TEST-HORIZON-TIMING-SERVICE
# public_entrypoints:
#   - test_date_and_instant_duration_semantics
#   - test_timing_error_and_target_clock_matrix
#   - test_containment_state_and_window_semantics
#   - test_canonical_preferred_horizon_semantics
#   - test_transit_speed_and_programming_error_behavior
#   - test_peak_tolerance_and_transition_boundaries
#   - test_date_precision_peak_state_boundaries
#   - test_unexpected_target_clock_faults_propagate
#   - test_no_server_clock_dependency
# semantic_blocks:
#   - HORIZON_TIMING_TEST_HELPERS: synthetic evidence builder.
#   - HORIZON_TIMING_CLASSIFICATION_TESTS: pure timing state and eligibility assertions.
# owned_tests:
#   - apps/api/tests/test_horizon_timing_service.py
# END_MODULE_MAP: M-TEST-HORIZON-TIMING-SERVICE

# START_BLOCK: HORIZON_TIMING_TEST_HELPERS
from __future__ import annotations

from datetime import datetime

import pytest

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.scoring_v2 import ScoringV2Result
from app.services.horizon_selection_service import HorizonSelectionService
from app.services.horizon_timing_service import HorizonTimingService


def _activation(**overrides: object) -> ActivationEvidence:
    payload = {
        "id": "act-1",
        "technique": "transit_to_natal",
        "technique_family": "transit",
        "target_type": "planet",
        "target_key": "SATURN",
        "kind": "aspect",
        "source_planet": "PLUTO",
        "target_planet": "SATURN",
        "strength": 0.8,
        "evidence": "synthetic evidence",
        "active_from": "2026-01-01T00:00:00Z",
        "exact_at": "2026-07-12T12:00:00Z",
        "active_until": "2026-12-31T00:00:00Z",
    }
    payload.update(overrides)
    return ActivationEvidence(**payload)
# END_BLOCK: HORIZON_TIMING_TEST_HELPERS


# START_BLOCK: HORIZON_TIMING_CLASSIFICATION_TESTS
def test_date_and_instant_duration_semantics() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_date_and_instant_duration_semantics
    # purpose: Prove inclusive dates, leap days, offset equivalence, and target timezone conversion.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on timing duration/clock regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_date_and_instant_duration_semantics
    service = HorizonTimingService()
    date_assessment = service.classify(
        _activation(
            technique="annual_profection",
            technique_family="profection",
            source_planet=None,
            target_planet=None,
            active_from="2028-01-01",
            exact_at="2028-02-29",
            active_until="2028-05-31",
        ),
        target_date="2028-02-29",
        target_time="12:00",
        target_tz="UTC",
    )
    assert date_assessment.precision == "date"
    assert date_assessment.duration_days == 152.0
    assert date_assessment.duration_seconds == 152 * 86400.0
    assert date_assessment.timing_state == "background"
    instant_assessment = service.classify(
        _activation(
            active_from="2026-07-12T10:00:00+02:00",
            exact_at="2026-07-12T12:00:00+02:00",
            active_until="2026-07-12T16:00:00+02:00",
            source_planet="MOON",
        ),
        target_date="2026-07-12",
        target_time="10:00:00",
        target_tz="UTC",
    )
    assert instant_assessment.precision == "instant"
    assert instant_assessment.timing_state == "exact"
    assert instant_assessment.duration_seconds == 6 * 3600.0
    assert instant_assessment.eligible_horizons == ["fast"]
    moscow = service.classify(
        _activation(
            active_from="2026-07-11T23:00:00Z",
            exact_at="2026-07-12T00:00:00Z",
            active_until="2026-07-28T00:00:00Z",
            source_planet="SATURN",
        ),
        target_date="2026-07-12",
        target_time="03:00",
        target_tz="Europe/Moscow",
    )
    assert moscow.relative_position == "inside"
    assert moscow.target_utc == "2026-07-12T00:00:00+00:00"
    assert moscow.eligible_horizons == ["medium"]


@pytest.mark.parametrize(
    ("overrides", "target", "expected_warning"),
    [
        ({"active_from": None, "exact_at": None, "active_until": None}, {}, "missing_timing"),
        ({"active_from": None}, {}, "partial_timing"),
        ({"active_until": None}, {}, "partial_timing"),
        ({"active_from": "2026-01-01", "exact_at": "2026-01-03T00:00:00Z", "active_until": "2026-01-05"}, {}, "mixed_precision"),
        ({"active_from": "bad", "exact_at": None, "active_until": "2026-01-05"}, {}, "invalid_timing"),
        ({"active_from": "2026-01-10", "exact_at": None, "active_until": "2026-01-05"}, {}, "invalid_timing"),
        ({"active_from": "2026-01-01", "exact_at": "2026-02-01", "active_until": "2026-01-05"}, {}, "invalid_timing"),
        ({}, {"target_time": "99:00"}, "invalid_target_clock"),
        ({}, {"target_date": "2026-02-30"}, "invalid_target_clock"),
        ({}, {"target_tz": "Invalid/Timezone"}, "invalid_target_clock"),
    ],
)
def test_timing_error_and_target_clock_matrix(
    overrides: dict[str, object], target: dict[str, str], expected_warning: str
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_timing_error_and_target_clock_matrix
    # purpose: Prove every ordinary malformed timing/target-clock path uses typed ineligible fallback.
    # inputs: overrides - synthetic evidence mutation; target - target clock mutation; expected_warning - typed result code.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if an expected fallback warning is absent.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_timing_error_and_target_clock_matrix
    kwargs = {"target_date": "2026-01-03", "target_time": "12:00", "target_tz": "UTC"}
    kwargs.update(target)
    assessment = HorizonTimingService().classify(_activation(**overrides), **kwargs)
    assert assessment.warning_codes == [expected_warning]
    assert assessment.is_anchor_eligible is False


def test_containment_state_and_window_semantics() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_containment_state_and_window_semantics
    # purpose: Prove inclusive before/start/exact/end/after containment and peak/period/window state rules.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on state or containment regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_containment_state_and_window_semantics
    service = HorizonTimingService()
    before = service.classify(
        _activation(technique="eclipse_window", technique_family="eclipse", source_planet=None, active_from="2026-07-13", exact_at="2026-07-14", active_until="2026-07-20"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    start = service.classify(
        _activation(source_planet="MOON", active_from="2026-07-12T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-13T12:00:00Z"),
        target_date="2026-07-12", target_time="00:00", target_tz="UTC",
    )
    exact = service.classify(
        _activation(source_planet="MOON", active_from="2026-07-12T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-13T12:00:00Z"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    peaked = service.classify(
        _activation(source_planet="MOON", active_from="2026-07-12T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-13T12:00:00Z"),
        target_date="2026-07-12", target_time="18:00", target_tz="UTC",
    )
    end = service.classify(
        _activation(source_planet="MOON", active_from="2026-07-12T00:00:00Z", exact_at="2026-07-12T01:00:00Z", active_until="2026-07-13T12:00:00Z"),
        target_date="2026-07-13", target_time="12:00", target_tz="UTC",
    )
    after = service.classify(
        _activation(source_planet="MOON", active_from="2026-07-01T00:00:00Z", exact_at="2026-07-02T00:00:00Z", active_until="2026-07-03T00:00:00Z"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    period = service.classify(
        _activation(technique="monthly_profection", technique_family="profection", source_planet=None, target_planet=None, active_from="2026-07-01", exact_at=None, active_until="2026-07-31"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    window_without_exact = service.classify(
        _activation(technique="eclipse_window", technique_family="eclipse", source_planet=None, active_from="2026-07-01", exact_at=None, active_until="2026-07-31"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    assert before.relative_position == "before" and before.warning_codes == ["target_before_window"]
    assert start.timing_state == "building"
    assert exact.timing_state == "exact"
    assert peaked.timing_state == "peaked"
    assert end.timing_state == "fading" and end.is_anchor_eligible is True
    assert after.relative_position == "after" and after.warning_codes == ["target_after_window"]
    assert period.timing_state == "active" and period.eligible_horizons == ["medium"]
    assert window_without_exact.timing_state == "active"


def test_canonical_preferred_horizon_semantics() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_canonical_preferred_horizon_semantics
    # purpose: Prove technique preference wins when eligible, otherwise duration preferred-band fallback is canonical.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on preferred horizon ordering/selection regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_canonical_preferred_horizon_semantics
    service = HorizonTimingService()
    slow_transit = service.classify(
        _activation(active_from="2026-01-14T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-13T00:00:00Z", source_planet="PLUTO"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    firdar_long = service.classify(
        _activation(technique="firdar_minor", technique_family="firdar", source_planet=None, target_planet=None, active_from="2026-01-14", exact_at=None, active_until="2026-07-12"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    firdar_medium = service.classify(
        _activation(technique="firdar_minor", technique_family="firdar", source_planet=None, target_planet=None, active_from="2026-06-01", exact_at=None, active_until="2026-07-15"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    assert slow_transit.eligible_horizons == ["long", "medium"]
    assert slow_transit.preferred_horizons == ["medium"]
    assert firdar_long.eligible_horizons == ["long", "medium"]
    assert firdar_long.preferred_horizons == ["long"]
    assert firdar_medium.eligible_horizons == ["medium"]
    assert firdar_medium.preferred_horizons == ["medium"]


def test_peak_tolerance_and_transition_boundaries() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_peak_tolerance_and_transition_boundaries
    # purpose: Prove exact tolerance inclusivity and the exact 12-hour peaked-to-fading transition.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on instant peak state boundary regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_peak_tolerance_and_transition_boundaries
    service = HorizonTimingService()
    tolerance_evidence = _activation(
        source_planet="MOON",
        active_from="2026-07-12T00:00:00Z",
        exact_at="2026-07-12T12:00:00Z",
        active_until="2026-07-13T12:00:00Z",
    )
    states = {
        "11:00:00": "exact",
        "13:00:00": "exact",
        "10:59:59": "building",
        "13:00:01": "peaked",
    }
    for target_time, expected_state in states.items():
        assessment = service.classify(
            tolerance_evidence,
            target_date="2026-07-12",
            target_time=target_time,
            target_tz="UTC",
        )
        assert assessment.timing_state == expected_state

    twelve_hour_tail = _activation(
        source_planet="MOON",
        active_from="2026-07-12T00:00:00Z",
        exact_at="2026-07-12T12:00:00Z",
        active_until="2026-07-13T01:00:00Z",
    )
    at_transition = service.classify(
        twelve_hour_tail,
        target_date="2026-07-13",
        target_time="00:00:00",
        target_tz="UTC",
    )
    after_transition = service.classify(
        twelve_hour_tail,
        target_date="2026-07-13",
        target_time="00:00:01",
        target_tz="UTC",
    )
    assert at_transition.timing_state == "peaked"
    assert after_transition.timing_state == "fading"
    assert at_transition.relative_position == after_transition.relative_position == "inside"


def test_date_precision_peak_state_boundaries() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_date_precision_peak_state_boundaries
    # purpose: Prove date-only peak classification handles building, exact, peaked, and fading states.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure on date precision peak-state regression.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_date_precision_peak_state_boundaries
    evidence = _activation(
        source_planet="MOON",
        active_from="2026-07-01",
        exact_at="2026-07-05",
        active_until="2026-07-09",
    )
    service = HorizonTimingService()
    states = {
        "2026-07-04": "building",
        "2026-07-05": "exact",
        "2026-07-06": "peaked",
        "2026-07-07": "fading",
    }
    for target_date, expected_state in states.items():
        assessment = service.classify(evidence, target_date=target_date, target_time="12:00", target_tz="UTC")
        assert assessment.timing_state == expected_state


def test_unexpected_target_clock_faults_propagate(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_unexpected_target_clock_faults_propagate
    # purpose: Prove target-clock programming faults propagate from timing and selection rather than becoming typed fallback.
    # inputs: monkeypatch - pytest scoped target-clock helper replacement.
    # returns: none.
    # side_effects: temporary module helper patches only.
    # emitted_logs: none.
    # error_behavior: assertion failure if RuntimeError becomes invalid_target_clock.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_unexpected_target_clock_faults_propagate
    import app.services.horizon_selection_service as selection_module
    import app.services.horizon_timing_service as timing_module

    def fail_target_clock(*args: object, **kwargs: object) -> tuple[object, object]:
        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_unexpected_target_clock_faults_propagate.fail_target_clock
        # purpose: Simulate an unexpected internal target-clock helper failure.
        # inputs: args/kwargs - ignored target-clock parser inputs.
        # returns: never.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: always raises RuntimeError.
        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_unexpected_target_clock_faults_propagate.fail_target_clock
        raise RuntimeError("target clock programming fault")

    monkeypatch.setattr(timing_module, "_parse_target_clock", fail_target_clock)
    with pytest.raises(RuntimeError, match="target clock programming fault"):
        HorizonTimingService().classify(_activation(), target_date="2026-07-12", target_time="12:00", target_tz="UTC")

    monkeypatch.setattr(selection_module, "_parse_target_clock", fail_target_clock)
    layer = ActivationLayer(
        calculation_version="calc",
        target_date="2026-07-12",
        target_time="12:00",
        target_tz="UTC",
        house_system="WHOLE_SIGN",
        activations=[],
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    )
    scoring = ScoringV2Result(
        canon_versions={"spheres": "v1"},
        day_status="supportive",
        status_breakdown={},
        sphere_scores={},
        top_signals=[],
        top_activations=[],
    )
    with pytest.raises(RuntimeError, match="target clock programming fault"):
        HorizonSelectionService().select(activation_layer=layer, scoring_result=scoring)


def test_transit_speed_and_programming_error_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_transit_speed_and_programming_error_behavior
    # purpose: Prove all speed groups classify canonically and unexpected helper failure propagates unchanged.
    # inputs: monkeypatch - pytest scoped helper patcher.
    # returns: none.
    # side_effects: temporary module helper patch.
    # emitted_logs: none.
    # error_behavior: assertion failure if programming errors are converted to invalid_timing.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_transit_speed_and_programming_error_behavior
    service = HorizonTimingService()
    fast = service.classify(
        _activation(source_planet="MOON", active_from="2026-07-12T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-12T23:00:00Z"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    medium = service.classify(
        _activation(source_planet="SATURN", active_from="2026-06-25T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-20T00:00:00Z"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    slow = service.classify(
        _activation(source_planet="PLUTO", active_from="2026-01-14T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-13T00:00:00Z"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    unknown = service.classify(_activation(source_planet="CERES"), target_date="2026-07-12", target_time="12:00", target_tz="UTC")
    assert fast.eligible_horizons == ["fast"]
    assert medium.eligible_horizons == ["medium"]
    assert slow.eligible_horizons == ["long", "medium"]
    assert unknown.warning_codes == ["unknown_source_speed"]
    import app.services.horizon_timing_service as module

    def fail_duration(*args: object, **kwargs: object) -> bool:
        # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_transit_speed_and_programming_error_behavior.fail_duration
        # purpose: Simulate an unexpected internal duration helper programming fault.
        # inputs: args/kwargs - ignored helper arguments.
        # returns: never.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: always raises RuntimeError.
        # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_transit_speed_and_programming_error_behavior.fail_duration
        raise RuntimeError("programming fault")

    monkeypatch.setattr(module, "_duration_matches", fail_duration)
    with pytest.raises(RuntimeError, match="programming fault"):
        service.classify(_activation(source_planet="MOON"), target_date="2026-07-12", target_time="12:00", target_tz="UTC")


def test_no_server_clock_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_no_server_clock_dependency
    # purpose: Prove classification relies exclusively on supplied target clock rather than datetime.now.
    # inputs: monkeypatch - pytest scoped replacement helper.
    # returns: none.
    # side_effects: patches module datetime facade for this test.
    # emitted_logs: none.
    # error_behavior: assertion failure if service consults server clock.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.test_no_server_clock_dependency
    import app.services.horizon_timing_service as module

    real_datetime = module.datetime

    class DatetimeShim:
        @staticmethod
        def now(*args: object, **kwargs: object) -> datetime:
            # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.DatetimeShim.now
            # purpose: Fail if tested service reads the server clock.
            # inputs: args/kwargs - ignored datetime parameters.
            # returns: never.
            # side_effects: none.
            # emitted_logs: none.
            # error_behavior: always raises AssertionError.
            # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.DatetimeShim.now
            raise AssertionError("datetime.now must not be called")

        @staticmethod
        def fromisoformat(value: str) -> datetime:
            # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.DatetimeShim.fromisoformat
            # purpose: Preserve required parsing behavior while the server-clock sentinel is installed.
            # inputs: value - RFC3339-compatible instant string.
            # returns: parsed datetime.
            # side_effects: none.
            # emitted_logs: none.
            # error_behavior: delegates datetime parse behavior.
            # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.DatetimeShim.fromisoformat
            return real_datetime.fromisoformat(value)

        @staticmethod
        def combine(*args: object, **kwargs: object) -> datetime:
            # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.DatetimeShim.combine
            # purpose: Preserve target-clock construction while the server-clock sentinel is installed.
            # inputs: args/kwargs - datetime.combine inputs.
            # returns: combined datetime.
            # side_effects: none.
            # emitted_logs: none.
            # error_behavior: delegates datetime combine behavior.
            # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-TIMING-SERVICE.DatetimeShim.combine
            return real_datetime.combine(*args, **kwargs)

    monkeypatch.setattr(module, "datetime", DatetimeShim)
    assessment = HorizonTimingService().classify(
        _activation(source_planet="MOON", active_from="2026-07-12T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-12T23:00:00Z"),
        target_date="2026-07-12", target_time="12:00", target_tz="UTC",
    )
    assert assessment.is_anchor_eligible is True
# END_BLOCK: HORIZON_TIMING_CLASSIFICATION_TESTS
