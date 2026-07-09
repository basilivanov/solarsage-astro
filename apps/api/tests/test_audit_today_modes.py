"""W9 tests: audit mode split and artifact_source honesty."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from scripts import audit_today as audit_mod  # noqa: E402


def test_resolve_audit_mode_fail_fast_without_mode():
    args = SimpleNamespace(mode=None, live_llm_sample=False, frozen_baseline=False)
    with pytest.raises(SystemExit, match="audit mode is required"):
        audit_mod.resolve_audit_mode(args)


def test_resolve_audit_mode_explicit_and_aliases():
    assert audit_mod.resolve_audit_mode(SimpleNamespace(mode="live-production", live_llm_sample=False, frozen_baseline=False)) == "live-production"
    assert audit_mod.resolve_audit_mode(SimpleNamespace(mode="frozen-baseline", live_llm_sample=False, frozen_baseline=False)) == "frozen-baseline"
    assert audit_mod.resolve_audit_mode(SimpleNamespace(mode=None, live_llm_sample=True, frozen_baseline=False)) == "live-production"
    assert audit_mod.resolve_audit_mode(SimpleNamespace(mode=None, live_llm_sample=False, frozen_baseline=True)) == "frozen-baseline"


def test_parse_args_accepts_mode():
    args = audit_mod.parse_args([
        "--user-id", "u1",
        "--date", "2026-07-08",
        "--out", "/tmp/out",
        "--mode", "live-production",
    ])
    assert args.mode == "live-production"
    assert args.user_id == "u1"


@pytest.mark.asyncio
async def test_live_mode_calls_today_service_and_writes_artifact_source(tmp_path, monkeypatch):
    """live-production must call TodayService.get_today_payload and label source honestly."""
    out = tmp_path / "audit"
    out.mkdir()

    class FakePayload:
        def model_dump(self, mode="json", by_alias=False):
            return {
                "meta": {"generated_at": "2026-07-08T10:00:00Z", "cached": True},
                "headline": "live",
                "day_status": "steady",
                "concrete_advice": {"rows": []},
                "why_this_happens": {"sections": []},
            }

    fake_user = SimpleNamespace(id="user-1", tg_user_id=1, tg_username="u")
    fake_profile = SimpleNamespace(
        is_onboarded=True,
        gender="female",
        birthday=MagicMock(isoformat=lambda: "1990-01-15"),
        birth_time=MagicMock(strftime=lambda fmt: "12:00"),
        birth_city="Moscow",
        birth_lat=55.75,
        birth_lon=37.61,
        birth_tz="Europe/Moscow",
        current_city="Moscow",
        current_lat=55.75,
        current_lon=37.61,
        current_tz="Europe/Moscow",
    )

    mock_client = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value={"planets": []})
    mock_client.get_activation_layer = AsyncMock(return_value={
        "schema_version": "activation-layer.v1",
        "activation_layer_version": "al-1.0",
        "calculation_version": "ss-calc-1.1.0",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
        "activations": [{
            "id": "t2n__SUN__MOON",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "target_type": "planet",
            "target_key": "MOON",
            "kind": "aspect",
            "strength": 0.5,
            "evidence": "test",
            "phase": "background",
            "polarity": "neutral",
        }],
        "by_planet": {"MOON": ["t2n__SUN__MOON"]},
        "by_house": {},
        "by_lot": {},
        "by_angle": {},
        "warnings": [],
    })
    mock_client.close = AsyncMock()

    today_svc = MagicMock()
    today_svc.invalidate_cache = AsyncMock()
    today_svc.get_today_payload = AsyncMock(return_value=FakePayload())

    class FakeNatal:
        def model_dump(self, mode="json", by_alias=False):
            return {"house_system": "PLACIDUS", "planets": [], "houses": []}

    class FakeNatalService:
        def __init__(self, db=None):
            pass

        async def get_or_build_natal_context(self, user_id):
            return FakeNatal()

        @staticmethod
        def compute_profile_hash(profile):
            return "hash"

    access_svc = MagicMock()
    access_svc.can_access_day = AsyncMock(return_value=SimpleNamespace(state="subscription"))

    class _CM:
        async def __aenter__(self):
            return MagicMock()
        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(audit_mod, "SessionLocal", lambda: _CM())
    monkeypatch.setattr(audit_mod, "load_user_and_profile", AsyncMock(return_value=(fake_user, fake_profile)))
    monkeypatch.setattr(audit_mod, "load_raw_natal_sidecar", AsyncMock(return_value=None))
    monkeypatch.setattr(audit_mod, "get_solarsage_client", lambda: mock_client)
    monkeypatch.setattr(audit_mod, "AccessService", lambda db: access_svc)
    monkeypatch.setattr(audit_mod, "NatalContextService", FakeNatalService)
    monkeypatch.setattr(audit_mod, "NormalizationService", lambda: MagicMock(normalize_day=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "DayDeltaService", lambda a, b: MagicMock(compute_deltas=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "filter_day_scored_signals", lambda s: [])
    monkeypatch.setattr(audit_mod, "ScoringService", lambda: MagicMock(score_day=MagicMock(return_value={
        "day_status": "steady", "sphere_scores": {}, "top_signals": [],
    })))
    monkeypatch.setattr(audit_mod, "SemanticService", lambda: MagicMock(
        build_semantic_layer=MagicMock(return_value={}),
        build_why_contexts=MagicMock(return_value={}),
    ))
    monkeypatch.setattr(audit_mod, "TodayService", lambda db: today_svc)
    monkeypatch.setattr(audit_mod, "run_oracles", AsyncMock())

    # Ensure intermediate oracle files exist so copy steps don't fail hard.
    async def _oracles(**kwargs):
        d = kwargs["out_dir"]
        (d / "scoring_intermediate_table.csv").write_text("x\n", encoding="utf-8")
        (d / "scoring_oracle_comparison.json").write_text("{}", encoding="utf-8")
        (d / "astronomy_oracle_summary.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audit_mod, "run_oracles", _oracles)

    args = audit_mod.parse_args([
        "--user-id", "user-1",
        "--date", "2026-07-08",
        "--out", str(out),
        "--mode", "live-production",
        "--skip-oracles",
    ])
    args.resolved_mode = "live-production"

    summary = await audit_mod.run_audit(args)

    today_svc.get_today_payload.assert_awaited()
    today_svc.invalidate_cache.assert_awaited()
    mock_client.get_activation_layer.assert_awaited()
    assert summary["mode"] == "live-production"
    assert summary["final_payload_source"] == "TodayService.get_today_payload"
    assert summary["activation_layer_source"] == "sidecar"

    # live writes under out/live/<ts>/
    live_roots = list((out / "live").glob("*"))
    assert live_roots
    src = json.loads((live_roots[0] / "artifact_source.json").read_text(encoding="utf-8"))
    assert src["mode"] == "live-production"
    assert src["final_payload_source"] == "TodayService.get_today_payload"
    assert src["activation_layer_source"] == "sidecar"
    assert (live_roots[0] / "16_activation_layer.json").exists()


@pytest.mark.asyncio
async def test_frozen_mode_does_not_call_today_service(tmp_path, monkeypatch):
    """frozen-baseline must use committed fixture and not call TodayService."""
    out = tmp_path / "audit"
    out.mkdir()
    baseline = {
        "meta": {"generated_at": "2026-07-08T12:00:00Z"},
        "headline": "frozen",
        "day_status": "steady",
        "concrete_advice": {"rows": []},
        "why_this_happens": {"sections": []},
    }
    (out / "11_final_today_payload.json").write_text(json.dumps(baseline), encoding="utf-8")

    fake_user = SimpleNamespace(id="user-1", tg_user_id=1, tg_username="u")
    fake_profile = SimpleNamespace(
        is_onboarded=True,
        gender="female",
        birthday=MagicMock(isoformat=lambda: "1990-01-15"),
        birth_time=MagicMock(strftime=lambda fmt: "12:00"),
        birth_city="Moscow",
        birth_lat=55.75,
        birth_lon=37.61,
        birth_tz="Europe/Moscow",
        current_city="Moscow",
        current_lat=55.75,
        current_lon=37.61,
        current_tz="Europe/Moscow",
    )

    mock_client = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value={"planets": []})
    mock_client.get_activation_layer = AsyncMock(return_value={
        "schema_version": "activation-layer.v1",
        "activation_layer_version": "al-1.0",
        "calculation_version": "ss-calc-1.1.0",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
        "activations": [{
            "id": "t2n__SUN__MOON",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "target_type": "planet",
            "target_key": "MOON",
            "kind": "aspect",
            "strength": 0.5,
            "evidence": "test",
            "phase": "background",
            "polarity": "neutral",
        }],
        "by_planet": {"MOON": ["t2n__SUN__MOON"]},
        "by_house": {},
        "by_lot": {},
        "by_angle": {},
        "warnings": [],
    })
    mock_client.close = AsyncMock()

    today_svc = MagicMock()
    today_svc.invalidate_cache = AsyncMock()
    today_svc.get_today_payload = AsyncMock()

    class FakeNatal:
        def model_dump(self, mode="json", by_alias=False):
            return {"house_system": "PLACIDUS", "planets": [], "houses": []}

    class FakeNatalService:
        def __init__(self, db=None):
            pass

        async def get_or_build_natal_context(self, user_id):
            return FakeNatal()

        @staticmethod
        def compute_profile_hash(profile):
            return "hash"

    access_svc = MagicMock()
    access_svc.can_access_day = AsyncMock(return_value=SimpleNamespace(state="subscription"))

    class _CM:
        async def __aenter__(self):
            return MagicMock()
        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(audit_mod, "SessionLocal", lambda: _CM())
    monkeypatch.setattr(audit_mod, "load_user_and_profile", AsyncMock(return_value=(fake_user, fake_profile)))
    monkeypatch.setattr(audit_mod, "load_raw_natal_sidecar", AsyncMock(return_value=None))
    monkeypatch.setattr(audit_mod, "get_solarsage_client", lambda: mock_client)
    monkeypatch.setattr(audit_mod, "AccessService", lambda db: access_svc)
    monkeypatch.setattr(audit_mod, "NatalContextService", FakeNatalService)
    monkeypatch.setattr(audit_mod, "NormalizationService", lambda: MagicMock(normalize_day=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "DayDeltaService", lambda a, b: MagicMock(compute_deltas=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "filter_day_scored_signals", lambda s: [])
    monkeypatch.setattr(audit_mod, "ScoringService", lambda: MagicMock(score_day=MagicMock(return_value={
        "day_status": "steady", "sphere_scores": {}, "top_signals": [],
    })))
    monkeypatch.setattr(audit_mod, "SemanticService", lambda: MagicMock(
        build_semantic_layer=MagicMock(return_value={}),
        build_why_contexts=MagicMock(return_value={}),
    ))
    monkeypatch.setattr(audit_mod, "TodayService", lambda db: today_svc)

    async def _oracles(**kwargs):
        d = kwargs["out_dir"]
        (d / "scoring_intermediate_table.csv").write_text("x\n", encoding="utf-8")
        (d / "scoring_oracle_comparison.json").write_text("{}", encoding="utf-8")
        (d / "astronomy_oracle_summary.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audit_mod, "run_oracles", _oracles)

    args = audit_mod.parse_args([
        "--user-id", "user-1",
        "--date", "2026-07-08",
        "--out", str(out),
        "--mode", "frozen-baseline",
        "--skip-oracles",
    ])
    args.resolved_mode = "frozen-baseline"

    summary = await audit_mod.run_audit(args)

    today_svc.get_today_payload.assert_not_called()
    assert summary["mode"] == "frozen-baseline"
    assert summary["final_payload_source"] == "committed_baseline_fixture"
    src = json.loads((out / "artifact_source.json").read_text(encoding="utf-8"))
    assert src["final_payload_source"] == "committed_baseline_fixture"
    assert src["activation_layer_source"] == "sidecar"
    claims = (out / "14_claims_audit.md").read_text(encoding="utf-8")
    assert "frozen baseline payload review" in claims.lower()
