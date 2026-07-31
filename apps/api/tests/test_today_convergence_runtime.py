# ############################################################################
# AI_HEADER: TEST_TODAY-CONVERGENCE-RUNTIME — runtime calculation boundary tests.
# ROLE: Proves strict profile validation, one activation-grid call, typed stage
#       composition, and immutable built/unavailable calculation results.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-RUNTIME
# purpose: Validate the pure runtime boundary between a profile, sidecar grid,
#   robust facts, and the accepted canonical convergence pipeline.
# owns:
#   - apps/api/tests/test_today_convergence_runtime.py
# inputs: Direct profile-like values, typed synthetic activation-grid samples,
#   and injected network clients.
# outputs: pytest assertions for deterministic built/unavailable results.
# dependencies: today_convergence_runtime and its accepted resolver/client/facts/pipeline stages.
# side_effects: none; network is always replaced by an injected fake client.
# emitted_logs: none.
# invariants: one ordered sidecar request, no fallback/retry, safe failure tokens,
#   and frozen result records.
# failure_policy: unexpected programming errors propagate; typed boundary errors
#   become the declared unavailable stage.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-RUNTIME

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-RUNTIME
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - HAPPY_PATH: exact, bucket, unknown grids and built record preservation.
#   - PROFILE_BOUNDARY: dates, coordinates, zones, mode state, and locations.
#   - FAILURE_BOUNDARY: transport, facts, pipeline, and unexpected errors.
#   - IMMUTABILITY: frozen records, exact forwarding, and source guards.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-RUNTIME

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date, datetime, time
from math import nan
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.clients.solarsage_client import ActivationGridSample, SolarSageClientError
from app.core.versions import ACTIVATION_LAYER_VERSION, CALCULATION_VERSION
from app.schemas.activation import ActivationLayer
from app.services import today_convergence_runtime as runtime_module
from app.services.today_birth_time import BirthTimeResolution
from app.services.today_birth_time_facts import BirthTimeFactsAudit, BirthTimeFactsResult, TodayBirthTimeFactsError
from app.services.today_convergence_canon import load_today_convergence_canon
from app.services.today_convergence_pipeline import CanonicalPipelineUnavailable
from app.services.today_convergence_runtime import (
    CANONICAL_TARGET_TIME,
    TodayConvergenceCalculationBuilt,
    TodayConvergenceCalculationUnavailable,
    calculate_today_convergence,
)


TARGET_DATE = date(2026, 7, 31)
CANON = load_today_convergence_canon()


