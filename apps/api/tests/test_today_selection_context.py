# ############################################################################
# AI_HEADER: TEST_TODAY_SELECTION_CONTEXT — W1 pure selection/cache foundation.
# ROLE: Proves immutable request selection, runtime isolation, and cache parity.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SELECTION-CONTEXT
# purpose: Verify the complete W1 selection truth tables, runtime error policy,
#          real concurrent independence, explicit cache authority, and guards.
# owns:
#   - apps/api/tests/test_today_selection_context.py
# inputs: deterministic fake V1/V2 services and monkeypatched rollout flags.
# outputs: executable evidence for request-scoped selection and cache identity.
# dependencies: pytest, Python concurrency/inspection helpers, W1 service modules.
# side_effects: starts two bounded worker threads in the concurrency proof.
# emitted_logs: none.
# invariants:
#   - Tests do not depend on astrological scoring data or raw sleeps.
#   - Global settings are restored by pytest monkeypatch fixtures.
# failure_policy: assertion failure on selection, isolation, parity, or guard drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-SELECTION-CONTEXT

# START_MODULE_MAP: M-TEST-TODAY-SELECTION-CONTEXT
# public_entrypoints:
#   - pytest test cases in this module
# semantic_blocks:
#   - TEST_SUPPORT: deterministic thread-safe scoring fakes and key builder.
#   - PURE_CONTEXT: enum, resolver, immutability, and ambient-state tests.
#   - FLAG_HELPERS: selected/compute truth tables and default compatibility.
#   - RUNTIME_SELECTION: runtime result and failure-policy tests.
#   - CONCURRENT_INDEPENDENCE: real overlapping request selection proof.
#   - CACHE_AUTHORITY: explicit/default identity and read/write parity tests.
#   - STATIC_GUARDS: source and signature constraints for the W1 implementation.
# owned_tests:
#   - apps/api/tests/test_today_selection_context.py
# END_MODULE_MAP: M-TEST-TODAY-SELECTION-CONTEXT

from __future__ import annotations

import ast
import inspect
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from threading import Barrier, Lock
from types import SimpleNamespace
from typing import Any, Iterator
from uuid import UUID, uuid4

import pytest

from app.core.config import settings
from app.core.versions import (
    ACTIVATION_LAYER_VERSION,
    CALCULATION_VERSION,
    LEGACY_CALCULATION_VERSION,
    LEGACY_FRONTEND_PAYLOAD_VERSION,
    LEGACY_SCORING_VERSION,
    SCORING_V2_VERSION,
    TODAY_CONTENT_VERSION,
    TODAY_V1_PAYLOAD_VERSION,
    TODAY_V2_PAYLOAD_VERSION,
    V2_FRONTEND_PAYLOAD_VERSION,
)
from app.services import day_scoring_runtime_service as runtime_module
from app.services import cache_key_service as cache_key_module
from app.services.cache_key_service import (
    TodayCacheKey,
    build_today_cache_key,
    expected_cache_identity,
    resolve_today_runtime_identity,
)
from app.services.day_scoring_runtime_service import (
    DayScoringRuntimeService,
    selected_scoring_version_for_flags,
    should_compute_v2,
)
from app.services.today_selection_context import (
    TodaySelectionContext,
    TodaySelectionSource,
    resolve_today_selection_context,
)


# START_BLOCK: TEST_SUPPORT
class _FakeV1Service:
    """Thread-safe deterministic V1 scoring fake."""

    def __init__(self, *, overlap_barrier: Barrier | None = None) -> None:
        self._lock = Lock()
        self._overlap_barrier = overlap_barrier
        self.calls = 0
        self.flag_snapshots: list[tuple[bool, bool]] = []

    def score_day(self, day_signals: list[Any]) -> dict[str, Any]:
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.FakeV1Service.score_day
        # purpose: Return deterministic V1 output while recording calls, global flag snapshots, and optional overlap.
        # inputs: self — configured fake; day_signals — ignored scoring inputs.
        # returns: deterministic V1 scoring dictionary.
        # side_effects: records synchronized call state and may wait on a bounded thread barrier.
        # emitted_logs: none.
        # error_behavior: propagates a broken or timed-out overlap barrier error.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.FakeV1Service.score_day
        del day_signals
        with self._lock:
            self.calls += 1
            self.flag_snapshots.append(
                (
                    bool(settings.solarsage_v2_enabled),
                    bool(settings.solarsage_v2_dual_run),
                )
            )
        if self._overlap_barrier is not None:
            self._overlap_barrier.wait(timeout=5)
        with self._lock:
            self.flag_snapshots.append(
                (
                    bool(settings.solarsage_v2_enabled),
                    bool(settings.solarsage_v2_dual_run),
                )
            )
        return {
            "day_status": "v1_status",
            "sphere_scores": {"focus": 1.0},
            "top_signals": [{"id": "v1"}],
        }

