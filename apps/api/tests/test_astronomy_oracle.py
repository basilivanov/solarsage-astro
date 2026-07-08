import pytest
import subprocess
import sys
import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch
from app.clients.solarsage_client import SolarSageClient

@pytest.mark.asyncio
async def test_retrograde_flags_2026_07_08():
    client = SolarSageClient()
    try:
        res = await client.get_transits(
            target_date="2026-07-08",
            target_time="12:00",
            target_tz="Europe/Moscow"
        )
        planets = {p["name"]: p for p in res["planets"]}

        assert planets["Mercury"]["retrograde"] is True
        assert planets["Neptune"]["retrograde"] is True
        assert planets["Pluto"]["retrograde"] is True
    finally:
        await client.client.aclose()

@pytest.mark.asyncio
async def test_moon_phase_illumination_2026_07_08():
    client = SolarSageClient()
    try:
        res = await client.get_transits(
            target_date="2026-07-08",
            target_time="12:00",
            target_tz="Europe/Moscow"
        )
        planets = {p["name"]: p for p in res["planets"]}
        sun_lon = planets["Sun"]["longitude"]
        moon_lon = planets["Moon"]["longitude"]

        from math import radians, cos
        angle = (moon_lon - sun_lon) % 360
        illumination = (1 - cos(radians(angle))) / 2 * 100

        assert abs(illumination - 43.792) <= 0.5
    finally:
        await client.client.aclose()

def test_scoring_oracle_failure_exits_non_zero(tmp_path: Path):
    signals_file = tmp_path / "signal_trace.csv"
    signals_file.write_text(
        "included_in_day_scoring,type,planet,target_planet,aspect_type,orb,strength,house,sign,daily_salience\n"
        "true,aspect,Transit_Mars,Saturn,square,1.0,0.9,,,\n",
        encoding="utf-8"
    )

    prod_file = tmp_path / "production_scoring.json"
    prod_file.write_text(json.dumps({"day_status": "supportive", "sphere_scores": {}, "top_signals": []}), encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[3]
    script_path = repo_root / "scripts" / "audit_scoring_oracle.py"
    canon_dir = repo_root / "grace" / "canon"

    res = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--canon-dir", str(canon_dir),
            "--signals", str(signals_file),
            "--production-scoring", str(prod_file),
            "--out", str(tmp_path / "out"),
        ],
        capture_output=True,
    )
    assert res.returncode != 0

def test_scoring_oracle_top_signals_mismatch_exits_non_zero(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    canon_dir = repo_root / "grace" / "canon"
    script_path = repo_root / "scripts" / "audit_scoring_oracle.py"

    signals_file = tmp_path / "signal_trace.csv"
    signals_file.write_text(
        "included_in_day_scoring,type,planet,target_planet,aspect_type,orb,strength,house,sign,daily_salience\n"
        "true,aspect,Transit_Sun,Mercury,trine,1.0,0.9,,,\n",
        encoding="utf-8"
    )

    # Run once to get the oracle results
    res_run = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--canon-dir", str(canon_dir),
            "--signals", str(signals_file),
            "--out", str(tmp_path / "out1"),
        ],
        capture_output=True,
    )
    assert res_run.returncode == 0
    oracle_res = json.loads((tmp_path / "out1" / "scoring_oracle_result.json").read_text(encoding="utf-8"))

    # Now create production scoring with the exact same day_status and sphere_scores,
    # but a completely different/mismatched top_signals list!
    prod_file = tmp_path / "production_scoring.json"
    prod_data = {
        "day_status": oracle_res["day_status"],
        "sphere_scores": oracle_res["sphere_scores"],
        "top_signals": [
            {
                "type": "aspect",
                "planet": "Transit_Moon",
                "target_planet": "Pluto",
                "aspect_type": "opposition"
            }
        ]
    }
    prod_file.write_text(json.dumps(prod_data), encoding="utf-8")

    # Run again with production scoring, which should now fail due to top_signals mismatch!
    res_fail = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--canon-dir", str(canon_dir),
            "--signals", str(signals_file),
            "--production-scoring", str(prod_file),
            "--out", str(tmp_path / "out2"),
        ],
        capture_output=True,
    )
    assert res_fail.returncode != 0

