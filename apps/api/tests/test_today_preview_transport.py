# ############################################################################
# AI_HEADER: TEST_TODAY_PREVIEW_TRANSPORT — W2 guard, route, and service proofs.
# ROLE: Verifies the closed local transport proof and explicit Today V2 propagation.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-PREVIEW-TRANSPORT
# purpose: Prove pure preview authorization, ASGI route selection, service
#          cache/runtime boundaries, concurrency isolation, and static guards.
# owns:
#   - apps/api/tests/test_today_preview_transport.py
# inputs: Deterministic scalar guard cases, ASGI requests, and boundary mocks.
# outputs: Executable W2 authorization and propagation evidence.
# dependencies: pytest, FastAPI/httpx test transport, Today route/services/schemas.
# side_effects: Builds in-process ASGI apps and monkeypatches request-local test doubles.
# emitted_logs: none.
# invariants:
#   - No live service, external network, production data, or global selector mutation.
#   - V2 test payloads use the current identity and honest unavailable horizons.
#   - Parametrization collects at least thirty independent cases.
# failure_policy: Assertion failure on guard, route, service, isolation, or scope drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-PREVIEW-TRANSPORT

# START_MODULE_MAP: M-TEST-TODAY-PREVIEW-TRANSPORT
# public_entrypoints:
#   - pytest test cases in this module
# semantic_blocks:
#   - TEST_SUPPORT: schema-valid payloads, ASGI recorder, and service harness.
#   - PURE_GUARD: constants, ordered decisions, transport matrices, and purity.
#   - ROUTE_INTEGRATION: direct/rewrite selection, denials, and concurrency.
#   - SERVICE_BOUNDARIES: cache, sidecar, runtime, split-brain, and prefetch proofs.
#   - STATIC_GUARDS: signatures and forbidden ambient/selector mechanisms.
# owned_tests:
#   - apps/api/tests/test_today_preview_transport.py
# END_MODULE_MAP: M-TEST-TODAY-PREVIEW-TRANSPORT

from __future__ import annotations

import ast
import asyncio
import inspect
from dataclasses import fields
from datetime import date as Date
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
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
from app.services import today_service as today_service_module
from app.services.cache_key_service import resolve_today_runtime_identity
from app.services.day_scoring_runtime_service import DualRunResult
from app.services.today_preview_guard import (
    TODAY_PREVIEW_HEADER_NAME,
    TODAY_PREVIEW_HEADER_VALUE,
    TODAY_PREVIEW_PORT,
    TODAY_PREVIEW_TG_USER_ID,
    TODAY_PREVIEW_TG_USERNAME,
    TodayPreviewGuardDecision,
    TodayPreviewGuardInput,
    TodayPreviewGuardReason,
    authorize_today_preview,
)
from app.services.today_selection_context import (
    TodaySelectionContext,
    TodaySelectionSource,
)
from app.services.today_service import TodayService

# START_BLOCK: TEST_SUPPORT
class _BoundaryStop(Exception):
    """Expected deterministic stop after the boundary under test."""

def _guard_input(**overrides: Any) -> TodayPreviewGuardInput:
    values: dict[str, Any] = {
        "app_env": "development",
        "marker_value": TODAY_PREVIEW_HEADER_VALUE,
        "client_host": "127.0.0.1",
        "host": "127.0.0.1:3003",
        "origin": "http://127.0.0.1:3003",
        "forwarded": None,
        "x_forwarded_for": None,
        "x_forwarded_host": None,
        "x_forwarded_port": None,
        "x_real_ip": None,
        "tg_user_id": TODAY_PREVIEW_TG_USER_ID,
        "tg_username": TODAY_PREVIEW_TG_USERNAME,
    }
    values.update(overrides)
    return TodayPreviewGuardInput(**values)

def _payload_for(context: TodaySelectionContext) -> TodayPayload:
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
        "access": {"state": "full"},
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

class _RouteTodayService:
    """Request-context recorder returning schema-valid family payloads."""

    def __init__(self, *, overlap_count: int = 0) -> None:
        self.contexts: list[TodaySelectionContext] = []
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
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.RouteTodayService.get_today_payload
        # purpose: Record the explicit route selection and return a matching schema-valid payload.
        # inputs: Service-compatible user/date/access/prefetch arguments and selection_context.
        # returns: Current V1 or V2 TodayPayload matching the received context.
        # side_effects: Appends context and optionally synchronizes two overlapping ASGI calls.
        # emitted_logs: none.
        # error_behavior: Raises AssertionError for a missing route selection context.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.RouteTodayService.get_today_payload
        del user_id, target_date, access_state, skip_prefetch
        assert selection_context is not None
        self.contexts.append(selection_context)
        if self._overlap_count:
            if len(self.contexts) >= self._overlap_count:
                self._all_arrived.set()
            await self._all_arrived.wait()
        return _payload_for(selection_context)

