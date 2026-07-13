# ############################################################################
# AI_HEADER: TEST_TODAY_PREVIEW_ACCESS — request-scoped full-access proof.
# ROLE: Verifies pure access derivation, route isolation, and fail-closed boundaries.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-PREVIEW-ACCESS
# purpose: Prove exact local preview receives full/null access while every other
#          request preserves the real AccessService result and global state.
# owns:
#   - apps/api/tests/test_today_preview_access.py
# inputs: Pure access/context values and isolated in-process ASGI requests.
# outputs: Resolver, route, concurrency, import, and static boundary assertions.
# dependencies: pytest, FastAPI/httpx, Today route, access/selection schemas.
# side_effects: Builds isolated ASGI apps and monkeypatches test-local dependencies.
# emitted_logs: none.
# invariants:
#   - No live service, database, access ledger, external network, or raw identity output.
#   - AccessService baseline is preview/expired unless a case declares otherwise.
#   - Local preview full access always has null commercial metadata.
# failure_policy: Assertion failure on access, identity, isolation, or source drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-PREVIEW-ACCESS

# START_MODULE_MAP: M-TEST-TODAY-PREVIEW-ACCESS
# public_entrypoints:
#   - pytest test cases in this module
# semantic_blocks:
#   - TEST_SUPPORT: access values, schema-valid payloads, and ASGI recorders.
#   - PURE_RESOLVER: closed resolver matrix, purity, and concurrency.
#   - ROUTE_MATRIX: authorized, denied, global, baseline, and overlap cases.
#   - STATIC_GUARDS: resolver imports, route selectors, and mutation guards.
# owned_tests:
#   - apps/api/tests/test_today_preview_access.py
# END_MODULE_MAP: M-TEST-TODAY-PREVIEW-ACCESS

from __future__ import annotations

import ast
import asyncio
from datetime import date as Date
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import day as day_api
from app.core.config import settings
from app.core.versions import (
    ACTIVATION_LAYER_VERSION,
    LEGACY_SCORING_VERSION,
    SCORING_V2_VERSION,
)
from app.schemas.access import ContentAccessState
from app.schemas.today import TodayPayload
from app.services.cache_key_service import resolve_today_runtime_identity
from app.services.today_preview_access import resolve_today_access_for_selection
from app.services.today_preview_guard import (
    TODAY_PREVIEW_HEADER_NAME,
    TODAY_PREVIEW_HEADER_VALUE,
    TODAY_PREVIEW_TG_USER_ID,
    TODAY_PREVIEW_TG_USERNAME,
)
from app.services.today_selection_context import (
    TodaySelectionContext,
    TodaySelectionSource,
)


# START_BLOCK: TEST_SUPPORT
LOCAL_PREVIEW = TodaySelectionContext(
    force_v2=True,
    source=TodaySelectionSource.LOCAL_DEV_PREVIEW,
)
GLOBAL_V1 = TodaySelectionContext(
    force_v2=False,
    source=TodaySelectionSource.GLOBAL_FLAGS,
)
GLOBAL_V2 = TodaySelectionContext(
    force_v2=True,
    source=TodaySelectionSource.GLOBAL_FLAGS,
)
MALFORMED_LOCAL = TodaySelectionContext(
    force_v2=False,
    source=TodaySelectionSource.LOCAL_DEV_PREVIEW,
)


def _preview_access() -> ContentAccessState:
    return ContentAccessState(
        state="preview",
        reason="expired_access",
        referral_days_left=None,
        subscription_active=None,
        access_until=None,
    )


def _locked_access() -> ContentAccessState:
    return ContentAccessState(
        state="locked",
        reason="outside_access_window",
        referral_days_left=None,
        subscription_active=None,
        access_until=None,
    )


def _commercial_access() -> ContentAccessState:
    return ContentAccessState(
        state="full",
        reason="active_subscription",
        referral_days_left=None,
        subscription_active=True,
        access_until="2026-08-01",
    )


