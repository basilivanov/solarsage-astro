# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ASTRONOMY_ORACLE_FINAL_CHART — final proof mutations.
# ROLE: Proves the astronomy oracle's FINAL dayChart verification: transit
#       longitude/sign/motion and serialized houses (number/order/cusp/sign)
#       against the independent Swiss result; sign aggregation is fail-closed.
#       Runs the oracle as a subprocess (canonical sidecar venv path) so the
#       api venv needs no swisseph import.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-ASTRONOMY-ORACLE-FINAL-CHART
# purpose: Directed mutation tests for scripts/audit_astronomy_oracle.py
#   final dayChart checks (existing tolerances unchanged).
# owns:
#   - apps/api/tests/test_astronomy_oracle_final_chart.py
# inputs: committed baseline artifacts (read-only) + tmp payload mutations.
# outputs: summary pass-key assertions + non-zero exit-code proofs.
# dependencies: scripts/audit_astronomy_oracle.py via sidecar venv python.
# side_effects: tmp output dirs only.
# emitted_logs: none.
# invariants:
#   - Honest artifact: all final pass keys are True, rc 0.
#   - Every final-chart mutation flips its pass key to False (rc non-zero).
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-ASTRONOMY-ORACLE-FINAL-CHART

from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE = REPO_ROOT / "artifacts" / "audit" / "2026-07-08"
SIDECAR_PYTHON = REPO_ROOT / "apps" / "solarsage" / "venv" / "bin" / "python"

import pytest  # noqa: E402

pytestmark = pytest.mark.skipif(not SIDECAR_PYTHON.exists(), reason="sidecar venv missing")


def _run(tmp_path: Path, mutate=None) -> tuple[int, dict]:
    payload = json.loads((BASE / "debug" / "final_today_payload.json").read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(payload)
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run(
        [
            str(SIDECAR_PYTHON),
            str(REPO_ROOT / "scripts" / "audit_astronomy_oracle.py"),
            "--input-profile", str(BASE / "00_input_profile.json"),
            "--raw-transits", str(BASE / "debug" / "raw_transits.json"),
            "--raw-natal-context", str(BASE / "debug" / "raw_natal_context.json"),
            "--final-payload", str(payload_path),
            "--date", "2026-07-08",
            "--time", "12:00",
            "--tz", "Europe/Moscow",
            "--out", str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    summary = json.loads((out / "astronomy_oracle_summary.json").read_text(encoding="utf-8"))
    return result.returncode, summary


def test_honest_final_chart_all_pass(tmp_path) -> None:
    rc, summary = _run(tmp_path)
    assert rc == 0
    assert summary["longitude_pass"] is True
    assert summary["sign_pass"] is True
    assert summary["retrograde_flag_pass"] is True
    assert summary["house_pass"] is True
    assert summary["final_transit_longitude_pass"] is True
    assert summary["final_transit_sign_pass"] is True
    assert summary["final_motion_pass"] is True
    assert summary["final_house_cusp_pass"] is True
    assert summary["final_house_sign_pass"] is True


def test_final_transit_longitude_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["transit_planets"][0]["longitude"] = 999.0

    rc, summary = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_transit_longitude_pass"] is False


def test_final_transit_sign_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["transit_planets"][0]["sign"] = "CORRUPTED"

    rc, summary = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_transit_sign_pass"] is False


def test_final_motion_mutation_fails(tmp_path) -> None:
    def mutate(p):
        for planet in p["day_chart"]["transit_planets"]:
            planet["motion"] = "retrograde"

    rc, summary = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_motion_pass"] is False


def test_final_house_cusp_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["houses"][0]["cusp_longitude"] = 999.0

    rc, summary = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_house_cusp_pass"] is False


def test_final_house_sign_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["houses"][0]["sign"] = "CORRUPTED"

    rc, summary = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_house_sign_pass"] is False


def test_final_house_order_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["houses"] = list(reversed(p["day_chart"]["houses"]))

    rc, summary = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_house_cusp_pass"] is False


def test_raw_transit_sign_mutation_fails(tmp_path) -> None:
    payload = json.loads((BASE / "debug" / "final_today_payload.json").read_text(encoding="utf-8"))
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    transits = json.loads((BASE / "debug" / "raw_transits.json").read_text(encoding="utf-8"))
    transits["planets"][0]["sign"] = "CORRUPTED"
    transits_path = tmp_path / "transits.json"
    transits_path.write_text(json.dumps(transits), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run(
        [
            str(SIDECAR_PYTHON),
            str(REPO_ROOT / "scripts" / "audit_astronomy_oracle.py"),
            "--input-profile", str(BASE / "00_input_profile.json"),
            "--raw-transits", str(transits_path),
            "--raw-natal-context", str(BASE / "debug" / "raw_natal_context.json"),
            "--final-payload", str(payload_path),
            "--date", "2026-07-08",
            "--time", "12:00",
            "--tz", "Europe/Moscow",
            "--out", str(out),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    summary = json.loads((out / "astronomy_oracle_summary.json").read_text(encoding="utf-8"))
    assert result.returncode != 0
    assert summary["sign_pass"] is False