def test_api_schema_retrograde_validation():
    from pydantic import ValidationError
    from app.schemas.natal import SolarSageTransitPlanet, SolarSagePlanetPosition

    # 1. Validation succeeds if retrograde is present
    p1 = SolarSageTransitPlanet.model_validate({
        "name": "Mercury",
        "longitude": 120.0,
        "sign": "Leo",
        "retrograde": True
    })
    assert p1.retrograde is True

    # 2. Validation succeeds and derives retrograde if speed is present
    p2 = SolarSageTransitPlanet.model_validate({
        "name": "Mercury",
        "longitude": 120.0,
        "sign": "Leo",
        "speed": -0.05
    })
    assert p2.retrograde is True

    p3 = SolarSageTransitPlanet.model_validate({
        "name": "Mercury",
        "longitude": 120.0,
        "sign": "Leo",
        "speed": 0.05
    })
    assert p3.retrograde is False

    # 3. Validation fails if both are missing
    with pytest.raises(ValidationError):
        SolarSageTransitPlanet.model_validate({
            "name": "Mercury",
            "longitude": 120.0,
            "sign": "Leo",
        })

def test_natal_chart_planet_requires_retrograde():
    from pydantic import ValidationError
    from app.schemas.natal import NatalChartPlanet, NatalPreviewChartPlanet

    with pytest.raises(ValidationError):
        NatalChartPlanet.model_validate({
            "name": "Mercury",
            "sign": "Leo",
            "degree": 12.5,
            "longitude": 132.5,
        })

    with pytest.raises(ValidationError):
        NatalPreviewChartPlanet.model_validate({
            "name": "Mercury",
            "sign": "Leo",
            "degree": 12.5,
            "longitude": 132.5,
        })