def profile(**overrides):
    values = {
        "birthday": date(1990, 1, 15),
        "birth_time": time(14, 30),
        "birth_time_mode": "exact",
        "birth_time_bucket": None,
        "birth_lat": 55.75,
        "birth_lon": 37.61,
        "birth_tz": "UTC",
        "current_lat": 55.76,
        "current_lon": 37.62,
        "current_tz": "Europe/Moscow",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def empty_layer(target_tz: str = "Europe/Moscow") -> ActivationLayer:
    return ActivationLayer(
        calculation_version=CALCULATION_VERSION,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
        target_date=TARGET_DATE.isoformat(),
        target_time=CANONICAL_TARGET_TIME,
        target_tz=target_tz,
        house_system="PLACIDUS",
        activations=[],
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    )


class FakeGridClient:
    def __init__(self, error: BaseException | None = None):
        self.calls: list[dict] = []
        self.error = error

    async def get_activation_layer_grid(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return tuple(
            ActivationGridSample(birth_time=birth_time, activation_layer=empty_layer(kwargs["target_tz"]))
            for birth_time in kwargs["birth_times"]
        )


def assert_safe_unavailable(result, stage: str) -> None:
    assert isinstance(result, TodayConvergenceCalculationUnavailable)
    assert result.state == "unavailable"
    assert result.failure_stage == stage
    assert result.failure_reason.startswith("today_convergence_runtime:")
    assert "1990" not in result.failure_reason
    assert "55.75" not in result.failure_reason


# START_BLOCK: HAPPY_PATH
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "birth_time", "bucket", "expected_controls"),
    [
        ("exact", time(14, 30), None, ("14:30",)),
        ("bucket", None, "morning", ("06:00", "09:00", "11:59")),
        ("unknown", None, None, ("00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:59")),
    ],
)
async def test_modes_make_one_exact_grid_call_and_built_result(
    mode: str,
    birth_time: time | None,
    bucket: str | None,
    expected_controls: tuple[str, ...],
) -> None:
    client = FakeGridClient()
    result = await calculate_today_convergence(
        profile(birth_time_mode=mode, birth_time=birth_time, birth_time_bucket=bucket),
        TARGET_DATE,
        client=client,
    )

    assert isinstance(result, TodayConvergenceCalculationBuilt)
    assert result.state == "quiet_day"
    assert result.target_date == TARGET_DATE
    assert result.target_timezone == "Europe/Moscow"
    assert result.target_time == "12:00"
    assert result.birth_time.control_times == expected_controls
    assert result.calculation_version == CALCULATION_VERSION
    assert result.activation_layer_version == ACTIVATION_LAYER_VERSION
    assert result.facts_audit.input_sample_count == len(expected_controls)
    assert result.pipeline.state == result.state
    with pytest.raises(FrozenInstanceError):
        result.state = "convergence_today"  # type: ignore[misc]
    assert len(client.calls) == 1
    assert client.calls[0] == {
        "birth_date": "1990-01-15",
        "birth_times": expected_controls,
        "birth_lat": 55.75,
        "birth_lon": 37.61,
        "birth_tz": "UTC",
        "target_date": "2026-07-31",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
        "techniques": None,
        "current_location": {"lat": 55.76, "lon": 37.62, "tz": "Europe/Moscow"},
    }


@pytest.mark.asyncio
async def test_target_timezone_priority_and_partial_current_location() -> None:
    client = FakeGridClient()
    result = await calculate_today_convergence(
        profile(current_tz=None, current_lat=None, current_lon=None), TARGET_DATE, client=client
    )
    assert isinstance(result, TodayConvergenceCalculationBuilt)
    assert result.target_timezone == "UTC"
    assert client.calls[0]["current_location"] is None


@pytest.mark.asyncio
async def test_identical_inputs_with_fresh_clients_produce_equal_records() -> None:
    first = await calculate_today_convergence(profile(), TARGET_DATE, client=FakeGridClient())
    second = await calculate_today_convergence(profile(), TARGET_DATE, client=FakeGridClient())

    assert first == second


@pytest.mark.asyncio
async def test_default_client_is_resolved_once(monkeypatch) -> None:
    client = FakeGridClient()
    resolutions: list[object] = []

    def resolve_client():
        resolutions.append(object())
        return client

    monkeypatch.setattr(runtime_module, "get_solarsage_client", resolve_client)
    result = await calculate_today_convergence(profile(), TARGET_DATE)

    assert isinstance(result, TodayConvergenceCalculationBuilt)
    assert len(resolutions) == 1
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_resolution_and_returned_samples_are_forwarded_to_accepted_stages(monkeypatch) -> None:
    client = FakeGridClient()
    seen: dict[str, object] = {}
    real_resolution = runtime_module.resolve_profile_birth_time(profile(), CANON)
    real_pipeline = runtime_module.run_canonical_today_pipeline
    real_facts = BirthTimeFactsResult(
        facts=(),
        audit=BirthTimeFactsAudit(input_sample_count=1, input_activation_count=0, published_fact_count=0, excluded_by_reason=()),
    )

    def fake_resolve(value, canon=None):
        seen["profile"] = value
        seen["canon"] = canon
        return real_resolution

    def fake_facts(resolution, samples):
        seen["resolution"] = resolution
        seen["samples"] = samples
        return real_facts

    def fake_pipeline(facts, target_date, timezone_name, delta_keys):
        seen["facts"] = facts
        seen["target_date"] = target_date
        seen["timezone"] = timezone_name
        seen["delta_keys"] = delta_keys
        return real_pipeline(facts, target_date, timezone_name, delta_keys, CANON)

    monkeypatch.setattr(runtime_module, "resolve_profile_birth_time", fake_resolve)
    monkeypatch.setattr(runtime_module, "build_birth_time_facts", fake_facts)
    monkeypatch.setattr(runtime_module, "run_canonical_today_pipeline", fake_pipeline)
    delta_keys = ("exact-semantic-key",)

    result = await calculate_today_convergence(profile(), TARGET_DATE, delta_trigger_semantic_keys=delta_keys, client=client)

    assert isinstance(result, TodayConvergenceCalculationBuilt)
    assert seen["resolution"] is real_resolution
    assert seen["samples"] == tuple(
        ActivationGridSample(birth_time=item, activation_layer=empty_layer("Europe/Moscow"))
        for item in ("14:30",)
    )
    assert seen["facts"] is real_facts.facts
    assert seen["delta_keys"] is delta_keys