def _assert_full_null(access: ContentAccessState) -> None:
    assert access.model_dump() == {
        "state": "full",
        "reason": None,
        "referral_days_left": None,
        "subscription_active": None,
        "access_until": None,
    }


def _payload_for(
    context: TodaySelectionContext,
    access_state: ContentAccessState,
) -> TodayPayload:
    selected_version = SCORING_V2_VERSION if context.force_v2 else LEGACY_SCORING_VERSION
    identity = resolve_today_runtime_identity(
        selected_scoring_version=selected_version,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
    )
    payload: dict[str, Any] = {
        "meta": {
            "schema_version": "today/v1",
            "contract_version": 3,
            "calculation_version": identity.calculation_version,
            "normalization_version": 1,
            "scoring_version": identity.scoring_version,
            "prompt_version": 2,
            "content_version": identity.content_version,
            "generated_at": "2026-07-13T00:00:00+00:00",
            "cached": False,
            "canon_versions": {},
            "activation_layer_version": identity.activation_layer_version,
            "payload_version": identity.payload_version,
            "frontend_payload_version": identity.frontend_payload_version,
        },
        "date": "2026-07-13",
        "title": "Today",
        "headline": "Boundary payload",
        "access": access_state.model_dump(mode="json"),
        "day_status": "steady",
        "day_summary": {"status_label": "Steady", "status_line": "Safe", "facts": []},
        "concrete_advice": {
            "rows": [],
            "counts": {"good": 0, "caution": 0, "avoid": 0, "neutral": 0},
        },
        "top_flags": [],
        "reading": {"paragraphs": ["Boundary"]},
        "why_this_happens": {"sections": []},
        "week_strip": [],
        "microcopy": [],
        "important_today": [],
        "v2": None,
    }
    if context.force_v2:
        payload["v2"] = {
            "activation_summary": {"headline": "Preview", "top_activated_targets": []},
            "activation_evidence": [],
            "score_breakdown": {},
            "why_today": [],
            "audit": {
                "available": False,
                "payload_version": identity.payload_version,
                "calculation_version": identity.calculation_version,
                "scoring_version": identity.scoring_version,
                "activation_layer_version": identity.activation_layer_version,
                "canon_versions": {},
                "horizon_pipeline": {
                    "status": "unavailable",
                    "reason": "missing_long",
                    "selected_count": 0,
                },
            },
            "horizons": None,
        }
    return TodayPayload.model_validate(payload)


class _RouteAccessService:
    def __init__(self, baseline: ContentAccessState) -> None:
        self.baseline = baseline
        self.calls: list[tuple[Any, Date]] = []

    async def can_access_day(
        self,
        user_id: Any,
        target_date: Date,
    ) -> ContentAccessState:
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.RouteAccessService.can_access_day
        # purpose: Record one real-access boundary call and return its declared baseline.
        # inputs: user_id and target_date accepted for AccessService compatibility.
        # returns: The same baseline ContentAccessState instance.
        # side_effects: Appends a non-serialized call tuple to the test recorder.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.RouteAccessService.can_access_day
        self.calls.append((user_id, target_date))
        return self.baseline


class _RouteTodayService:
    def __init__(self, *, overlap_count: int = 0) -> None:
        self.records: list[tuple[TodaySelectionContext, ContentAccessState]] = []
        self._overlap_count = overlap_count
        self._all_arrived = asyncio.Event()

    async def get_today_payload(
        self,
        user_id: Any,
        target_date: Date,
        access_state: ContentAccessState,
        skip_prefetch: bool = False,
        *,
        selection_context: TodaySelectionContext | None = None,
    ) -> TodayPayload:
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.RouteTodayService.get_today_payload
        # purpose: Record route access/context and return a matching schema-valid payload.
        # inputs: Service-compatible arguments plus explicit selection_context.
        # returns: TodayPayload whose access and V1/V2 identity match received values.
        # side_effects: Appends a record and optionally synchronizes overlapping calls.
        # emitted_logs: none.
        # error_behavior: AssertionError when selection_context is missing.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.RouteTodayService.get_today_payload
        del user_id, target_date, skip_prefetch
        assert selection_context is not None
        self.records.append((selection_context, access_state))
        if self._overlap_count:
            if len(self.records) >= self._overlap_count:
                self._all_arrived.set()
            await self._all_arrived.wait()
        return _payload_for(selection_context, access_state)