class _RouteAccessService:
    """Minimal route access dependency returning full access."""

    def __init__(self, db: Any) -> None:
        del db

    async def can_access_day(self, user_id: Any, target_date: Date) -> ContentAccessState:
        # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.RouteAccessService.can_access_day
        # purpose: Return deterministic full access so route tests isolate selection behavior.
        # inputs: user_id and target_date accepted for AccessService compatibility.
        # returns: Full ContentAccessState.
        # side_effects: none.
        # emitted_logs: none.
        # error_behavior: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.RouteAccessService.can_access_day
        del user_id, target_date
        return ContentAccessState(state="full")

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

def _build_route_app(
    monkeypatch: pytest.MonkeyPatch,
    recorder: _RouteTodayService,
    *,
    user: SimpleNamespace | None = None,
) -> FastAPI:
    route_app = FastAPI()
    route_app.include_router(day_api.router)
    selected_user = user or _route_user()

    async def _override_user() -> SimpleNamespace:
        return selected_user

    async def _override_db() -> Any:
        yield SimpleNamespace()

    route_app.dependency_overrides[day_api.require_session] = _override_user
    route_app.dependency_overrides[day_api.get_session] = _override_db
    monkeypatch.setattr(day_api, "AccessService", _RouteAccessService)
    monkeypatch.setattr(day_api, "TodayService", lambda db: recorder)
    return route_app

async def _route_get(
    route_app: FastAPI,
    *,
    base_url: str = "http://127.0.0.1:3003",
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
) -> Any:
    transport = ASGITransport(app=route_app, client=("127.0.0.1", 49152))
    async with AsyncClient(transport=transport, base_url=base_url) as client:
        return await client.get(
            "/api/day/2026-07-13",
            headers=headers,
            params=params,
        )

def _install_service_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    runtime_selected_version: int | str,
    activation_error: Exception | None = None,
) -> SimpleNamespace:
    profile = SimpleNamespace(
        birth_lat=55.75,
        birth_lon=37.61,
        current_lat=None,
        current_lon=None,
        current_tz="Europe/Moscow",
        birth_tz="Europe/Moscow",
        birthday=Date(1990, 1, 1),
        birth_time=None,
    )
    db = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(scalar_one=lambda: profile),
        )
    )
    service = TodayService(db)
    service._get_cached_payload = AsyncMock(return_value=None)
    service._get_yesterday_signals = AsyncMock(return_value=None)
    service._cache_payload = AsyncMock()

    natal_context = SimpleNamespace(
        model_dump=MagicMock(return_value={"house_system": "PLACIDUS"}),
    )
    natal_class = MagicMock()
    natal_class.compute_profile_hash.return_value = "profile-hash"
    natal_class.return_value.get_or_build_natal_context = AsyncMock(
        return_value=natal_context,
    )
    monkeypatch.setattr(today_service_module, "NatalContextService", natal_class)

    client = MagicMock()
    client.get_transits = AsyncMock(return_value={"planets": []})
    client.get_activation_layer = AsyncMock(
        return_value=SimpleNamespace(activation_layer_version=ACTIVATION_LAYER_VERSION),
    )
    if activation_error is not None:
        client.get_activation_layer.side_effect = activation_error
    monkeypatch.setattr(today_service_module, "get_solarsage_client", lambda: client)

    normalization_class = MagicMock()
    normalization_class.return_value.normalize_day.return_value = []
    monkeypatch.setattr(today_service_module, "NormalizationService", normalization_class)

    activation_layer = SimpleNamespace(activation_layer_version=ACTIVATION_LAYER_VERSION)
    activation_class = MagicMock()
    activation_class.return_value.build.return_value = activation_layer
    monkeypatch.setattr(today_service_module, "ActivationLayerService", activation_class)

    runtime_result = DualRunResult(
        selected_result={"day_status": "steady", "sphere_scores": {}, "top_signals": []},
        selected_scoring_version=runtime_selected_version,
        v1_result={"day_status": "steady", "sphere_scores": {}, "top_signals": []},
        v2_result=SimpleNamespace() if runtime_selected_version == SCORING_V2_VERSION else None,
    )
    runtime_class = MagicMock()
    runtime_class.return_value.compute.return_value = runtime_result
    monkeypatch.setattr(today_service_module, "DayScoringRuntimeService", runtime_class)
    monkeypatch.setattr(today_service_module, "log_event", MagicMock())
    return SimpleNamespace(
        service=service,
        client=client,
        runtime_class=runtime_class,
        activation_class=activation_class,
    )