# END_BLOCK: HAPPY_PATH


# START_BLOCK: PROFILE_BOUNDARY
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation",
    [
        lambda value: value.pop("birthday"),
        lambda value: value.update(birthday=datetime(1990, 1, 15)),
        lambda value: value.update(birth_lat=True),
        lambda value: value.update(birth_lon=nan),
        lambda value: value.update(birth_lat=91.0),
        lambda value: value.update(birth_lon=181.0),
        lambda value: value.update(birth_tz=None),
        lambda value: value.update(birth_tz="Not/AZone"),
        lambda value: value.update(current_tz="Not/AZone"),
        lambda value: value.update(birth_time_mode="bucket", birth_time=None, birth_time_bucket=None),
        lambda value: value.update(birth_time_mode="unknown", birth_time=None, birth_time_bucket="morning"),
    ],
)
async def test_profile_boundary_failures_are_typed_and_do_not_call_sidecar(mutation) -> None:
    values = vars(profile()).copy()
    mutation(values)
    client = FakeGridClient()
    result = await calculate_today_convergence(SimpleNamespace(**values), TARGET_DATE, client=client)

    assert_safe_unavailable(result, "profile")
    assert result.target_timezone is None
    assert result.birth_time is None
    assert result.facts_audit is None
    assert result.pipeline is None
    assert client.calls == []


@pytest.mark.asyncio
async def test_missing_profile_attribute_and_invalid_target_date_fail_closed() -> None:
    client = FakeGridClient()
    values = vars(profile()).copy()
    values.pop("birth_time_mode")
    missing = await calculate_today_convergence(SimpleNamespace(**values), TARGET_DATE, client=client)
    assert_safe_unavailable(missing, "profile")
    assert client.calls == []

    invalid_date = await calculate_today_convergence(profile(), datetime(2026, 7, 31), client=client)  # type: ignore[arg-type]
    assert_safe_unavailable(invalid_date, "profile")
    assert client.calls == []


@pytest.mark.asyncio
async def test_complete_current_location_is_validated_but_partial_location_is_omitted() -> None:
    invalid = await calculate_today_convergence(
        profile(current_lat=55.0, current_lon=37.0, current_tz="Not/AZone"), TARGET_DATE, client=FakeGridClient()
    )
    assert_safe_unavailable(invalid, "profile")

    client = FakeGridClient()
    result = await calculate_today_convergence(
        profile(current_lat=55.0, current_lon=None, current_tz=None), TARGET_DATE, client=client
    )
    assert isinstance(result, TodayConvergenceCalculationBuilt)
    assert client.calls[0]["current_location"] is None


# END_BLOCK: PROFILE_BOUNDARY


