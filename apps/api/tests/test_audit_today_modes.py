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


def test_summary_out_dir_frozen_is_repo_relative_across_checkout_roots():
    """Frozen baseline must not leak the absolute checkout root into the
    committed artifact (run 29945668331: /opt/solarsage-astro vs runner)."""
    f = audit_mod.summary_out_dir_provenance
    assert (
        f(Path("/opt/solarsage-astro/artifacts/audit/2026-07-08"), False, repo_root=Path("/opt/solarsage-astro"))
        == "artifacts/audit/2026-07-08"
    )
    runner_root = Path("/home/runner/work/solarsage-astro/solarsage-astro")
    assert (
        f(runner_root / "artifacts/audit/2026-07-08", False, repo_root=runner_root)
        == "artifacts/audit/2026-07-08"
    )


def test_summary_out_dir_live_keeps_actual_absolute_path():
    p = Path("/opt/solarsage-astro/artifacts/audit/2026-07-08")
    assert audit_mod.summary_out_dir_provenance(p, True, repo_root=Path("/opt/solarsage-astro")) == str(p)


def test_summary_out_dir_frozen_outside_repo_falls_back_to_absolute():
    p = Path("/tmp/external-audit-out")
    assert audit_mod.summary_out_dir_provenance(p, False, repo_root=Path("/opt/solarsage-astro")) == str(p)