# END_BLOCK: TEST_SUPPORT

# START_BLOCK: PURE_GUARD
def test_guard_constants_are_exact() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_constants_are_exact
    # purpose: Verify the closed header, marker, identity, and port constants.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Assertion failure on any constant drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_constants_are_exact
    assert TODAY_PREVIEW_HEADER_NAME == "X-SolarSage-Preview-Mode"
    assert TODAY_PREVIEW_HEADER_VALUE == "today-v2-real"
    assert TODAY_PREVIEW_TG_USER_ID == 999999999
    assert TODAY_PREVIEW_TG_USERNAME == "dev_user"
    assert TODAY_PREVIEW_PORT == 3003

def test_guard_reason_enum_is_exact_and_closed() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_reason_enum_is_exact_and_closed
    # purpose: Verify the guard exposes only the approved safe reason values.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Assertion failure if a reason is added, removed, renamed, or revalued.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_reason_enum_is_exact_and_closed
    assert [reason.value for reason in TodayPreviewGuardReason] == [
        "authorized",
        "production_denied",
        "app_env_denied",
        "marker_denied",
        "client_denied",
        "forwarded_chain_denied",
        "host_denied",
        "origin_denied",
        "port_denied",
        "identity_denied",
    ]

def test_production_denial_is_absolute_and_first() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_production_denial_is_absolute_and_first
    # purpose: Prove normalized production denial occurs before all other explosive facts.
    # inputs: none.
    # returns: none.
    # side_effects: Constructs sentinel mocks that would raise if inspected.
    # emitted_logs: none.
    # error_behavior: Sentinel AssertionError exposes any out-of-order field access.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_production_denial_is_absolute_and_first
    exploding = MagicMock()
    exploding.__eq__.side_effect = AssertionError("production touched a later fact")
    decision = authorize_today_preview(
        TodayPreviewGuardInput(
            app_env="  ProDucTion  ",
            marker_value=exploding,
            client_host=exploding,
            host=exploding,
            origin=exploding,
            forwarded=exploding,
            x_forwarded_for=exploding,
            x_forwarded_host=exploding,
            x_forwarded_port=exploding,
            x_real_ip=exploding,
            tg_user_id=exploding,
            tg_username=exploding,
        )
    )
    assert decision == TodayPreviewGuardDecision(
        authorized=False,
        reason=TodayPreviewGuardReason.PRODUCTION_DENIED,
    )