def _route_user(*, exact_identity: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        tg_user_id=TODAY_PREVIEW_TG_USER_ID if exact_identity else 7777,
        tg_username=TODAY_PREVIEW_TG_USERNAME if exact_identity else "ordinary",
        profile=SimpleNamespace(
            is_onboarded=True,
            birth_lat=55.75,
            birth_lon=37.61,
        ),
    )


def _build_route_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    baseline: ContentAccessState | None = None,
    user: SimpleNamespace | None = None,
    overlap_count: int = 0,
) -> SimpleNamespace:
    route_app = FastAPI()
    route_app.include_router(day_api.router)
    selected_user = user or _route_user()
    selected_baseline = baseline or _preview_access()
    access_recorder = _RouteAccessService(selected_baseline)
    today_recorder = _RouteTodayService(overlap_count=overlap_count)
    db = SimpleNamespace(boundary_marker=object())
    db_before = vars(db).copy()
    access_factory_calls: list[Any] = []

    async def _override_user() -> SimpleNamespace:
        return selected_user

    async def _override_db() -> Any:
        yield db

    def _access_factory(db_value: Any) -> _RouteAccessService:
        access_factory_calls.append(db_value)
        return access_recorder

    route_app.dependency_overrides[day_api.require_session] = _override_user
    route_app.dependency_overrides[day_api.get_session] = _override_db
    monkeypatch.setattr(day_api, "AccessService", _access_factory)
    monkeypatch.setattr(day_api, "TodayService", lambda db_value: today_recorder)
    return SimpleNamespace(
        app=route_app,
        baseline=selected_baseline,
        access=access_recorder,
        today=today_recorder,
        db=db,
        db_before=db_before,
        access_factory_calls=access_factory_calls,
    )