class _FakeV2Service:
    """Thread-safe deterministic V2 scoring fake with configurable failure."""

    def __init__(self, *, error: Exception | None = None) -> None:
        self._lock = Lock()
        self._error = error
        self.calls = 0

    def score_day(self, day_signals: list[Any], activation_layer: Any) -> Any:
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.FakeV2Service.score_day
        # purpose: Return deterministic V2 output or raise the configured failure after recording the call.
        # inputs: self — configured fake; day_signals and activation_layer — ignored scoring inputs.
        # returns: deterministic namespace-shaped V2 scoring result when no error is configured.
        # side_effects: increments the synchronized call count.
        # emitted_logs: none.
        # error_behavior: raises the exact configured exception when present.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.FakeV2Service.score_day
        del day_signals, activation_layer
        with self._lock:
            self.calls += 1
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            day_status="v2_status",
            sphere_scores={
                "focus": SimpleNamespace(final_score=2.5, contributions=[]),
            },
            top_signals=[{"id": "v2"}],
        )

@contextmanager
def _silent_log_block(**kwargs: Any) -> Iterator[None]:
    del kwargs
    yield

def _install_fake_scoring(
    monkeypatch: pytest.MonkeyPatch,
    *,
    v1_service: _FakeV1Service | None = None,
    v2_service: _FakeV2Service | None = None,
) -> tuple[_FakeV1Service, _FakeV2Service]:
    v1 = v1_service or _FakeV1Service()
    v2 = v2_service or _FakeV2Service()
    monkeypatch.setattr(runtime_module, "ScoringService", lambda: v1)
    monkeypatch.setattr(runtime_module, "ScoringV2Service", lambda: v2)
    monkeypatch.setattr(runtime_module, "log_block", _silent_log_block)
    monkeypatch.setattr(runtime_module, "log_event", lambda *args, **kwargs: None)
    return v1, v2

def _write_key_for_selected_version(
    *,
    user_id: UUID,
    target_date: str,
    profile_hash: str,
    selected_scoring_version: int | str,
) -> TodayCacheKey:
    identity = resolve_today_runtime_identity(
        selected_scoring_version=selected_scoring_version,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
    )
    return build_today_cache_key(
        user_id=user_id,
        target_date=target_date,
        profile_hash=profile_hash,
        calculation_version=identity.calculation_version,
        activation_layer_version=identity.activation_layer_version,
        scoring_version=identity.scoring_version,
        content_version=identity.content_version,
        frontend_payload_version=identity.frontend_payload_version,
    )
# END_BLOCK: TEST_SUPPORT

# START_BLOCK: PURE_CONTEXT
def test_selection_source_has_exact_closed_values() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selection_source_has_exact_closed_values
    # purpose: Verify the selection-source enum exposes exactly the two approved name/value pairs.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if the enum gains, loses, renames, or revalues a member.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selection_source_has_exact_closed_values
    assert [(source.name, source.value) for source in TodaySelectionSource] == [
        ("GLOBAL_FLAGS", "global_flags"),
        ("LOCAL_DEV_PREVIEW", "local_dev_preview"),
    ]