@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"app_env": "test"}, TodayPreviewGuardReason.APP_ENV_DENIED),
        ({"app_env": "dev"}, TodayPreviewGuardReason.APP_ENV_DENIED),
        ({"marker_value": None}, TodayPreviewGuardReason.MARKER_DENIED),
        ({"marker_value": "today-v2"}, TodayPreviewGuardReason.MARKER_DENIED),
        ({"client_host": None}, TodayPreviewGuardReason.CLIENT_DENIED),
        ({"client_host": "203.0.113.7"}, TodayPreviewGuardReason.CLIENT_DENIED),
        ({"host": "public.example:8000", "origin": None, "x_forwarded_for": "127.0.0.1", "x_forwarded_host": "127.0.0.1:3003", "x_forwarded_port": "3003"}, TodayPreviewGuardReason.HOST_DENIED),
        ({"host": "127.0.0.1"}, TodayPreviewGuardReason.PORT_DENIED),
        ({"host": "127.0.0.1:3000"}, TodayPreviewGuardReason.PORT_DENIED),
        ({"host": "127.0.0.1:not-a-port", "origin": None, "x_forwarded_for": "127.0.0.1", "x_forwarded_host": "127.0.0.1:3003", "x_forwarded_port": "3003"}, TodayPreviewGuardReason.HOST_DENIED),
        ({"origin": "https://example.com:3003"}, TodayPreviewGuardReason.ORIGIN_DENIED),
        ({"origin": "http://127.0.0.1:3000"}, TodayPreviewGuardReason.ORIGIN_DENIED),
        ({"x_forwarded_for": "127.0.0.1, 203.0.113.9"}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"x_forwarded_for": "127.0.0.1, not-an-ip"}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"x_real_ip": "203.0.113.9"}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"x_real_ip": "garbage"}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"x_forwarded_host": "example.com:3003"}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"x_forwarded_port": "3000"}, TodayPreviewGuardReason.PORT_DENIED),
        ({"forwarded": "for=203.0.113.9;host=127.0.0.1:3003"}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"forwarded": "for=unknown;host=127.0.0.1:3003"}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"forwarded": "for=_hidden;host=127.0.0.1:3003"}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"forwarded": 'for="[::1]'}, TodayPreviewGuardReason.FORWARDED_CHAIN_DENIED),
        ({"tg_user_id": 1}, TodayPreviewGuardReason.IDENTITY_DENIED),
        ({"tg_username": None}, TodayPreviewGuardReason.IDENTITY_DENIED),
        ({"tg_username": "Dev_User"}, TodayPreviewGuardReason.IDENTITY_DENIED),
    ],
    ids=lambda value: str(value),
)
def test_guard_denial_matrix(
    overrides: dict[str, Any],
    reason: TodayPreviewGuardReason,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_denial_matrix
    # purpose: Verify malformed, public, incomplete, wrong-port, and wrong-identity cases fail closed.
    # inputs: Parametrized guard overrides and expected closed denial reason.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Assertion failure on authorization or reason-order drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_denial_matrix
    assert authorize_today_preview(_guard_input(**overrides)) == TodayPreviewGuardDecision(
        authorized=False,
        reason=reason,
    )

@pytest.mark.parametrize(
    "overrides",
    [
        {"client_host": "localhost", "host": "localhost:3003", "origin": "http://localhost:3003"},
        {"client_host": "127.0.0.44", "host": "127.0.0.1:3003"},
        {"client_host": "::1", "host": "[::1]:3003", "origin": "http://[::1]:3003"},
        {"origin": None},
        {"x_forwarded_for": "127.0.0.1, 127.0.0.2", "x_real_ip": "127.0.0.3"},
        {
            "host": "127.0.0.1:8000",
            "origin": None,
            "x_forwarded_for": "127.0.0.1, ::1",
            "x_forwarded_host": "127.0.0.1:3003",
            "x_forwarded_port": "3003",
        },
        {
            "host": "127.0.0.1:8000",
            "origin": None,
            "forwarded": "for=127.0.0.1;host=127.0.0.1:3003",
        },
        {
            "host": "127.0.0.1:8000",
            "origin": None,
            "forwarded": 'for="[::1]";host="[::1]:3003"',
        },
    ],
    ids=["localhost", "ipv4-127-8", "ipv6", "direct-loopback", "xff-chain", "next-rewrite", "forwarded", "forwarded-ipv6"],
)
def test_guard_authorization_matrix(overrides: dict[str, Any]) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_authorization_matrix
    # purpose: Verify direct, rewritten, forwarded, IPv4, IPv6, and absent-Origin local proofs authorize.
    # inputs: Parametrized safe guard fact overrides.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Assertion failure if an approved closed proof is denied.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_authorization_matrix
    assert authorize_today_preview(_guard_input(**overrides)) == TodayPreviewGuardDecision(
        authorized=True,
        reason=TodayPreviewGuardReason.AUTHORIZED,
    )

def test_guard_decision_contains_no_raw_request_facts() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_decision_contains_no_raw_request_facts
    # purpose: Verify decisions expose only authorization and the closed reason.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Assertion failure if raw transport or identity storage is added.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_decision_contains_no_raw_request_facts
    assert {field.name for field in fields(TodayPreviewGuardDecision)} == {
        "authorized",
        "reason",
    }

def test_guard_module_is_pure_standard_library_only() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_module_is_pure_standard_library_only
    # purpose: Verify the guard imports no framework, configuration, database, logger, or ambient context.
    # inputs: none.
    # returns: none.
    # side_effects: Reads and parses the guard source file.
    # emitted_logs: none.
    # error_behavior: Assertion failure on any non-approved import or forbidden ambient token.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_guard_module_is_pure_standard_library_only
    path = Path(__file__).resolve().parents[1] / "app/services/today_preview_guard.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported_roots <= {"__future__", "dataclasses", "enum", "ipaddress", "urllib"}
    assert not any(token in source for token in ("ContextVar", "threading.local", "current_selection"))
# END_BLOCK: PURE_GUARD

# START_BLOCK: ROUTE_INTEGRATION
@pytest.mark.asyncio
async def test_route_exact_direct_preview_passes_local_v2_context_and_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_exact_direct_preview_passes_local_v2_context_and_identity
    # purpose: Verify exact local direct transport reaches TodayService as LOCAL_DEV_PREVIEW V2.
    # inputs: monkeypatch fixture for development settings and route test doubles.
    # returns: none.
    # side_effects: Executes one in-process ASGI request.
    # emitted_logs: none.
    # error_behavior: Assertion failure on HTTP, context, or current V2 identity drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_exact_direct_preview_passes_local_v2_context_and_identity
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    recorder = _RouteTodayService()
    response = await _route_get(
        _build_route_app(monkeypatch, recorder),
        headers={TODAY_PREVIEW_HEADER_NAME: TODAY_PREVIEW_HEADER_VALUE},
    )
    assert response.status_code == 200
    assert recorder.contexts == [TodaySelectionContext(
        force_v2=True,
        source=TodaySelectionSource.LOCAL_DEV_PREVIEW,
    )]
    assert response.json()["meta"]["scoringVersion"] == SCORING_V2_VERSION
    assert response.json()["v2"]["audit"]["horizonPipeline"]["status"] == "unavailable"
    assert response.json()["v2"]["horizons"] is None

@pytest.mark.asyncio
async def test_route_next_rewrite_preview_passes_local_v2_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_next_rewrite_preview_passes_local_v2_context
    # purpose: Verify the canonical loopback Next rewrite proof authorizes local preview V2.
    # inputs: monkeypatch fixture for development settings and route test doubles.
    # returns: none.
    # side_effects: Executes one in-process ASGI request with forwarded headers.
    # emitted_logs: none.
    # error_behavior: Assertion failure on HTTP or request selection drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_next_rewrite_preview_passes_local_v2_context
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    recorder = _RouteTodayService()
    response = await _route_get(
        _build_route_app(monkeypatch, recorder),
        base_url="http://127.0.0.1:8000",
        headers={
            TODAY_PREVIEW_HEADER_NAME: TODAY_PREVIEW_HEADER_VALUE,
            "X-Forwarded-For": "127.0.0.1, ::1",
            "X-Forwarded-Host": "127.0.0.1:3003",
            "X-Forwarded-Port": "3003",
        },
    )
    assert response.status_code == 200
    assert recorder.contexts[0].source is TodaySelectionSource.LOCAL_DEV_PREVIEW
    assert recorder.contexts[0].force_v2 is True

@pytest.mark.parametrize(
    "case",
    ["missing", "wrong", "query-only", "ordinary-user", "public-forwarded", "wrong-port", "production"],
)
@pytest.mark.asyncio
async def test_route_denials_continue_with_ordinary_global_context(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_denials_continue_with_ordinary_global_context
    # purpose: Verify denied preview attempts continue normally with global V1 rather than HTTP 403.
    # inputs: monkeypatch plus a parametrized missing/wrong/query/identity/transport/environment case.
    # returns: none.
    # side_effects: Executes one in-process ASGI request per collected case.
    # emitted_logs: none.
    # error_behavior: Assertion failure on denial handling, source, or V1 identity drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_denials_continue_with_ordinary_global_context
    monkeypatch.setattr(settings, "app_env", "production" if case == "production" else "development")
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    headers: dict[str, str] = {}
    base_url = "http://127.0.0.1:3003"
    params = None
    user = _route_user(exact_identity=case != "ordinary-user")
    if case not in {"missing", "query-only"}:
        headers[TODAY_PREVIEW_HEADER_NAME] = (
            "wrong" if case == "wrong" else TODAY_PREVIEW_HEADER_VALUE
        )
    if case == "query-only":
        params = {"preview": "today-v2-real", "v2": "1", "fixture": "1"}
    if case == "public-forwarded":
        headers["X-Forwarded-For"] = "127.0.0.1, 203.0.113.9"
    if case == "wrong-port":
        base_url = "http://127.0.0.1:3000"
    recorder = _RouteTodayService()
    response = await _route_get(
        _build_route_app(monkeypatch, recorder, user=user),
        base_url=base_url,
        headers=headers,
        params=params,
    )
    assert response.status_code == 200
    assert recorder.contexts == [TodaySelectionContext(
        force_v2=False,
        source=TodaySelectionSource.GLOBAL_FLAGS,
    )]
    assert response.json()["meta"]["scoringVersion"] == LEGACY_SCORING_VERSION
    assert response.json()["v2"] is None

@pytest.mark.asyncio
async def test_route_global_v2_without_preview_uses_global_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_global_v2_without_preview_uses_global_source
    # purpose: Verify global V2 enablement selects V2 without claiming local preview provenance.
    # inputs: monkeypatch fixture for development environment and global V2 flag.
    # returns: none.
    # side_effects: Executes one in-process ASGI request.
    # emitted_logs: none.
    # error_behavior: Assertion failure on context source, force value, or response identity.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_global_v2_without_preview_uses_global_source
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    recorder = _RouteTodayService()
    response = await _route_get(_build_route_app(monkeypatch, recorder))
    assert response.status_code == 200
    assert recorder.contexts == [TodaySelectionContext(
        force_v2=True,
        source=TodaySelectionSource.GLOBAL_FLAGS,
    )]
    assert response.json()["meta"]["scoringVersion"] == SCORING_V2_VERSION

@pytest.mark.asyncio
async def test_overlapping_route_calls_keep_independent_contexts_and_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_overlapping_route_calls_keep_independent_contexts_and_globals
    # purpose: Prove overlapping local-preview and ordinary ASGI calls retain independent explicit contexts.
    # inputs: monkeypatch fixture for stable development/global settings.
    # returns: none.
    # side_effects: Executes two synchronized in-process ASGI requests concurrently.
    # emitted_logs: none.
    # error_behavior: Assertion failure on response, context set, overlap, or global-state drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_overlapping_route_calls_keep_independent_contexts_and_globals
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    recorder = _RouteTodayService(overlap_count=2)
    route_app = _build_route_app(monkeypatch, recorder)
    preview_response, ordinary_response = await asyncio.gather(
        _route_get(
            route_app,
            headers={TODAY_PREVIEW_HEADER_NAME: TODAY_PREVIEW_HEADER_VALUE},
        ),
        _route_get(route_app),
    )
    assert preview_response.status_code == ordinary_response.status_code == 200
    assert {(context.force_v2, context.source) for context in recorder.contexts} == {
        (True, TodaySelectionSource.LOCAL_DEV_PREVIEW),
        (False, TodaySelectionSource.GLOBAL_FLAGS),
    }
    assert settings.solarsage_v2_enabled is False
# END_BLOCK: ROUTE_INTEGRATION

# START_BLOCK: SERVICE_BOUNDARIES
@pytest.mark.parametrize(
    ("selection_context", "expected_version"),
    [
        (
            TodaySelectionContext(True, TodaySelectionSource.LOCAL_DEV_PREVIEW),
            SCORING_V2_VERSION,
        ),
        (None, LEGACY_SCORING_VERSION),
    ],
    ids=["forced-v2", "default-v1"],
)
@pytest.mark.asyncio
async def test_service_passes_explicit_selected_family_to_cache_read(
    monkeypatch: pytest.MonkeyPatch,
    selection_context: TodaySelectionContext | None,
    expected_version: int | str,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_passes_explicit_selected_family_to_cache_read
    # purpose: Verify forced V2 and default V1 become explicit pre-cache identity authorities.
    # inputs: monkeypatch plus parametrized selection context and expected scoring version.
    # returns: none.
    # side_effects: Runs TodayService to a deterministic cache-read stop with boundary mocks.
    # emitted_logs: none.
    # error_behavior: Expected BoundaryStop ends the pipeline; assertions expose authority drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_passes_explicit_selected_family_to_cache_read
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    harness = _install_service_harness(
        monkeypatch,
        runtime_selected_version=expected_version,
    )
    identity_spy = MagicMock(wraps=today_service_module.expected_cache_identity)
    monkeypatch.setattr(today_service_module, "expected_cache_identity", identity_spy)
    harness.service._get_cached_payload.side_effect = _BoundaryStop("after cache authority")
    with pytest.raises(_BoundaryStop, match="after cache authority"):
        await harness.service.get_today_payload(
            uuid4(),
            Date(2026, 7, 13),
            ContentAccessState(state="full"),
            selection_context=selection_context,
        )
    assert identity_spy.call_args.kwargs["selected_scoring_version"] == expected_version
    assert settings.solarsage_v2_enabled is False

@pytest.mark.asyncio
async def test_service_forced_context_activates_sidecar_and_runtime_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_forced_context_activates_sidecar_and_runtime_force
    # purpose: Verify forced preview activates V2 compute, sidecar, and force_v2 runtime propagation.
    # inputs: monkeypatch fixture for disabled global rollout and service boundary doubles.
    # returns: none.
    # side_effects: Runs TodayService through runtime compute to a deterministic identity stop.
    # emitted_logs: none.
    # error_behavior: Expected BoundaryStop ends the pipeline; assertions expose missing propagation.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_forced_context_activates_sidecar_and_runtime_force
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)
    harness = _install_service_harness(
        monkeypatch,
        runtime_selected_version=SCORING_V2_VERSION,
    )
    compute_spy = MagicMock(wraps=today_service_module.should_compute_v2)
    monkeypatch.setattr(today_service_module, "should_compute_v2", compute_spy)
    monkeypatch.setattr(
        today_service_module,
        "resolve_today_runtime_identity",
        MagicMock(side_effect=_BoundaryStop("after runtime")),
    )
    with pytest.raises(_BoundaryStop, match="after runtime"):
        await harness.service.get_today_payload(
            uuid4(),
            Date(2026, 7, 13),
            ContentAccessState(state="full"),
            selection_context=TodaySelectionContext(
                True,
                TodaySelectionSource.LOCAL_DEV_PREVIEW,
            ),
        )
    compute_spy.assert_called_once_with(force_v2=True)
    harness.client.get_activation_layer.assert_awaited_once()
    assert harness.runtime_class.return_value.compute.call_args.kwargs["force_v2"] is True
    assert settings.solarsage_v2_enabled is False

@pytest.mark.asyncio
async def test_service_forced_activation_failure_reraises_without_global_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_forced_activation_failure_reraises_without_global_mutation
    # purpose: Verify request-selected V2 activation failure is fail-loud like global V2.
    # inputs: monkeypatch fixture and a deterministic sidecar activation error.
    # returns: none.
    # side_effects: Runs TodayService until the mocked activation call fails.
    # emitted_logs: none.
    # error_behavior: Re-raises the exact activation RuntimeError.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_forced_activation_failure_reraises_without_global_mutation
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    harness = _install_service_harness(
        monkeypatch,
        runtime_selected_version=SCORING_V2_VERSION,
        activation_error=RuntimeError("activation unavailable"),
    )
    with pytest.raises(RuntimeError, match="activation unavailable"):
        await harness.service.get_today_payload(
            uuid4(),
            Date(2026, 7, 13),
            ContentAccessState(state="full"),
            selection_context=TodaySelectionContext(
                True,
                TodaySelectionSource.LOCAL_DEV_PREVIEW,
            ),
        )
    assert settings.solarsage_v2_enabled is False

@pytest.mark.asyncio
async def test_service_shadow_activation_failure_remains_fail_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_shadow_activation_failure_remains_fail_open
    # purpose: Verify dual-run-only activation failure continues into the existing local fallback path.
    # inputs: monkeypatch fixture and a deterministic shadow sidecar activation error.
    # returns: none.
    # side_effects: Runs TodayService until the mocked post-fallback activation build stop.
    # emitted_logs: none from test doubles.
    # error_behavior: Expected BoundaryStop proves the sidecar error was swallowed only in shadow mode.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_shadow_activation_failure_remains_fail_open
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    harness = _install_service_harness(
        monkeypatch,
        runtime_selected_version=LEGACY_SCORING_VERSION,
        activation_error=RuntimeError("shadow activation unavailable"),
    )
    harness.activation_class.return_value.build.side_effect = _BoundaryStop("shadow fallback reached")
    with pytest.raises(_BoundaryStop, match="shadow fallback reached"):
        await harness.service.get_today_payload(
            uuid4(),
            Date(2026, 7, 13),
            ContentAccessState(state="full"),
        )
    assert settings.solarsage_v2_enabled is False
    assert settings.solarsage_v2_dual_run is True

@pytest.mark.asyncio
async def test_service_split_brain_fails_before_identity_and_cache_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_split_brain_fails_before_identity_and_cache_write
    # purpose: Verify runtime/pre-cache family mismatch fails closed before public identity or cache write.
    # inputs: monkeypatch fixture with forced V2 preselection and a mismatching V1 runtime result.
    # returns: none.
    # side_effects: Runs TodayService through the runtime split-brain assertion.
    # emitted_logs: none.
    # error_behavior: Raises the fixed safe split-brain RuntimeError.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_split_brain_fails_before_identity_and_cache_write
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    harness = _install_service_harness(
        monkeypatch,
        runtime_selected_version=LEGACY_SCORING_VERSION,
    )
    identity_spy = MagicMock(side_effect=AssertionError("identity must not resolve"))
    monkeypatch.setattr(today_service_module, "resolve_today_runtime_identity", identity_spy)
    with pytest.raises(RuntimeError, match="^Today scoring selection split-brain detected$"):
        await harness.service.get_today_payload(
            uuid4(),
            Date(2026, 7, 13),
            ContentAccessState(state="full"),
            selection_context=TodaySelectionContext(
                True,
                TodaySelectionSource.LOCAL_DEV_PREVIEW,
            ),
        )
    identity_spy.assert_not_called()
    harness.service._cache_payload.assert_not_awaited()
    assert settings.solarsage_v2_enabled is False


def test_today_service_has_no_background_week_prefetch_surface() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_today_service_has_no_background_week_prefetch_surface
    # purpose: Prove that TodayService has no background week prefetch tasks or helper methods.
    # inputs: none.
    # returns: none.
    # side_effects: reads today_service.py source.
    # emitted_logs: none.
    # error_behavior: pytest assertion failure on prefetch code presence.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_today_service_has_no_background_week_prefetch_surface
    source = inspect.getsource(today_service_module)
    assert "_prefetch_week" not in source
    assert "_TODAY_PREFETCH_TASKS" not in source
    assert "asyncio.create_task" not in source
    assert "asyncio.gather" not in source
    assert "SessionLocal" not in source
# END_BLOCK: SERVICE_BOUNDARIES


# START_BLOCK: STATIC_GUARDS
def test_service_signature_keeps_context_keyword_only_and_optional() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_signature_keeps_context_keyword_only_and_optional
    # purpose: Verify existing callers remain compatible while selection context stays explicit and keyword-only.
    # inputs: none.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Assertion failure on signature compatibility drift.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_service_signature_keeps_context_keyword_only_and_optional
    signature = inspect.signature(TodayService.get_today_payload)
    parameter = signature.parameters["selection_context"]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is None
    assert signature.parameters["skip_prefetch"].default is False


def test_w2_sources_have_no_ambient_selection_or_settings_mutation() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_w2_sources_have_no_ambient_selection_or_settings_mutation
    # purpose: Verify W2 implementation avoids ambient request state and global configuration mutation.
    # inputs: none.
    # returns: none.
    # side_effects: Reads and parses the four backend implementation sources.
    # emitted_logs: none.
    # error_behavior: Assertion failure on forbidden context or configuration assignment.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_w2_sources_have_no_ambient_selection_or_settings_mutation
    api_root = Path(__file__).resolve().parents[1] / "app"
    paths = [
        api_root / "services/today_preview_guard.py",
        api_root / "api/day.py",
        api_root / "services/today_service.py",
        api_root / "services/today_selection_context.py",
    ]
    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert not any(token in source for token in ("ContextVar", "threading.local", "current_selection"))
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


def test_route_and_frontend_selectors_remain_closed() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_and_frontend_selectors_remain_closed
    # purpose: Verify query/cookie/Referer are not selectors and calendar never gains the marker.
    # inputs: none.
    # returns: none.
    # side_effects: Reads route and frontend client source files.
    # emitted_logs: none.
    # error_behavior: Assertion failure if forbidden selectors or calendar marker emission appear.
    # END_FUNCTION_CONTRACT: F-M-TEST-TODAY-PREVIEW-TRANSPORT.test_route_and_frontend_selectors_remain_closed
    repo_root = Path(__file__).resolve().parents[3]
    route_source = (repo_root / "apps/api/app/api/day.py").read_text(encoding="utf-8")
    client_source = (repo_root / "lib/grace/api/client.ts").read_text(encoding="utf-8")
    route_tree = ast.parse(route_source)
    assert not any(
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "request"
        and node.attr in {"query_params", "cookies"}
        for node in ast.walk(route_tree)
    )
    assert 'request.headers.get("Referer")' not in route_source
    calendar_source = client_source.split("export async function fetchCalendar", 1)[1]
    assert "TODAY_PREVIEW_HEADER_NAME" not in calendar_source
    assert "TODAY_PREVIEW_HEADER_VALUE" not in calendar_source
    assert "fixture" not in client_source.lower()
    assert "demo" not in client_source.lower()
# END_BLOCK: STATIC_GUARDS