@pytest.mark.asyncio
async def test_today_interpretation_service_moon_phase_rounding():
    from app.schemas.today import DayChart, DayChartTransitPlanet
    from app.services.today_interpretation_service import TodayInterpretationService

    # 2026-07-08 12:00 Moscow longitudes: Sun=106.2336, Moon=23.3659
    day_chart = DayChart(
        source="solarsage",
        houses=[],
        transit_planets=[
            DayChartTransitPlanet(name="Sun", longitude=106.233642, sign="Cancer", speed=0.95, house=1),
            DayChartTransitPlanet(name="Moon", longitude=23.365864, sign="Aries", speed=13.1, house=10),
        ],
        aspects=[],
    )

    service = TodayInterpretationService()

    with patch("app.services.llm_service.LLMService.generate_concrete_advice", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {k: "СЕНТИНЕЛ РЕКОМЕНДАЦИЯ" for k in ["work", "money", "documents", "relationships", "sport", "communication", "health", "decisions", "travel", "creativity", "study", "shopping"]}

        _, day_summary, _ = await service.build(
            target_date=date(2026, 7, 8),
            day_status="supportive",
            scoring_result={"day_status": "supportive", "sphere_scores": {}},
            signals=[],
            semantic_layer=None,
            day_chart=day_chart,
            planet_influences=[],
            sphere_scores=[],
            important_items=[],
        )

    lunar_fact = next((f for f in day_summary.facts if f.kind == "lunar_phase"), None)
    assert lunar_fact is not None
    # Verify the correctly rounded value is displayed (44%, not truncated 43%)
    assert lunar_fact.title == "Убывающая Луна 44%"

def test_audit_claims_report_has_no_na_placeholders_for_present_data():
    """Verify that the generated 14_claims_audit.md does not contain N/A
    placeholders or fallback advice text for fields that are populated
    in the actual payload."""
    from pathlib import Path
    claims_path = Path("artifacts/audit/2026-07-08/14_claims_audit.md")
    if not claims_path.exists():
        pytest.skip("14_claims_audit.md not found; run make audit-day first")
    text = claims_path.read_text(encoding="utf-8")
    # If the payload fields are present, the report must not show N/A for them
    assert 'Moon Phase Fact: "N/A"' not in text
    assert "Top Flags: N/A" not in text
    assert "| N/A | N/A | N/A |" not in text
    # The canonical W0 baseline must not contain fallback LLM advice text
    assert "Рекомендация временно недоступна." not in text

def test_audit_default_fails_fast_on_missing_baseline(tmp_path: Path):
    """Default mode must exit non-zero before any artifact writes when baseline is missing."""
    import subprocess, sys
    from pathlib import Path
    script = Path(__file__).resolve().parents[3] / "scripts" / "audit_today.py"
    out = tmp_path / "out"
    # No baseline fixture exists in tmp_path/out
    res = subprocess.run(
        [sys.executable, str(script), "--user-id", "eb3876be-e1b4-43d6-b887-1f8554e33150",
         "--date", "2026-07-08", "--out", str(out)],
        capture_output=True, timeout=30,
    )
    assert res.returncode != 0
    # No files should be written to out/ or out/debug/
    assert not list(out.rglob("*")), "No files should exist after missing-baseline failure"

def test_audit_default_fails_fast_on_invalid_baseline(tmp_path: Path):
    """Default mode must exit non-zero before any artifact writes when baseline is invalid."""
    import subprocess, sys, json
    from pathlib import Path
    script = Path(__file__).resolve().parents[3] / "scripts" / "audit_today.py"
    out = tmp_path / "out"
    out.mkdir()
    # Write an invalid baseline (not valid JSON)
    (out / "11_final_today_payload.json").write_text("{invalid json", encoding="utf-8")
    res = subprocess.run(
        [sys.executable, str(script), "--user-id", "eb3876be-e1b4-43d6-b887-1f8554e33150",
         "--date", "2026-07-08", "--out", str(out)],
        capture_output=True, timeout=30,
    )
    assert res.returncode != 0
    # Only the baseline file should exist (nothing else written)
    existing = list(out.rglob("*"))
    assert len(existing) == 1 and existing[0].name == "11_final_today_payload.json"

def test_audit_live_isolates_output(tmp_path: Path):
    """Live mode must write only under live/<timestamp>/ and not to canonical root.
    Must fail when subprocess fails (detects regression in live execution)."""
    import subprocess, sys
    from pathlib import Path
    script = Path(__file__).resolve().parents[3] / "scripts" / "audit_today.py"
    real_baseline = Path(__file__).resolve().parents[3] / "artifacts" / "audit" / "2026-07-08" / "11_final_today_payload.json"
    out = tmp_path / "out"
    out.mkdir()
    import shutil
    shutil.copy2(real_baseline, out / "11_final_today_payload.json")
    res = subprocess.run(
        [sys.executable, str(script), "--user-id", "eb3876be-e1b4-43d6-b887-1f8554e33150",
         "--date", "2026-07-08", "--out", str(out), "--live-llm-sample"],
        capture_output=True, timeout=120,
    )
    # Must fail on subprocess failure — live execution regression must be caught
    assert res.returncode == 0, f"live audit subprocess failed: {res.stderr.decode()}"
    # No canonical root debug/ directory in live mode
    assert not (out / "debug").exists(), "live mode must not create canonical root debug/"
    # No root 00_* through 15_* files outside the timestamped live directory
    for child in out.iterdir():
        name = child.name
        if name == "11_final_today_payload.json":
            continue  # baseline fixture is allowed
        if name == "live":
            continue  # live output directory is allowed
        assert False, f"Unexpected file/dir in canonical root during live mode: {name}"
    # Live output must exist inside live/<timestamp>/
    live_items = list((out / "live").iterdir()) if (out / "live").exists() else []
    assert len(live_items) > 0, "live/ should contain at least one timestamped run"

def test_audit_resolve_output_dirs_default():
    """Default mode: root_dir == out_dir, debug_dir == out_dir/debug."""
    from pathlib import Path
    from scripts.audit_today import resolve_audit_output_dirs
    base = Path("/tmp/test_audit")
    dirs = resolve_audit_output_dirs(base, is_live=False)
    assert dirs.root_dir == base
    assert dirs.debug_dir == base / "debug"
    assert not dirs.is_live

def test_audit_resolve_output_dirs_live():
    """Live mode: root_dir == out_dir/live/<timestamp>, debug_dir == root_dir/debug.
    Canonical root debug/ must NOT be set as debug_dir."""
    from pathlib import Path
    from scripts.audit_today import resolve_audit_output_dirs
    base = Path("/tmp/test_audit")
    ts = "20260708T120000"
    dirs = resolve_audit_output_dirs(base, is_live=True, timestamp=ts)
    assert dirs.root_dir == base / "live" / ts
    assert dirs.debug_dir == base / "live" / ts / "debug"
    assert dirs.debug_dir != base / "debug"
    assert dirs.is_live