@pytest.mark.parametrize(
    ("preview_authorized", "global_v2_enabled", "force_v2", "source"),
    [
        (False, False, False, TodaySelectionSource.GLOBAL_FLAGS),
        (False, True, True, TodaySelectionSource.GLOBAL_FLAGS),
        (True, False, True, TodaySelectionSource.LOCAL_DEV_PREVIEW),
        (True, True, True, TodaySelectionSource.LOCAL_DEV_PREVIEW),
    ],
)
def test_resolver_exact_truth_table(
    preview_authorized: bool,
    global_v2_enabled: bool,
    force_v2: bool,
    source: TodaySelectionSource,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_resolver_exact_truth_table
    # purpose: Verify every authorized-preview/global-flag row resolves to the exact immutable context.
    # inputs: preview_authorized, global_v2_enabled, force_v2, and source — parametrized truth-table values.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if any resolver truth-table row differs.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_resolver_exact_truth_table
    assert resolve_today_selection_context(
        global_v2_enabled=global_v2_enabled,
        preview_authorized=preview_authorized,
    ) == TodaySelectionContext(force_v2=force_v2, source=source)

def test_preview_source_precedes_global_source_when_both_true() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_preview_source_precedes_global_source_when_both_true
    # purpose: Verify authorized local preview is the recorded source when preview and global V2 are both enabled.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if source precedence or forced selection changes.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_preview_source_precedes_global_source_when_both_true
    context = resolve_today_selection_context(
        global_v2_enabled=True,
        preview_authorized=True,
    )
    assert context.source is TodaySelectionSource.LOCAL_DEV_PREVIEW
    assert context.force_v2 is True

def test_selection_context_is_frozen() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selection_context_is_frozen
    # purpose: Verify callers cannot mutate force_v2 on an established selection context.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: expects FrozenInstanceError; assertion failure if mutation becomes possible.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selection_context_is_frozen
    context = TodaySelectionContext(
        force_v2=False,
        source=TodaySelectionSource.GLOBAL_FLAGS,
    )
    with pytest.raises(FrozenInstanceError):
        context.force_v2 = True

def test_selection_context_uses_slots_without_instance_dict() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selection_context_uses_slots_without_instance_dict
    # purpose: Verify selection contexts use slots and expose only force_v2 and source storage.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if instance dictionaries appear or slot names drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selection_context_uses_slots_without_instance_dict
    context = TodaySelectionContext(
        force_v2=False,
        source=TodaySelectionSource.GLOBAL_FLAGS,
    )
    assert not hasattr(context, "__dict__")
    assert set(TodaySelectionContext.__slots__) == {"force_v2", "source"}

def test_selection_context_has_exact_safe_field_set() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selection_context_has_exact_safe_field_set
    # purpose: Verify the immutable context contains no request data beyond force_v2 and source.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if the dataclass field set changes.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selection_context_has_exact_safe_field_set
    assert {field.name for field in fields(TodaySelectionContext)} == {
        "force_v2",
        "source",
    }

def test_resolver_module_has_no_global_settings_dependency() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_resolver_module_has_no_global_settings_dependency
    # purpose: Verify the pure resolver module neither imports nor references global settings.
    # inputs: none.
    # returns: none.
    # side_effects: reads and parses the resolver source file.
    # emitted_logs: none.
    # error_behavior: assertion failure if an ambient settings dependency is found; propagates read or parse errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_resolver_module_has_no_global_settings_dependency
    module_path = Path(__file__).resolve().parents[1] / "app/services/today_selection_context.py"
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module == "app.core.config"
        and any(alias.name == "settings" for alias in node.names)
        for node in ast.walk(tree)
    )
    assert not any(isinstance(node, ast.Name) and node.id == "settings" for node in ast.walk(tree))
# END_BLOCK: PURE_CONTEXT

# START_BLOCK: FLAG_HELPERS
def test_selected_helper_default_is_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_default_is_v1
    # purpose: Verify the default selected scoring family is V1 when the global V2 flag is disabled.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled for the test scope.
    # emitted_logs: none.
    # error_behavior: assertion failure if default selection is not legacy V1.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_default_is_v1
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    assert selected_scoring_version_for_flags() == LEGACY_SCORING_VERSION

def test_selected_helper_global_enabled_is_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_global_enabled_is_v2
    # purpose: Verify the global V2 flag selects the V2 scoring family.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled for the test scope.
    # emitted_logs: none.
    # error_behavior: assertion failure if global enablement does not select V2.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_global_enabled_is_v2
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    assert selected_scoring_version_for_flags() == SCORING_V2_VERSION

def test_selected_helper_force_true_global_false_is_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_force_true_global_false_is_v2
    # purpose: Verify request-scoped force_v2 selects V2 while global V2 is disabled.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled for the test scope.
    # emitted_logs: none.
    # error_behavior: assertion failure if force_v2 does not select V2.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_force_true_global_false_is_v2
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    assert selected_scoring_version_for_flags(force_v2=True) == SCORING_V2_VERSION

def test_selected_helper_force_false_does_not_disable_global_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_force_false_does_not_disable_global_v2
    # purpose: Verify explicit force_v2=False does not override an enabled global V2 selection.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled for the test scope.
    # emitted_logs: none.
    # error_behavior: assertion failure if force_v2=False suppresses global V2.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_force_false_does_not_disable_global_v2
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    assert selected_scoring_version_for_flags(force_v2=False) == SCORING_V2_VERSION

def test_selected_helper_force_true_with_global_true_is_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_force_true_with_global_true_is_v2
    # purpose: Verify force_v2 and global V2 enablement together retain V2 selection.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled for the test scope.
    # emitted_logs: none.
    # error_behavior: assertion failure if the combined enabled state does not select V2.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_selected_helper_force_true_with_global_true_is_v2
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    assert selected_scoring_version_for_flags(force_v2=True) == SCORING_V2_VERSION

