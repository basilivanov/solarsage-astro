"""W9 tests: audit activation sidecar artifacts vs local fallback."""

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


def _common_monkeypatch(monkeypatch, *, sidecar_ok: bool, v2_enabled: bool = True):
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
    if sidecar_ok:
        mock_client.get_activation_layer = AsyncMock(return_value={
            "schema_version": "activation-layer.v1",
            "activation_layer_version": "al-1.0",
            "calculation_version": "ss-calc-1.1.0",
            "target_date": "2026-07-08",
            "target_time": "12:00",
            "target_tz": "Europe/Moscow",
            "house_system": "PLACIDUS",
            "activations": [{
                "id": "sidecar__ACT",
                "technique": "transit_to_natal",
                "technique_family": "transit",
                "target_type": "planet",
                "target_key": "SUN",
                "kind": "aspect",
                "strength": 0.8,
                "evidence": "sidecar",
                "phase": "background",
                "polarity": "neutral",
            }],
            "by_planet": {"SUN": ["sidecar__ACT"]},
            "by_house": {},
            "by_lot": {},
            "by_angle": {},
            "warnings": [],
        })
    else:
        mock_client.get_activation_layer = AsyncMock(side_effect=RuntimeError("sidecar down"))
    mock_client.close = AsyncMock()

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
    today_svc = MagicMock()
    today_svc.invalidate_cache = AsyncMock()
    today_svc.get_today_payload = AsyncMock(return_value=MagicMock(model_dump=lambda **k: {
        "meta": {
            "scoring_version": 1,
            "payload_version": "today.v1",
            "frontend_payload_version": 1,
        },
        "headline": "x", "day_status": "steady",
        "concrete_advice": {}, "why_this_happens": {},
        "v2": None,
    }))
    monkeypatch.setattr(audit_mod, "TodayService", lambda db: today_svc)

    async def _oracles(**kwargs):
        d = kwargs["out_dir"]
        (d / "scoring_intermediate_table.csv").write_text("x\n", encoding="utf-8")
        (d / "scoring_oracle_comparison.json").write_text("{}", encoding="utf-8")
        (d / "astronomy_oracle_summary.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(audit_mod, "run_oracles", _oracles)
    monkeypatch.setattr(audit_mod, "run_downstream_audit_step", lambda *a, **k: None)

    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "solarsage_v2_enabled", v2_enabled)
    return mock_client, today_svc


def _valid_baseline() -> dict:
    from tests.test_today_horizons_contract import build_complete_today_payload

    baseline = build_complete_today_payload(
        payload_version="today.v1",
        frontend_payload_version=1,
        audit_payload_version="today.v1",
        include_pipeline_audit=False,
    )
    baseline["v2"] = None
    baseline["headline"] = "f"
    return baseline


@pytest.mark.asyncio
async def test_audit_writes_sidecar_as_root_16(tmp_path, monkeypatch):
    mock_client, _ = _common_monkeypatch(monkeypatch, sidecar_ok=True)
    out = tmp_path / "audit"
    out.mkdir()
    (out / "11_final_today_payload.json").write_text(json.dumps(_valid_baseline()), encoding="utf-8")

    args = audit_mod.parse_args([
        "--user-id", "u", "--date", "2026-07-08", "--out", str(out),
        "--mode", "frozen-baseline", "--skip-oracles",
    ])
    args.resolved_mode = "frozen-baseline"
    summary = await audit_mod.run_audit(args)

    mock_client.get_activation_layer.assert_awaited()
    assert summary["activation_layer_source"] == "sidecar"
    assert (out / "debug" / "raw_sidecar_activation_layer.json").exists()
    assert (out / "debug" / "sidecar_activation_layer.json").exists()
    root16 = json.loads((out / "16_activation_layer.json").read_text(encoding="utf-8"))
    assert root16["activations"][0]["id"] == "sidecar__ACT"
    assert not (out / "debug" / "local_fallback_activation_layer.json").exists()


@pytest.mark.asyncio
async def test_live_v2_fails_loudly_when_sidecar_down(tmp_path, monkeypatch):
    _common_monkeypatch(monkeypatch, sidecar_ok=False, v2_enabled=True)
    out = tmp_path / "audit"
    out.mkdir()
    args = audit_mod.parse_args([
        "--user-id", "u", "--date", "2026-07-08", "--out", str(out),
        "--mode", "live-production", "--skip-oracles",
    ])
    args.resolved_mode = "live-production"
    with pytest.raises(SystemExit, match="sidecar activation layer failed"):
        await audit_mod.run_audit(args)


@pytest.mark.asyncio
async def test_fallback_only_with_explicit_flag(tmp_path, monkeypatch):
    _common_monkeypatch(monkeypatch, sidecar_ok=False, v2_enabled=False)
    out = tmp_path / "audit"
    out.mkdir()
    (out / "11_final_today_payload.json").write_text(json.dumps(_valid_baseline()), encoding="utf-8")

    args = audit_mod.parse_args([
        "--user-id", "u", "--date", "2026-07-08", "--out", str(out),
        "--mode", "frozen-baseline", "--skip-oracles",
        "--allow-activation-fallback",
    ])
    args.resolved_mode = "frozen-baseline"
    summary = await audit_mod.run_audit(args)
    assert summary["activation_layer_source"] == "local_fallback"
    assert (out / "debug" / "local_fallback_activation_layer.json").exists()
    # Root 16 must NOT be the fallback in acceptance mode
    assert not (out / "16_activation_layer.json").exists()