# START_BLOCK: FAILURE_BOUNDARY
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [
        SolarSageClientError("secret sidecar body"),
        httpx.TimeoutException("secret timeout"),
        httpx.HTTPStatusError(
            "secret status",
            request=httpx.Request("POST", "https://sidecar.invalid"),
            response=httpx.Response(500, request=httpx.Request("POST", "https://sidecar.invalid")),
        ),
    ],
)
async def test_expected_sidecar_errors_map_to_safe_activation_grid_failure(error) -> None:
    result = await calculate_today_convergence(profile(), TARGET_DATE, client=FakeGridClient(error))
    assert_safe_unavailable(result, "activation_grid")
    assert result.target_timezone == "Europe/Moscow"
    assert result.birth_time is not None
    assert result.facts_audit is None
    assert result.pipeline is None
    assert "secret" not in result.failure_reason


@pytest.mark.asyncio
async def test_unexpected_sidecar_programming_error_propagates() -> None:
    with pytest.raises(RuntimeError, match="programmer bug"):
        await calculate_today_convergence(profile(), TARGET_DATE, client=FakeGridClient(RuntimeError("programmer bug")))


@pytest.mark.asyncio
async def test_typed_facts_failure_and_pipeline_unavailable_preserve_completed_stages(monkeypatch) -> None:
    audit = BirthTimeFactsAudit(input_sample_count=1, input_activation_count=0, published_fact_count=0, excluded_by_reason=())
    facts = BirthTimeFactsResult(facts=(), audit=audit)
    monkeypatch.setattr(runtime_module, "build_birth_time_facts", lambda _resolution, _samples: facts)

    def fail_facts(_resolution, _samples):
        raise TodayBirthTimeFactsError("today_birth_time_facts:invalid_samples")

    monkeypatch.setattr(runtime_module, "build_birth_time_facts", fail_facts)
    failed = await calculate_today_convergence(profile(), TARGET_DATE, client=FakeGridClient())
    assert_safe_unavailable(failed, "facts")
    assert failed.facts_audit is None
    assert failed.pipeline is None

    monkeypatch.setattr(runtime_module, "build_birth_time_facts", lambda _resolution, _samples: facts)
    pipeline = CanonicalPipelineUnavailable(
        formula_version=CANON.formula_version,
        state="unavailable",
        failure_stage="ledger",
        failure_reason="raw_facts must be a sequence",
        ledger=None,
        grouping=None,
        tone=None,
    )
    monkeypatch.setattr(runtime_module, "run_canonical_today_pipeline", lambda *_args: pipeline)
    unavailable = await calculate_today_convergence(profile(), TARGET_DATE, client=FakeGridClient())
    assert_safe_unavailable(unavailable, "pipeline")
    assert unavailable.facts_audit is audit
    assert unavailable.pipeline is pipeline


@pytest.mark.asyncio
async def test_invalid_delta_collection_reaches_pipeline_without_normalization() -> None:
    result = await calculate_today_convergence(
        profile(), TARGET_DATE, delta_trigger_semantic_keys="not-a-sequence", client=FakeGridClient()  # type: ignore[arg-type]
    )
    assert_safe_unavailable(result, "pipeline")
    assert result.pipeline is not None
    assert result.pipeline.failure_stage == "ledger"
    assert result.pipeline.failure_reason == "delta_trigger_semantic_keys must be a sequence"


# END_BLOCK: FAILURE_BOUNDARY


# START_BLOCK: IMMUTABILITY
def test_runtime_public_records_are_frozen_and_have_no_aliases() -> None:
    assert CANONICAL_TARGET_TIME == "12:00"
    assert BirthTimeResolution.__dataclass_params__.frozen is True
    assert not hasattr(TodayConvergenceCalculationBuilt, "result")
    assert not hasattr(TodayConvergenceCalculationUnavailable, "error")


def test_runtime_source_has_no_legacy_or_analysis_imports_or_birth_noon_fallback() -> None:
    source = Path(runtime_module.__file__).read_text(encoding="utf-8")
    assert "analysis" not in source
    assert "today_service" not in source
    assert "scoring" not in source
    assert "normalization" not in source
    assert "birth_time or \"12:00\"" not in source


# END_BLOCK: IMMUTABILITY