@pytest.mark.parametrize(
    ("global_enabled", "dual_run", "force_v2", "expected"),
    [
        (False, False, False, False),
        (False, False, True, True),
        (False, True, False, True),
        (False, True, True, True),
        (True, False, False, True),
        (True, False, True, True),
        (True, True, False, True),
        (True, True, True, True),
    ],
)
def test_compute_helper_exact_eight_row_matrix(
    monkeypatch: pytest.MonkeyPatch,
    global_enabled: bool,
    dual_run: bool,
    force_v2: bool,
    expected: bool,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_compute_helper_exact_eight_row_matrix
    # purpose: Verify V2 computation follows the complete global, dual-run, and request-force truth table.
    # inputs: monkeypatch plus parametrized global_enabled, dual_run, force_v2, and expected values.
    # returns: none.
    # side_effects: monkeypatches global V2 enabled and dual-run settings for each row.
    # emitted_logs: none.
    # error_behavior: assertion failure if any of the eight computation rows differs.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_compute_helper_exact_eight_row_matrix
    monkeypatch.setattr(settings, "solarsage_v2_enabled", global_enabled)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", dual_run)
    assert should_compute_v2(force_v2=force_v2) is expected

def test_dual_run_alone_computes_but_does_not_select_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_dual_run_alone_computes_but_does_not_select_v2
    # purpose: Verify shadow dual-run computes V2 without making V2 the selected response family.
    # inputs: monkeypatch — pytest fixture for global V2 and dual-run flags.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled and solarsage_v2_dual_run.
    # emitted_logs: none.
    # error_behavior: assertion failure if dual-run computation changes selected scoring authority.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_dual_run_alone_computes_but_does_not_select_v2
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    assert should_compute_v2() is True
    assert selected_scoring_version_for_flags() == LEGACY_SCORING_VERSION
# END_BLOCK: FLAG_HELPERS

# START_BLOCK: RUNTIME_SELECTION
def test_runtime_default_v1_does_not_call_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_default_v1_does_not_call_v2
    # purpose: Verify default runtime execution calls only V1 and returns its result as selected.
    # inputs: monkeypatch — pytest fixture used to install deterministic scoring fakes.
    # returns: none.
    # side_effects: monkeypatches runtime scoring services and logging functions.
    # emitted_logs: none.
    # error_behavior: assertion failure if V2 is called or the selected V1 result drifts.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_default_v1_does_not_call_v2
    v1, v2 = _install_fake_scoring(monkeypatch)
    result = DayScoringRuntimeService().compute([])
    assert v1.calls == 1
    assert v2.calls == 0
    assert result.selected_scoring_version == LEGACY_SCORING_VERSION
    assert result.selected_result is result.v1_result

def test_runtime_dual_run_calls_v2_but_selects_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_dual_run_calls_v2_but_selects_v1
    # purpose: Verify dual-run computes and diffs V2 while retaining V1 as the selected runtime result.
    # inputs: monkeypatch — pytest fixture for dual-run and deterministic scoring fakes.
    # returns: none.
    # side_effects: monkeypatches the dual-run setting, runtime scoring services, and logging functions.
    # emitted_logs: none.
    # error_behavior: assertion failure if shadow V2 is skipped, undiffed, or selected.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_dual_run_calls_v2_but_selects_v1
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    _, v2 = _install_fake_scoring(monkeypatch)
    result = DayScoringRuntimeService().compute([])
    assert v2.calls == 1
    assert result.v2_result is not None
    assert result.diff is not None
    assert result.selected_scoring_version == LEGACY_SCORING_VERSION
    assert result.selected_result is result.v1_result

def test_runtime_force_v2_with_globals_off_calls_and_selects_v2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_force_v2_with_globals_off_calls_and_selects_v2
    # purpose: Verify request force computes and selects V2 when global rollout flags remain off.
    # inputs: monkeypatch — pytest fixture used to install deterministic scoring fakes.
    # returns: none.
    # side_effects: monkeypatches runtime scoring services and logging functions.
    # emitted_logs: none.
    # error_behavior: assertion failure if forced runtime selection does not return V2.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_force_v2_with_globals_off_calls_and_selects_v2
    _, v2 = _install_fake_scoring(monkeypatch)
    result = DayScoringRuntimeService().compute([], force_v2=True)
    assert v2.calls == 1
    assert result.selected_scoring_version == SCORING_V2_VERSION
    assert result.selected_result["day_status"] == "v2_status"

def test_runtime_global_v2_selects_v2_with_force_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_global_v2_selects_v2_with_force_false
    # purpose: Verify an enabled global rollout still selects V2 when request force_v2 is false.
    # inputs: monkeypatch — pytest fixture for global V2 and deterministic scoring fakes.
    # returns: none.
    # side_effects: monkeypatches global V2, runtime scoring services, and logging functions.
    # emitted_logs: none.
    # error_behavior: assertion failure if global V2 is not computed and selected.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_global_v2_selects_v2_with_force_false
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    _, v2 = _install_fake_scoring(monkeypatch)
    result = DayScoringRuntimeService().compute([], force_v2=False)
    assert v2.calls == 1
    assert result.selected_scoring_version == SCORING_V2_VERSION

def test_runtime_force_selected_v2_error_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_force_selected_v2_error_reraises
    # purpose: Verify a failure in request-selected V2 is propagated instead of shadowed.
    # inputs: monkeypatch — pytest fixture used to install a failing V2 fake.
    # returns: none.
    # side_effects: monkeypatches runtime scoring services and logging functions.
    # emitted_logs: none.
    # error_behavior: expects the exact configured RuntimeError from forced V2.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_force_selected_v2_error_reraises
    _install_fake_scoring(
        monkeypatch,
        v2_service=_FakeV2Service(error=RuntimeError("forced v2 failed")),
    )
    with pytest.raises(RuntimeError, match="forced v2 failed"):
        DayScoringRuntimeService().compute([], force_v2=True)

def test_runtime_global_selected_v2_error_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_global_selected_v2_error_reraises
    # purpose: Verify a failure in globally selected V2 is propagated to the caller.
    # inputs: monkeypatch — pytest fixture for global V2 and a failing V2 fake.
    # returns: none.
    # side_effects: monkeypatches global V2, runtime scoring services, and logging functions.
    # emitted_logs: none.
    # error_behavior: expects the exact configured RuntimeError from globally selected V2.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_global_selected_v2_error_reraises
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    _install_fake_scoring(
        monkeypatch,
        v2_service=_FakeV2Service(error=RuntimeError("global v2 failed")),
    )
    with pytest.raises(RuntimeError, match="global v2 failed"):
        DayScoringRuntimeService().compute([], force_v2=False)

def test_runtime_dual_run_only_error_records_and_returns_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_dual_run_only_error_records_and_returns_v1
    # purpose: Verify a shadow-only V2 failure is recorded while the selected V1 response succeeds.
    # inputs: monkeypatch — pytest fixture for dual-run and a failing V2 fake.
    # returns: none.
    # side_effects: monkeypatches dual-run, runtime scoring services, and logging functions.
    # emitted_logs: none.
    # error_behavior: assertion failure if the shadow error is raised, lost, or changes V1 selection.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_dual_run_only_error_records_and_returns_v1
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    _install_fake_scoring(
        monkeypatch,
        v2_service=_FakeV2Service(error=RuntimeError("shadow v2 failed")),
    )
    result = DayScoringRuntimeService().compute([])
    assert result.selected_scoring_version == LEGACY_SCORING_VERSION
    assert result.selected_result is result.v1_result
    assert result.v2_error == "shadow v2 failed"

def test_force_success_leaves_global_settings_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_force_success_leaves_global_settings_unchanged
    # purpose: Verify a successful request-forced V2 computation never mutates global rollout settings.
    # inputs: monkeypatch — pytest fixture for global flags and deterministic scoring fakes.
    # returns: none.
    # side_effects: monkeypatches both global flags, runtime scoring services, and logging functions.
    # emitted_logs: none.
    # error_behavior: assertion failure if either global flag changes during successful execution.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_force_success_leaves_global_settings_unchanged
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)
    before = (settings.solarsage_v2_enabled, settings.solarsage_v2_dual_run)
    _install_fake_scoring(monkeypatch)
    DayScoringRuntimeService().compute([], force_v2=True)
    assert (settings.solarsage_v2_enabled, settings.solarsage_v2_dual_run) == before