@pytest.mark.asyncio
async def test_live_mode_calls_today_service_and_writes_artifact_source(tmp_path, monkeypatch):
    """live-production must call TodayService.get_today_payload and label source honestly."""
    out = tmp_path / "audit"
    out.mkdir()

    class FakePayload:
        def model_dump(self, mode="json", by_alias=False):
            return {
                "meta": {
                    "generated_at": "2026-07-08T10:00:00Z",
                    "cached": True,
                    "scoring_version": "ss-scoring-2.0",
                    "payload_version": "today.v2",
                    "frontend_payload_version": 2,
                },
                "headline": "live",
                "day_status": "steady",
                "concrete_advice": {"rows": []},
                "why_this_happens": {"sections": []},
                "v2": {
                    "activation_evidence": [{
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
                },
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
    monkeypatch.setattr(audit_mod, "run_downstream_audit_step", lambda *a, **k: None)

    # Ensure intermediate oracle files exist so copy steps don't fail hard.
    async def _oracles(**kwargs):
        d = kwargs["out_dir"]
        (d / "scoring_intermediate_table.csv").write_text("x\n", encoding="utf-8")
        (d / "scoring_oracle_comparison.json").write_text("{}", encoding="utf-8")
        (d / "astronomy_oracle_summary.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audit_mod, "run_oracles", _oracles)
    monkeypatch.setattr(audit_mod, "run_downstream_audit_step", lambda *a, **k: None)

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
    from tests.test_today_horizons_contract import build_complete_today_payload

    out = tmp_path / "audit"
    out.mkdir()
    baseline = build_complete_today_payload(
        payload_version="today.v1",
        frontend_payload_version=1,
        audit_payload_version="today.v1",
        include_pipeline_audit=False,
    )
    baseline["v2"] = None
    baseline["headline"] = "frozen"
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

    oracle_saw_payload = {"ok": False}

    async def _oracles(**kwargs):
        d = kwargs["out_dir"]
        # Regression: frozen mode must materialize baseline payload before oracles.
        payload_path = d / "final_today_payload.json"
        assert payload_path.exists(), (
            "frozen-baseline must write debug/final_today_payload.json before run_oracles"
        )
        loaded = json.loads(payload_path.read_text(encoding="utf-8"))
        assert loaded.get("headline") == "frozen"
        oracle_saw_payload["ok"] = True
        (d / "scoring_intermediate_table.csv").write_text("x\n", encoding="utf-8")
        (d / "scoring_oracle_comparison.json").write_text("{}", encoding="utf-8")
        (d / "astronomy_oracle_summary.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audit_mod, "run_oracles", _oracles)
    monkeypatch.setattr(audit_mod, "run_downstream_audit_step", lambda *a, **k: None)

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
    assert (out / "debug" / "final_today_payload.json").exists()
    assert (out / "debug" / "final_today_payload.normalized.json").exists()
    assert oracle_saw_payload["ok"] is True

    # Frozen-baseline mapping proof: non-live status, both artifacts present.
    root_mapping_path = out / "activation_evidence_mapping.json"
    debug_mapping_path = out / "debug" / "activation_evidence_mapping.json"
    assert root_mapping_path.exists()
    assert debug_mapping_path.exists()
    root_mapping = json.loads(root_mapping_path.read_text(encoding="utf-8"))
    debug_mapping = json.loads(debug_mapping_path.read_text(encoding="utf-8"))
    assert root_mapping["mode"] == "frozen-baseline"
    assert root_mapping["status"] == "frozen_baseline_not_live"
    assert debug_mapping["status"] == "frozen_baseline_not_live"
    assert root_mapping.get("accepted_unmapped") is True
    # Must not claim live production proof through mapping.
    assert root_mapping["status"] != "ok" or root_mapping["mode"] != "live-production"
# W9 rework01 regression: frozen payload before oracles


@pytest.mark.asyncio
async def test_live_audit_records_v2_runtime_flags(tmp_path, monkeypatch):
    out = tmp_path / "audit"
    out.mkdir()

    class FakePayload:
        def model_dump(self, mode="json", by_alias=False):
            return {
                "meta": {
                    "scoring_version": "ss-scoring-2.0",
                    "payload_version": "today.v2.1",
                    "frontend_payload_version": 3,
                },
                "headline": "live",
                "day_status": "steady",
                "concrete_advice": {},
                "why_this_happens": {},
                "v2": {
                    "activation_evidence": [{
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
                },
            }

    fake_user = SimpleNamespace(id="user-1", tg_user_id=1, tg_username="u")
    fake_profile = SimpleNamespace(
        is_onboarded=True, gender="female",
        birthday=MagicMock(isoformat=lambda: "1990-01-15"),
        birth_time=MagicMock(strftime=lambda fmt: "12:00"),
        birth_city="Moscow", birth_lat=55.75, birth_lon=37.61, birth_tz="Europe/Moscow",
        current_city="Moscow", current_lat=55.75, current_lon=37.61, current_tz="Europe/Moscow",
    )
    mock_client = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value={"planets": []})
    mock_client.get_activation_layer = AsyncMock(return_value={
        "schema_version": "activation-layer.v1",
        "activation_layer_version": "al-1.0",
        "calculation_version": "ss-calc-1.1.0",
        "target_date": "2026-07-08", "target_time": "12:00", "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
        "activations": [{
            "id": "t2n__SUN__MOON", "technique": "transit_to_natal", "technique_family": "transit",
            "target_type": "planet", "target_key": "MOON", "kind": "aspect", "strength": 0.5,
            "evidence": "test", "phase": "background", "polarity": "neutral",
        }],
        "by_planet": {"MOON": ["t2n__SUN__MOON"]}, "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
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

    class _CM:
        async def __aenter__(self):
            return MagicMock()
        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(audit_mod, "SessionLocal", lambda: _CM())
    monkeypatch.setattr(audit_mod, "load_user_and_profile", AsyncMock(return_value=(fake_user, fake_profile)))
    monkeypatch.setattr(audit_mod, "load_raw_natal_sidecar", AsyncMock(return_value=None))
    monkeypatch.setattr(audit_mod, "get_solarsage_client", lambda: mock_client)
    monkeypatch.setattr(audit_mod, "AccessService", lambda db: MagicMock(can_access_day=AsyncMock(return_value=SimpleNamespace(state="subscription"))))
    monkeypatch.setattr(audit_mod, "NatalContextService", FakeNatalService)
    monkeypatch.setattr(audit_mod, "NormalizationService", lambda: MagicMock(normalize_day=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "DayDeltaService", lambda a, b: MagicMock(compute_deltas=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "filter_day_scored_signals", lambda s: [])
    monkeypatch.setattr(audit_mod, "ScoringService", lambda: MagicMock(score_day=MagicMock(return_value={"day_status": "steady", "sphere_scores": {}, "top_signals": []})))
    monkeypatch.setattr(audit_mod, "SemanticService", lambda: MagicMock(build_semantic_layer=MagicMock(return_value={}), build_why_contexts=MagicMock(return_value={})))
    monkeypatch.setattr(audit_mod, "TodayService", lambda db: today_svc)

    async def _oracles(**kwargs):
        d = kwargs["out_dir"]
        (d / "scoring_intermediate_table.csv").write_text("x\n", encoding="utf-8")
        (d / "scoring_oracle_comparison.json").write_text("{}", encoding="utf-8")
        (d / "astronomy_oracle_summary.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audit_mod, "run_oracles", _oracles)
    monkeypatch.setattr(audit_mod, "run_downstream_audit_step", lambda *a, **k: None)

    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "solarsage_v2_enabled", True)
    monkeypatch.setattr(cfg.settings, "solarsage_v2_dual_run", False)
    monkeypatch.setattr(cfg.settings, "solarsage_v2_frontend_enabled", False)

    args = audit_mod.parse_args(["--user-id", "user-1", "--date", "2026-07-08", "--out", str(out), "--mode", "live-production", "--skip-oracles"])
    args.resolved_mode = "live-production"
    await audit_mod.run_audit(args)

    live_roots = list((out / "live").glob("*"))
    assert live_roots
    src = json.loads((live_roots[0] / "artifact_source.json").read_text(encoding="utf-8"))
    assert src["solarsage_v2_enabled"] is True
    assert src["solarsage_v2_frontend_enabled"] is False
    assert src["selected_scoring_version"] == "ss-scoring-2.0"
    assert src["final_payload_version"] == "today.v2.1"
    assert src["final_frontend_payload_version"] == 3
    assert src["final_has_v2_block"] is True
    assert src["final_v2_activation_evidence_count"] == 1
    assert src["sidecar_activation_count"] == 1
    assert src["activation_evidence_unmapped_count"] == 0
    mapping = json.loads((live_roots[0] / "activation_evidence_mapping.json").read_text(encoding="utf-8"))
    assert mapping["status"] == "ok"
    assert mapping["unmapped_ids"] == []


@pytest.mark.asyncio
async def test_live_audit_v2_payload_missing_v2_block_fails(tmp_path, monkeypatch):
    out = tmp_path / "audit"
    out.mkdir()

    class FakePayload:
        def model_dump(self, mode="json", by_alias=False):
            return {
                "meta": {
                    "scoring_version": "ss-scoring-2.0",
                    "payload_version": "today.v2.1",
                    "frontend_payload_version": 3,
                },
                "headline": "live", "day_status": "steady", "concrete_advice": {}, "why_this_happens": {},
                "v2": None,
            }

    fake_user = SimpleNamespace(id="user-1", tg_user_id=1, tg_username="u")
    fake_profile = SimpleNamespace(
        is_onboarded=True, gender="female",
        birthday=MagicMock(isoformat=lambda: "1990-01-15"),
        birth_time=MagicMock(strftime=lambda fmt: "12:00"),
        birth_city="Moscow", birth_lat=55.75, birth_lon=37.61, birth_tz="Europe/Moscow",
        current_city="Moscow", current_lat=55.75, current_lon=37.61, current_tz="Europe/Moscow",
    )
    mock_client = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value={"planets": []})
    mock_client.get_activation_layer = AsyncMock(return_value={
        "schema_version": "activation-layer.v1", "activation_layer_version": "al-1.0",
        "calculation_version": "ss-calc-1.1.0", "target_date": "2026-07-08", "target_time": "12:00",
        "target_tz": "Europe/Moscow", "house_system": "PLACIDUS",
        "activations": [{"id": "A", "technique": "transit_to_natal", "technique_family": "transit",
                         "target_type": "planet", "target_key": "MOON", "kind": "aspect", "strength": 0.5,
                         "evidence": "t", "phase": "background", "polarity": "neutral"}],
        "by_planet": {"MOON": ["A"]}, "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
    })
    mock_client.close = AsyncMock()
    today_svc = MagicMock()
    today_svc.invalidate_cache = AsyncMock()
    today_svc.get_today_payload = AsyncMock(return_value=FakePayload())

    class FakeNatal:
        def model_dump(self, mode="json", by_alias=False):
            return {"house_system": "PLACIDUS", "planets": [], "houses": []}
    class FakeNatalService:
        def __init__(self, db=None): pass
        async def get_or_build_natal_context(self, user_id): return FakeNatal()
        @staticmethod
        def compute_profile_hash(profile): return "hash"
    class _CM:
        async def __aenter__(self): return MagicMock()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(audit_mod, "SessionLocal", lambda: _CM())
    monkeypatch.setattr(audit_mod, "load_user_and_profile", AsyncMock(return_value=(fake_user, fake_profile)))
    monkeypatch.setattr(audit_mod, "load_raw_natal_sidecar", AsyncMock(return_value=None))
    monkeypatch.setattr(audit_mod, "get_solarsage_client", lambda: mock_client)
    monkeypatch.setattr(audit_mod, "AccessService", lambda db: MagicMock(can_access_day=AsyncMock(return_value=SimpleNamespace(state="subscription"))))
    monkeypatch.setattr(audit_mod, "NatalContextService", FakeNatalService)
    monkeypatch.setattr(audit_mod, "NormalizationService", lambda: MagicMock(normalize_day=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "DayDeltaService", lambda a, b: MagicMock(compute_deltas=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "filter_day_scored_signals", lambda s: [])
    monkeypatch.setattr(audit_mod, "ScoringService", lambda: MagicMock(score_day=MagicMock(return_value={"day_status": "steady", "sphere_scores": {}, "top_signals": []})))
    monkeypatch.setattr(audit_mod, "SemanticService", lambda: MagicMock(build_semantic_layer=MagicMock(return_value={}), build_why_contexts=MagicMock(return_value={})))
    monkeypatch.setattr(audit_mod, "TodayService", lambda db: today_svc)
    monkeypatch.setattr(audit_mod, "run_oracles", AsyncMock())
    monkeypatch.setattr(audit_mod, "run_downstream_audit_step", lambda *a, **k: None)

    args = audit_mod.parse_args(["--user-id", "u", "--date", "2026-07-08", "--out", str(out), "--mode", "live-production", "--skip-oracles"])
    args.resolved_mode = "live-production"
    with pytest.raises(SystemExit, match="declares V2 identity but has no v2 block"):
        await audit_mod.run_audit(args)


@pytest.mark.asyncio
async def test_live_audit_v2_payload_unmapped_sidecar_activation_fails(tmp_path, monkeypatch):
    out = tmp_path / "audit"
    out.mkdir()

    class FakePayload:
        def model_dump(self, mode="json", by_alias=False):
            return {
                "meta": {"scoring_version": "ss-scoring-2.0", "payload_version": "today.v2", "frontend_payload_version": 2},
                "headline": "live", "day_status": "steady", "concrete_advice": {}, "why_this_happens": {},
                "v2": {"activation_evidence": [{
                    "id": "B", "technique": "transit_to_natal", "technique_family": "transit",
                    "target_type": "planet", "target_key": "MOON", "kind": "aspect", "strength": 0.5,
                    "evidence": "t", "phase": "background", "polarity": "neutral",
                }]},
            }

    fake_user = SimpleNamespace(id="user-1", tg_user_id=1, tg_username="u")
    fake_profile = SimpleNamespace(
        is_onboarded=True, gender="female",
        birthday=MagicMock(isoformat=lambda: "1990-01-15"),
        birth_time=MagicMock(strftime=lambda fmt: "12:00"),
        birth_city="Moscow", birth_lat=55.75, birth_lon=37.61, birth_tz="Europe/Moscow",
        current_city="Moscow", current_lat=55.75, current_lon=37.61, current_tz="Europe/Moscow",
    )
    mock_client = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value={"planets": []})
    mock_client.get_activation_layer = AsyncMock(return_value={
        "schema_version": "activation-layer.v1", "activation_layer_version": "al-1.0",
        "calculation_version": "ss-calc-1.1.0", "target_date": "2026-07-08", "target_time": "12:00",
        "target_tz": "Europe/Moscow", "house_system": "PLACIDUS",
        "activations": [{"id": "A", "technique": "transit_to_natal", "technique_family": "transit",
                         "target_type": "planet", "target_key": "MOON", "kind": "aspect", "strength": 0.5,
                         "evidence": "t", "phase": "background", "polarity": "neutral"}],
        "by_planet": {"MOON": ["A"]}, "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
    })
    mock_client.close = AsyncMock()
    today_svc = MagicMock()
    today_svc.invalidate_cache = AsyncMock()
    today_svc.get_today_payload = AsyncMock(return_value=FakePayload())

    class FakeNatal:
        def model_dump(self, mode="json", by_alias=False):
            return {"house_system": "PLACIDUS", "planets": [], "houses": []}
    class FakeNatalService:
        def __init__(self, db=None): pass
        async def get_or_build_natal_context(self, user_id): return FakeNatal()
        @staticmethod
        def compute_profile_hash(profile): return "hash"
    class _CM:
        async def __aenter__(self): return MagicMock()
        async def __aexit__(self, *a): return False

    monkeypatch.setattr(audit_mod, "SessionLocal", lambda: _CM())
    monkeypatch.setattr(audit_mod, "load_user_and_profile", AsyncMock(return_value=(fake_user, fake_profile)))
    monkeypatch.setattr(audit_mod, "load_raw_natal_sidecar", AsyncMock(return_value=None))
    monkeypatch.setattr(audit_mod, "get_solarsage_client", lambda: mock_client)
    monkeypatch.setattr(audit_mod, "AccessService", lambda db: MagicMock(can_access_day=AsyncMock(return_value=SimpleNamespace(state="subscription"))))
    monkeypatch.setattr(audit_mod, "NatalContextService", FakeNatalService)
    monkeypatch.setattr(audit_mod, "NormalizationService", lambda: MagicMock(normalize_day=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "DayDeltaService", lambda a, b: MagicMock(compute_deltas=MagicMock(return_value=[])))
    monkeypatch.setattr(audit_mod, "filter_day_scored_signals", lambda s: [])
    monkeypatch.setattr(audit_mod, "ScoringService", lambda: MagicMock(score_day=MagicMock(return_value={"day_status": "steady", "sphere_scores": {}, "top_signals": []})))
    monkeypatch.setattr(audit_mod, "SemanticService", lambda: MagicMock(build_semantic_layer=MagicMock(return_value={}), build_why_contexts=MagicMock(return_value={})))
    monkeypatch.setattr(audit_mod, "TodayService", lambda db: today_svc)
    monkeypatch.setattr(audit_mod, "run_oracles", AsyncMock())
    monkeypatch.setattr(audit_mod, "run_downstream_audit_step", lambda *a, **k: None)

    args = audit_mod.parse_args(["--user-id", "u", "--date", "2026-07-08", "--out", str(out), "--mode", "live-production", "--skip-oracles"])
    args.resolved_mode = "live-production"
    with pytest.raises(SystemExit, match="does not represent all sidecar activations"):
        await audit_mod.run_audit(args)


def test_activation_evidence_mapping_helpers_pure():
    mapping = audit_mod.build_activation_evidence_mapping(
        mode="live-production",
        payload={
            "meta": {"payload_version": "today.v2"},
            "v2": {"activation_evidence": [{"id": "A"}]},
        },
        sidecar_layer={"activations": [{"id": "A"}, {"id": "B"}]},
        filter_policy="all_sidecar_ids_required",
    )
    assert mapping["status"] == "failed"
    assert mapping["unmapped_ids"] == ["B"]
    assert "A" in mapping["mapped_ids"]


def test_previous_v2_identity_pair_remains_recognized_by_audit_mapping():
    mapping = audit_mod.build_activation_evidence_mapping(
        mode="live-production",
        payload={
            "meta": {"payload_version": "today.v2", "frontend_payload_version": 2},
            "v2": {"activation_evidence": [{"id": "A"}]},
        },
        sidecar_layer={"activations": [{"id": "A"}]},
        filter_policy="all_sidecar_ids_required",
    )
    assert mapping["payload_version"] == "today.v2"
    assert mapping["frontend_payload_version"] == 2
    assert mapping["status"] == "ok"
    assert mapping["accepted_unmapped"] is True