async def _route_get(
    app: FastAPI,
    *,
    base_url: str = "http://127.0.0.1:3003",
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    transport = ASGITransport(app=app, client=("127.0.0.1", 49152))
    async with AsyncClient(transport=transport, base_url=base_url) as client:
        return await client.get(
            "/api/day/2026-07-13",
            headers=headers,
            params=params,
        )


def _assert_v2_identity(body: dict[str, Any]) -> None:
    assert body["meta"]["payloadVersion"] == "today.v2.1"
    assert body["meta"]["scoringVersion"] == SCORING_V2_VERSION
    assert body["v2"] is not None


def _assert_v1_identity(body: dict[str, Any]) -> None:
    assert body["meta"]["payloadVersion"] == "today.v1"
    assert body["meta"]["scoringVersion"] == LEGACY_SCORING_VERSION
    assert body["v2"] is None


def _assert_full_null_wire(body: dict[str, Any]) -> None:
    assert body["access"] == {
        "state": "full",
        "reason": None,
        "referralDaysLeft": None,
        "subscriptionActive": None,
        "accessUntil": None,
    }
# END_BLOCK: TEST_SUPPORT


# START_BLOCK: PURE_RESOLVER
@pytest.mark.parametrize(
    "baseline_factory",
    [_preview_access, _locked_access, _commercial_access],
)
def test_local_preview_replaces_any_baseline_with_exact_full_null(
    baseline_factory: Any,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_local_preview_replaces_any_baseline_with_exact_full_null
    # purpose: Verify preview, locked, and commercial baselines receive exact local full access.
    # inputs: Parametrized baseline factory.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Assertion failure on value, identity, or input mutation drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_local_preview_replaces_any_baseline_with_exact_full_null
    baseline = baseline_factory()
    before = baseline.model_dump_json()
    result = resolve_today_access_for_selection(
        access_state=baseline,
        selection_context=LOCAL_PREVIEW,
    )
    assert result is not baseline
    _assert_full_null(result)
    assert baseline.model_dump_json() == before


@pytest.mark.parametrize("context", [GLOBAL_V1, GLOBAL_V2, MALFORMED_LOCAL])
def test_non_preview_contexts_preserve_same_access_instance(
    context: TodaySelectionContext,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_non_preview_contexts_preserve_same_access_instance
    # purpose: Verify global V1, global V2, and malformed local contexts fail closed.
    # inputs: Parametrized non-authorized selection context.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Assertion failure if access identity or value changes.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_non_preview_contexts_preserve_same_access_instance
    baseline = _preview_access()
    before = baseline.model_dump_json()
    result = resolve_today_access_for_selection(
        access_state=baseline,
        selection_context=context,
    )
    assert result is baseline
    assert result.model_dump_json() == before


@pytest.mark.asyncio
async def test_concurrent_resolver_calls_are_independent() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_concurrent_resolver_calls_are_independent
    # purpose: Prove concurrent local/global resolutions do not share request state.
    # inputs: none.
    # returns: none.
    # side_effects: Schedules two in-process coroutines.
    # emitted_logs: none.
    # error_behavior: Assertion failure on cross-call access leakage.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_concurrent_resolver_calls_are_independent
    local_baseline = _locked_access()
    global_baseline = _preview_access()
    async def _resolve(
        access_state: ContentAccessState,
        context: TodaySelectionContext,
    ) -> ContentAccessState:
        await asyncio.sleep(0)
        return resolve_today_access_for_selection(
            access_state=access_state,
            selection_context=context,
        )
    local_result, global_result = await asyncio.gather(
        _resolve(local_baseline, LOCAL_PREVIEW),
        _resolve(global_baseline, GLOBAL_V2),
    )
    _assert_full_null(local_result)
    assert global_result is global_baseline
    assert global_result.state == "preview"


# END_BLOCK: PURE_RESOLVER


# START_BLOCK: ROUTE_MATRIX
@pytest.mark.parametrize("case", ["direct", "next-rewrite", "locked-baseline"])
@pytest.mark.asyncio
async def test_route_authorized_local_preview_gets_full_null_v2(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_route_authorized_local_preview_gets_full_null_v2
    # purpose: Prove direct, Next rewrite, and locked-baseline local preview access.
    # inputs: monkeypatch fixture and parametrized authorized route case.
    # returns: none.
    # side_effects: Executes one isolated ASGI request.
    # emitted_logs: none.
    # error_behavior: Assertion failure on access, identity, call count, or mutation.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_route_authorized_local_preview_gets_full_null_v2
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    baseline = _locked_access() if case == "locked-baseline" else _preview_access()
    harness = _build_route_harness(monkeypatch, baseline=baseline)
    base_url = "http://127.0.0.1:3003"
    headers = {TODAY_PREVIEW_HEADER_NAME: TODAY_PREVIEW_HEADER_VALUE}
    if case == "next-rewrite":
        base_url = "http://127.0.0.1:8000"
        headers.update({
            "X-Forwarded-For": "127.0.0.1, ::1",
            "X-Forwarded-Host": "127.0.0.1:3003",
            "X-Forwarded-Port": "3003",
        })
    app_env_before = settings.app_env
    global_v2_before = settings.solarsage_v2_enabled
    response = await _route_get(
        harness.app,
        base_url=base_url,
        headers=headers,
    )
    body = response.json()
    assert response.status_code == 200
    assert harness.today.records[0][0] == LOCAL_PREVIEW
    assert harness.today.records[0][1] is not harness.baseline
    _assert_full_null(harness.today.records[0][1])
    _assert_full_null_wire(body)
    _assert_v2_identity(body)
    assert len(harness.access.calls) == len(harness.access_factory_calls) == 1
    assert harness.access_factory_calls[0] is harness.db
    assert vars(harness.db) == harness.db_before
    assert settings.app_env == app_env_before
    assert settings.solarsage_v2_enabled is global_v2_before


@pytest.mark.parametrize(
    "case",
    ["missing-marker", "wrong-marker", "ordinary-identity", "public-forwarded", "wrong-port", "production", "query-only"],
)
@pytest.mark.asyncio
async def test_route_denials_preserve_preview_access(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_route_denials_preserve_preview_access
    # purpose: Verify missing/wrong/ordinary/public/port/prod/query attempts preserve preview.
    # inputs: monkeypatch fixture and a parametrized denied transport case.
    # returns: none.
    # side_effects: Executes one isolated ASGI request per collected case.
    # emitted_logs: none.
    # error_behavior: Assertion failure if denial changes real access or V1 identity.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_route_denials_preserve_preview_access
    monkeypatch.setattr(
        settings,
        "app_env",
        "production" if case == "production" else "development",
    )
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    headers: dict[str, str] = {}
    params: dict[str, str] | None = None
    base_url = "http://127.0.0.1:3003"
    user = _route_user(exact_identity=case != "ordinary-identity")
    if case not in {"missing-marker", "query-only"}:
        headers[TODAY_PREVIEW_HEADER_NAME] = (
            "wrong" if case == "wrong-marker" else TODAY_PREVIEW_HEADER_VALUE
        )
    if case == "public-forwarded":
        headers.update({
            "X-Forwarded-For": "127.0.0.1, 203.0.113.9",
            "X-Forwarded-Host": "preview.example:3003",
        })
    if case == "wrong-port":
        base_url = "http://127.0.0.1:3000"
    if case == "query-only":
        params = {"preview": "today-v2-real", "v2": "1", "fixture": "1"}
    harness = _build_route_harness(monkeypatch, user=user)
    response = await _route_get(
        harness.app,
        base_url=base_url,
        headers=headers,
        params=params,
    )
    assert response.status_code == 200
    assert harness.today.records == [(GLOBAL_V1, harness.baseline)]
    assert response.json()["access"] == {
        "state": "preview",
        "reason": "expired_access",
        "referralDaysLeft": None,
        "subscriptionActive": None,
        "accessUntil": None,
    }
    _assert_v1_identity(response.json())
    assert len(harness.access.calls) == 1


@pytest.mark.parametrize("case", ["global-v2-preview", "ordinary-commercial"])
@pytest.mark.asyncio
async def test_route_nonlocal_selection_preserves_real_access(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_route_nonlocal_selection_preserves_real_access
    # purpose: Verify global V2 preview and ordinary commercial access remain unchanged.
    # inputs: monkeypatch fixture and parametrized nonlocal selection case.
    # returns: none.
    # side_effects: Executes one isolated ASGI request.
    # emitted_logs: none.
    # error_behavior: Assertion failure on access object, metadata, or identity drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_route_nonlocal_selection_preserves_real_access
    monkeypatch.setattr(settings, "app_env", "development")
    is_global_v2 = case == "global-v2-preview"
    monkeypatch.setattr(settings, "solarsage_v2_enabled", is_global_v2)
    baseline = _preview_access() if is_global_v2 else _commercial_access()
    expected_context = GLOBAL_V2 if is_global_v2 else GLOBAL_V1
    harness = _build_route_harness(monkeypatch, baseline=baseline)
    response = await _route_get(harness.app)
    assert response.status_code == 200
    assert harness.today.records == [(expected_context, harness.baseline)]
    if is_global_v2:
        assert response.json()["access"]["state"] == "preview"
        _assert_v2_identity(response.json())
    else:
        assert response.json()["access"] == {
            "state": "full",
            "reason": "active_subscription",
            "referralDaysLeft": None,
            "subscriptionActive": True,
            "accessUntil": "2026-08-01",
        }
        _assert_v1_identity(response.json())


@pytest.mark.asyncio
async def test_overlapping_preview_and_ordinary_routes_are_isolated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_overlapping_preview_and_ordinary_routes_are_isolated
    # purpose: Prove overlapping exact/ordinary calls keep independent access and globals.
    # inputs: monkeypatch fixture.
    # returns: none.
    # side_effects: Executes two synchronized isolated ASGI requests.
    # emitted_logs: none.
    # error_behavior: Assertion failure on cross-request leakage or global mutation.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_overlapping_preview_and_ordinary_routes_are_isolated
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    harness = _build_route_harness(monkeypatch, overlap_count=2)
    app_env_before = settings.app_env
    global_v2_before = settings.solarsage_v2_enabled
    preview_response, ordinary_response = await asyncio.gather(
        _route_get(
            harness.app,
            headers={TODAY_PREVIEW_HEADER_NAME: TODAY_PREVIEW_HEADER_VALUE},
        ),
        _route_get(harness.app),
    )
    assert preview_response.status_code == ordinary_response.status_code == 200
    _assert_full_null_wire(preview_response.json())
    assert ordinary_response.json()["access"]["state"] == "preview"
    assert {
        (context.force_v2, context.source, access.state)
        for context, access in harness.today.records
    } == {
        (True, TodaySelectionSource.LOCAL_DEV_PREVIEW, "full"),
        (False, TodaySelectionSource.GLOBAL_FLAGS, "preview"),
    }
    assert len(harness.access.calls) == len(harness.access_factory_calls) == 2
    assert settings.app_env == app_env_before
    assert settings.solarsage_v2_enabled is global_v2_before


# END_BLOCK: ROUTE_MATRIX


# START_BLOCK: STATIC_GUARDS
def test_route_and_resolver_access_boundaries_remain_closed() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_route_and_resolver_access_boundaries_remain_closed
    # purpose: Enforce selection-only resolver input and closed route selectors.
    # inputs: none.
    # returns: none.
    # side_effects: Reads and parses the owned route and resolver sources.
    # emitted_logs: none.
    # error_behavior: Assertion failure on selector, mutation, or write drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-ACCESS.test_route_and_resolver_access_boundaries_remain_closed
    repo_root = Path(__file__).resolve().parents[3]
    route_path = repo_root / "apps/api/app/api/day.py"
    resolver_path = repo_root / "apps/api/app/services/today_preview_access.py"
    route_source = route_path.read_text(encoding="utf-8")
    resolver_source = resolver_path.read_text(encoding="utf-8")
    route_tree = ast.parse(route_source)
    resolver_tree = ast.parse(resolver_source)
    imported_modules = {
        node.module
        for node in resolver_tree.body
        if isinstance(node, ast.ImportFrom)
    }
    assert imported_modules == {
        "__future__",
        "app.schemas.access",
        "app.services.today_selection_context",
    }
    assert not any(isinstance(node, ast.Import) for node in resolver_tree.body)
    assert not any(
        isinstance(node, (ast.Global, ast.Nonlocal))
        for node in ast.walk(resolver_tree)
    )
    assert not any(
        isinstance(node, (ast.Assign, ast.AnnAssign))
        for node in resolver_tree.body
    )
    resolver_calls = [
        node
        for node in ast.walk(route_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "resolve_today_access_for_selection"
    ]
    assert len(resolver_calls) == 1
    keywords = {keyword.arg: keyword.value for keyword in resolver_calls[0].keywords}
    assert isinstance(keywords["access_state"], ast.Name)
    assert keywords["access_state"].id == "real_access_state"
    assert isinstance(keywords["selection_context"], ast.Name)
    assert keywords["selection_context"].id == "selection_context"
    assert not any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "request"
        and node.attr in {"query_params", "cookies"}
        for node in ast.walk(route_tree)
    )
    assert sum(
        isinstance(node, ast.Attribute) and node.attr == "can_access_day"
        for node in ast.walk(route_tree)
    ) == 1
    combined_source = route_source + resolver_source
    assert not any(
        token in combined_source
        for token in (
            "setattr(settings",
            "AccessLedger",
            "ContextVar",
            "threading.local",
            "current_request",
            "db.add(",
            "grant_referral",
            "grant_subscription",
        )
    )
# END_BLOCK: STATIC_GUARDS