def test_force_exception_leaves_global_settings_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_force_exception_leaves_global_settings_unchanged
    # purpose: Verify a failed request-forced V2 computation never mutates global rollout settings.
    # inputs: monkeypatch — pytest fixture for global flags and a failing V2 fake.
    # returns: none.
    # side_effects: monkeypatches both global flags, runtime scoring services, and logging functions.
    # emitted_logs: none.
    # error_behavior: expects the forced RuntimeError and asserts both global flags remain unchanged.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_force_exception_leaves_global_settings_unchanged
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)
    before = (settings.solarsage_v2_enabled, settings.solarsage_v2_dual_run)
    _install_fake_scoring(
        monkeypatch,
        v2_service=_FakeV2Service(error=RuntimeError("forced v2 failed")),
    )
    with pytest.raises(RuntimeError, match="forced v2 failed"):
        DayScoringRuntimeService().compute([], force_v2=True)
    assert (settings.solarsage_v2_enabled, settings.solarsage_v2_dual_run) == before
# END_BLOCK: RUNTIME_SELECTION

# START_BLOCK: CONCURRENT_INDEPENDENCE
def test_overlapping_force_and_default_calls_are_request_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_overlapping_force_and_default_calls_are_request_independent
    # purpose: Verify overlapping forced-V2 and default-V1 requests select independently without global flag mutation.
    # inputs: monkeypatch — pytest fixture for global flags and deterministic scoring fakes.
    # returns: none.
    # side_effects: monkeypatches runtime dependencies and runs two bounded worker threads synchronized by a barrier.
    # emitted_logs: none.
    # error_behavior: assertion failure on selection, call-count, snapshot, or global-state drift; futures time out if overlap fails.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_overlapping_force_and_default_calls_are_request_independent
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)
    barrier = Barrier(2)
    v1 = _FakeV1Service(overlap_barrier=barrier)
    _, v2 = _install_fake_scoring(monkeypatch, v1_service=v1)
    runtime = DayScoringRuntimeService()

    with ThreadPoolExecutor(max_workers=2) as executor:
        forced_future = executor.submit(runtime.compute, [], force_v2=True)
        default_future = executor.submit(runtime.compute, [], force_v2=False)
        forced_result = forced_future.result(timeout=5)
        default_result = default_future.result(timeout=5)

    assert forced_result.selected_scoring_version == SCORING_V2_VERSION
    assert forced_result.selected_result["day_status"] == "v2_status"
    assert default_result.selected_scoring_version == LEGACY_SCORING_VERSION
    assert default_result.selected_result["day_status"] == "v1_status"
    assert v1.calls == 2
    assert v2.calls == 1
    assert v1.flag_snapshots == [(False, False)] * 4
    assert settings.solarsage_v2_enabled is False
    assert settings.solarsage_v2_dual_run is False
# END_BLOCK: CONCURRENT_INDEPENDENCE


# START_BLOCK: CACHE_AUTHORITY
def test_cache_default_none_global_false_uses_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_default_none_global_false_uses_v1
    # purpose: Verify an omitted cache authority follows disabled global V2 into the legacy V1 identity.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled and reads canon versions for the cache key.
    # emitted_logs: none.
    # error_behavior: assertion failure if scoring or calculation identity is not legacy V1; propagates cache-key errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_default_none_global_false_uses_v1
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    key = expected_cache_identity(
        user_id=uuid4(), target_date="2026-07-13", profile_hash="profile",
    )
    assert key.scoring_version == LEGACY_SCORING_VERSION
    assert key.calculation_version == LEGACY_CALCULATION_VERSION


def test_cache_default_none_global_true_uses_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_default_none_global_true_uses_v2
    # purpose: Verify an omitted cache authority follows enabled global V2 into the V2 identity.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled and reads canon versions for the cache key.
    # emitted_logs: none.
    # error_behavior: assertion failure if scoring or calculation identity is not V2; propagates cache-key errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_default_none_global_true_uses_v2
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    key = expected_cache_identity(
        user_id=uuid4(), target_date="2026-07-13", profile_hash="profile",
    )
    assert key.scoring_version == SCORING_V2_VERSION
    assert key.calculation_version == CALCULATION_VERSION


def test_cache_explicit_v2_global_false_remains_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_explicit_v2_global_false_remains_v2
    # purpose: Verify explicit V2 cache authority overrides a disabled global V2 flag.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled and reads canon versions for the cache key.
    # emitted_logs: none.
    # error_behavior: assertion failure if explicit V2 authority resolves to another family; propagates cache-key errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_explicit_v2_global_false_remains_v2
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    key = expected_cache_identity(
        user_id=uuid4(),
        target_date="2026-07-13",
        profile_hash="profile",
        selected_scoring_version=SCORING_V2_VERSION,
    )
    assert key.scoring_version == SCORING_V2_VERSION
    assert key.calculation_version == CALCULATION_VERSION


def test_cache_explicit_v1_global_true_remains_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_explicit_v1_global_true_remains_v1
    # purpose: Verify explicit V1 cache authority overrides an enabled global V2 flag.
    # inputs: monkeypatch — pytest fixture for the global V2 flag.
    # returns: none.
    # side_effects: monkeypatches settings.solarsage_v2_enabled and reads canon versions for the cache key.
    # emitted_logs: none.
    # error_behavior: assertion failure if explicit V1 authority resolves to another family; propagates cache-key errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_explicit_v1_global_true_remains_v1
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    key = expected_cache_identity(
        user_id=uuid4(),
        target_date="2026-07-13",
        profile_hash="profile",
        selected_scoring_version=LEGACY_SCORING_VERSION,
    )
    assert key.scoring_version == LEGACY_SCORING_VERSION
    assert key.calculation_version == LEGACY_CALCULATION_VERSION


@pytest.mark.parametrize(
    "selected_scoring_version",
    [LEGACY_SCORING_VERSION, SCORING_V2_VERSION],
)
def test_cache_explicit_authority_does_not_call_global_flag_selector(
    monkeypatch: pytest.MonkeyPatch,
    selected_scoring_version: int | str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_explicit_authority_does_not_call_global_flag_selector
    # purpose: Verify either explicit scoring version bypasses the ambient global flag selector entirely.
    # inputs: monkeypatch and parametrized selected_scoring_version for V1 and V2 authorities.
    # returns: none.
    # side_effects: monkeypatches the cache module's global selector and reads canon versions for the cache key.
    # emitted_logs: none.
    # error_behavior: nested guard raises if called; assertion failure if returned scoring authority differs.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_explicit_authority_does_not_call_global_flag_selector
    def fail_if_called(*args: Any, **kwargs: Any) -> int | str:
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.fail_if_called
        # purpose: Fail immediately if explicit cache identity resolution consults global selection flags.
        # inputs: arbitrary positional and keyword arguments supplied by an unexpected call.
        # returns: no normal return; annotation matches the replaced selector boundary.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: always raises AssertionError to expose an ambient selector call.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.fail_if_called
        del args, kwargs
        raise AssertionError("explicit cache authority must bypass global selection flags")

    monkeypatch.setattr(
        cache_key_module,
        "selected_scoring_version_for_flags",
        fail_if_called,
    )
    key = expected_cache_identity(
        user_id=uuid4(),
        target_date="2026-07-13",
        profile_hash="profile",
        selected_scoring_version=selected_scoring_version,
    )
    assert key.scoring_version == selected_scoring_version


def test_cache_dual_run_alone_does_not_select_v2(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_dual_run_alone_does_not_select_v2
    # purpose: Verify shadow dual-run alone cannot select the V2 cache identity.
    # inputs: monkeypatch — pytest fixture for global V2 and dual-run flags.
    # returns: none.
    # side_effects: monkeypatches both global rollout flags and reads canon versions for the cache key.
    # emitted_logs: none.
    # error_behavior: assertion failure if dual-run changes cache selection from V1; propagates cache-key errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_dual_run_alone_does_not_select_v2
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    key = expected_cache_identity(
        user_id=uuid4(), target_date="2026-07-13", profile_hash="profile",
    )
    assert key.scoring_version == LEGACY_SCORING_VERSION


def test_cache_frontend_flag_does_not_select_family(monkeypatch: pytest.MonkeyPatch) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_frontend_flag_does_not_select_family
    # purpose: Verify frontend rollout enablement cannot select scoring or frontend cache identity by itself.
    # inputs: monkeypatch — pytest fixture for scoring and frontend rollout flags.
    # returns: none.
    # side_effects: monkeypatches global scoring/frontend flags and reads canon versions for the cache key.
    # emitted_logs: none.
    # error_behavior: assertion failure if the frontend flag selects a non-legacy family; propagates cache-key errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_frontend_flag_does_not_select_family
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", True)
    key = expected_cache_identity(
        user_id=uuid4(), target_date="2026-07-13", profile_hash="profile",
    )
    assert key.scoring_version == LEGACY_SCORING_VERSION
    assert key.frontend_payload_version == LEGACY_FRONTEND_PAYLOAD_VERSION


@pytest.mark.parametrize(
    "selected_scoring_version",
    [LEGACY_SCORING_VERSION, SCORING_V2_VERSION],
)
def test_cache_read_write_fields_and_hash_have_exact_parity(
    monkeypatch: pytest.MonkeyPatch,
    selected_scoring_version: int | str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_read_write_fields_and_hash_have_exact_parity
    # purpose: Verify explicit read and runtime write cache keys are field-identical and hash-identical for V1 and V2.
    # inputs: monkeypatch and parametrized selected_scoring_version for both scoring families.
    # returns: none.
    # side_effects: monkeypatches global V2 contrary to explicit authority and reads canon versions for both keys.
    # emitted_logs: none.
    # error_behavior: assertion failure on any read/write field or hash mismatch; propagates cache-key errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_read_write_fields_and_hash_have_exact_parity
    monkeypatch.setattr(
        settings,
        "solarsage_v2_enabled",
        selected_scoring_version == LEGACY_SCORING_VERSION,
    )
    user_id = uuid4()
    common = {
        "user_id": user_id,
        "target_date": "2026-07-13",
        "profile_hash": "same-profile",
    }
    read_key = expected_cache_identity(
        **common,
        selected_scoring_version=selected_scoring_version,
    )
    write_key = _write_key_for_selected_version(
        **common,
        selected_scoring_version=selected_scoring_version,
    )
    assert read_key == write_key
    assert read_key.cache_key_hash == write_key.cache_key_hash


def test_cache_v1_and_v2_hashes_are_distinct() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_v1_and_v2_hashes_are_distinct
    # purpose: Verify identical request identity produces distinct cache hashes for explicit V1 and V2 families.
    # inputs: none.
    # returns: none.
    # side_effects: reads canon versions while building both cache keys.
    # emitted_logs: none.
    # error_behavior: assertion failure if V1 and V2 cache hashes collide; propagates cache-key errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_v1_and_v2_hashes_are_distinct
    user_id = uuid4()
    common = {
        "user_id": user_id,
        "target_date": "2026-07-13",
        "profile_hash": "same-profile",
    }
    v1_key = expected_cache_identity(
        **common,
        selected_scoring_version=LEGACY_SCORING_VERSION,
    )
    v2_key = expected_cache_identity(
        **common,
        selected_scoring_version=SCORING_V2_VERSION,
    )
    assert v1_key.cache_key_hash != v2_key.cache_key_hash


@pytest.mark.parametrize(
    (
        "selected_scoring_version",
        "calculation_version",
        "scoring_version",
        "payload_version",
        "frontend_payload_version",
    ),
    [
        (
            LEGACY_SCORING_VERSION,
            LEGACY_CALCULATION_VERSION,
            LEGACY_SCORING_VERSION,
            TODAY_V1_PAYLOAD_VERSION,
            LEGACY_FRONTEND_PAYLOAD_VERSION,
        ),
        (
            SCORING_V2_VERSION,
            CALCULATION_VERSION,
            SCORING_V2_VERSION,
            TODAY_V2_PAYLOAD_VERSION,
            V2_FRONTEND_PAYLOAD_VERSION,
        ),
    ],
)
def test_public_runtime_identity_versions_remain_exact(
    selected_scoring_version: int | str,
    calculation_version: str,
    scoring_version: int | str,
    payload_version: str,
    frontend_payload_version: int,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_public_runtime_identity_versions_remain_exact
    # purpose: Verify every public runtime identity field retains the canonical V1 and V2 version-family mapping.
    # inputs: parametrized selected, calculation, scoring, payload, and frontend version expectations.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if any canonical version field differs from its family expectation.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_public_runtime_identity_versions_remain_exact
    identity = resolve_today_runtime_identity(
        selected_scoring_version=selected_scoring_version,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
    )
    assert identity.calculation_version == calculation_version
    assert identity.activation_layer_version == ACTIVATION_LAYER_VERSION
    assert identity.scoring_version == scoring_version
    assert identity.payload_version == payload_version
    assert identity.frontend_payload_version == frontend_payload_version
    assert identity.content_version == TODAY_CONTENT_VERSION
# END_BLOCK: CACHE_AUTHORITY


# START_BLOCK: STATIC_GUARDS
def test_implementation_has_no_ambient_context_or_settings_mutation() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_implementation_has_no_ambient_context_or_settings_mutation
    # purpose: Verify all W1 service sources avoid ambient selection storage and direct global settings assignments.
    # inputs: none.
    # returns: none.
    # side_effects: reads and parses the three W1 service source files.
    # emitted_logs: none.
    # error_behavior: assertion failure on forbidden tokens or settings mutation; propagates read or parse errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_implementation_has_no_ambient_context_or_settings_mutation
    services_dir = Path(__file__).resolve().parents[1] / "app/services"
    implementation_paths = [
        services_dir / "today_selection_context.py",
        services_dir / "day_scoring_runtime_service.py",
        services_dir / "cache_key_service.py",
    ]
    forbidden_context_tokens = ("ContextVar", "threading.local", "current_selection")
    for path in implementation_paths:
        source = path.read_text(encoding="utf-8")
        assert not any(token in source for token in forbidden_context_tokens)
        assert "setattr(settings" not in source
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                assert not any(
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "settings"
                    for target in targets
                )


def test_force_v2_signatures_are_keyword_only_and_default_false() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_force_v2_signatures_are_keyword_only_and_default_false
    # purpose: Verify all request force_v2 boundaries remain keyword-only with a false compatibility default.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if any helper or runtime signature changes its force_v2 contract.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_force_v2_signatures_are_keyword_only_and_default_false
    helper_signature = inspect.signature(should_compute_v2)
    selected_signature = inspect.signature(selected_scoring_version_for_flags)
    compute_signature = inspect.signature(DayScoringRuntimeService.compute)
    for signature in (helper_signature, selected_signature, compute_signature):
        parameter = signature.parameters["force_v2"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is False


def test_cache_boundary_has_one_explicit_version_authority_not_force_selector() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_boundary_has_one_explicit_version_authority_not_force_selector
    # purpose: Verify the cache-read boundary accepts only optional selected scoring version as family authority.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: assertion failure if the authority is removed, gains a non-None default, or force_v2 appears.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_cache_boundary_has_one_explicit_version_authority_not_force_selector
    signature = inspect.signature(expected_cache_identity)
    assert "selected_scoring_version" in signature.parameters
    assert signature.parameters["selected_scoring_version"].default is None
    assert "force_v2" not in signature.parameters


def test_runtime_keeps_only_existing_structured_event_name() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_keeps_only_existing_structured_event_name
    # purpose: Verify W1 runtime logging introduces no structured event beyond the existing scoring.v2_diff event.
    # inputs: none.
    # returns: none.
    # side_effects: reads and parses the loaded runtime service source.
    # emitted_logs: none.
    # error_behavior: assertion failure if structured event names are added, removed, or renamed; propagates parse errors.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-SELECTION-CONTEXT.test_runtime_keeps_only_existing_structured_event_name
    source = inspect.getsource(runtime_module)
    tree = ast.parse(source)
    event_names = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "log_event"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert event_names == {"scoring.v2_diff"}
# END_BLOCK: STATIC_GUARDS
