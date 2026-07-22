# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ASTRONOMY_ORACLE_FINAL_CHART — final proof mutations.
# ROLE: Proves the astronomy oracle's FINAL dayChart verification: exact
#       structure/order/count, transit longitude/sign/retrograde/motion and
#       serialized houses against the independent Swiss result; moon phase
#       missing/non-True is a failure; the engine proof is fail-closed by
#       default. Structural defects must never traceback — the summary is
#       always written and the exit code is non-zero.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-ASTRONOMY-ORACLE-FINAL-CHART
# purpose: Directed mutation tests for scripts/audit_astronomy_oracle.py
#   final dayChart/structure/moon-phase/engine checks.
# owns:
#   - apps/api/tests/test_astronomy_oracle_final_chart.py
# inputs: committed baseline artifacts (read-only) + tmp payload mutations.
# outputs: summary pass-key assertions + non-zero exit-code proofs.
# dependencies: scripts/audit_astronomy_oracle.py via a resolved python with
#   swisseph (sidecar venv locally, the current interpreter in CI where
#   apps/solarsage is pip-installed into apps/api/.venv).
# side_effects: tmp output dirs only.
# emitted_logs: none.
# invariants:
#   - Honest artifact: all final pass keys are True, rc 0 (explicit
#     allow-moshier test policy, since the pinned bundle is not in checkout).
#   - Every structural mutation flips its pass key / exit code WITHOUT a
#     traceback, and the summary file is still written.
#   - Default engine policy fails closed when the engine is not swieph.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-ASTRONOMY-ORACLE-FINAL-CHART

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE = REPO_ROOT / "artifacts" / "audit" / "2026-07-08"
SIDECAR_PYTHON = REPO_ROOT / "apps" / "solarsage" / "venv" / "bin" / "python"

import pytest  # noqa: E402


def _resolve_oracle_python() -> str | None:
    """Local dev uses the sidecar venv; CI uses the current interpreter
    (apps/solarsage is pip-installed into apps/api/.venv there)."""
    if SIDECAR_PYTHON.exists():
        return str(SIDECAR_PYTHON)
    try:
        import swisseph  # noqa: F401

        return sys.executable
    except ImportError:
        return None


ORACLE_PYTHON = _resolve_oracle_python()
pytestmark = pytest.mark.skipif(ORACLE_PYTHON is None, reason="no python with swisseph available")

# Mutation tests run WITHOUT the pinned ephemeris bundle (not present in a
# bare checkout), so they use the explicitly marked allow-moshier test policy.
# The real audit-day contour never passes this flag (fail-closed swieph).
TEST_POLICY_ARGS = ["--engine-policy", "allow-moshier"]


def _oracle_cmd(payload_path: Path, out: Path, transits_path: Path | None = None) -> list[str]:
    return [
        ORACLE_PYTHON,
        str(REPO_ROOT / "scripts" / "audit_astronomy_oracle.py"),
        "--input-profile", str(BASE / "00_input_profile.json"),
        "--raw-transits", str(transits_path or (BASE / "debug" / "raw_transits.json")),
        "--raw-natal-context", str(BASE / "debug" / "raw_natal_context.json"),
        "--final-payload", str(payload_path),
        "--date", "2026-07-08",
        "--time", "12:00",
        "--tz", "Europe/Moscow",
        "--out", str(out),
    ]


def _run(tmp_path: Path, mutate=None, extra_args: list[str] | None = None) -> tuple[int, dict, subprocess.CompletedProcess]:
    payload = json.loads((BASE / "debug" / "final_today_payload.json").read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(payload)
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run(
        [*_oracle_cmd(payload_path, out), *(TEST_POLICY_ARGS if extra_args is None else extra_args)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    summary_path = out / "astronomy_oracle_summary.json"
    assert summary_path.exists(), f"summary not written (traceback?):\n{result.stderr[-2000:]}"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return result.returncode, summary, result


def test_honest_final_chart_all_pass(tmp_path) -> None:
    rc, summary, _ = _run(tmp_path)
    assert rc == 0
    assert summary["longitude_pass"] is True
    assert summary["sign_pass"] is True
    assert summary["retrograde_flag_pass"] is True
    assert summary["house_pass"] is True
    assert summary["final_transit_structure_pass"] is True
    assert summary["final_transit_longitude_pass"] is True
    assert summary["final_transit_sign_pass"] is True
    assert summary["final_transit_retrograde_pass"] is True
    assert summary["final_motion_pass"] is True
    assert summary["final_house_structure_pass"] is True
    assert summary["final_house_cusp_pass"] is True
    assert summary["final_house_sign_pass"] is True
    assert summary["moon_phase"]["pass"] is True
    assert summary["engine"]["engine_pass"] is True
    assert summary["engine"]["policy"] == "allow-moshier"
    # The summary never persists an absolute runner path (byte-stability).
    assert "ephemeris_path" not in summary["engine"]


def test_default_engine_policy_fails_closed_on_empty_ephe_dir(tmp_path) -> None:
    # Explicit EMPTY ephemeris dir => moshier is guaranteed, no conditional
    # skip: the default swieph policy must fail closed.
    empty_ephe = tmp_path / "empty-ephe"
    empty_ephe.mkdir()
    payload = json.loads((BASE / "debug" / "final_today_payload.json").read_text(encoding="utf-8"))
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run(
        [*_oracle_cmd(payload_path, out), "--ephemeris-path", str(empty_ephe)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    summary_path = out / "astronomy_oracle_summary.json"
    assert summary_path.exists(), f"summary not written (traceback?):\n{result.stderr[-2000:]}"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["engine"]["moseph"] is True
    assert summary["engine"]["swieph"] is False
    assert summary["engine"]["engine_pass"] is False
    assert summary["engine"]["policy"] == "swieph"
    assert result.returncode != 0


def test_final_transit_longitude_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["transit_planets"][0]["longitude"] = 999.0

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_transit_longitude_pass"] is False


def test_final_transit_sign_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["transit_planets"][0]["sign"] = "CORRUPTED"

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_transit_sign_pass"] is False


def test_final_transit_retrograde_flip_fails(tmp_path) -> None:
    def mutate(p):
        planet = p["day_chart"]["transit_planets"][0]
        planet["retrograde"] = not planet["retrograde"]

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_transit_retrograde_pass"] is False


def test_final_motion_mutation_fails(tmp_path) -> None:
    def mutate(p):
        for planet in p["day_chart"]["transit_planets"]:
            planet["motion"] = "retrograde"

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_motion_pass"] is False


def test_final_extra_transit_planet_fails(tmp_path) -> None:
    def mutate(p):
        extra = dict(p["day_chart"]["transit_planets"][0])
        extra["name"] = "Ceres"
        p["day_chart"]["transit_planets"] = [*p["day_chart"]["transit_planets"], extra]

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_transit_structure_pass"] is False


def test_final_transit_order_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["transit_planets"] = list(reversed(p["day_chart"]["transit_planets"]))

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_transit_structure_pass"] is False


def test_final_house_cusp_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["houses"][0]["cusp_longitude"] = 999.0

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_house_cusp_pass"] is False


def test_final_house_sign_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["houses"][0]["sign"] = "CORRUPTED"

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_house_sign_pass"] is False


def test_final_house_order_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["houses"] = list(reversed(p["day_chart"]["houses"]))

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_house_structure_pass"] is False
    assert summary["final_house_cusp_pass"] is False


def test_final_house_removed_fails_without_traceback(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["houses"] = p["day_chart"]["houses"][1:]

    rc, summary, result = _run(tmp_path, mutate)
    assert rc != 0
    assert "Traceback" not in result.stderr
    assert summary["final_house_structure_pass"] is False


def test_moon_phase_fact_removed_fails(tmp_path) -> None:
    def mutate(p):
        facts = (p.get("day_summary") or {}).get("facts") or []
        if "day_summary" in p:
            p["day_summary"]["facts"] = [f for f in facts if f.get("kind") != "lunar_phase"]

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["moon_phase"]["pass"] is None


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
        [*_oracle_cmd(payload_path, out, transits_path), *TEST_POLICY_ARGS],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    summary = json.loads((out / "astronomy_oracle_summary.json").read_text(encoding="utf-8"))
    assert result.returncode != 0
    assert summary["sign_pass"] is False


# -- Container-shape and bool-strict mutations (third-review blockers) ------

def test_final_retrograde_bool_to_int_fails(tmp_path) -> None:
    def mutate(p):
        planet = p["day_chart"]["transit_planets"][0]
        assert planet["retrograde"] is False
        planet["retrograde"] = 0  # JSON 0 is not JSON false

    rc, summary, _ = _run(tmp_path, mutate)
    assert rc != 0
    assert summary["final_transit_retrograde_pass"] is False


def test_transit_planets_wrong_container_no_traceback(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["transit_planets"] = {"bad": 1}

    rc, summary, result = _run(tmp_path, mutate)
    assert rc != 0
    assert "Traceback" not in result.stderr
    assert summary["final_transit_structure_pass"] is False


def test_houses_wrong_container_no_traceback(tmp_path) -> None:
    def mutate(p):
        p["day_chart"]["houses"] = {"bad": 1}

    rc, summary, result = _run(tmp_path, mutate)
    assert rc != 0
    assert "Traceback" not in result.stderr
    assert summary["final_house_structure_pass"] is False


def test_day_chart_wrong_container_no_traceback(tmp_path) -> None:
    def mutate(p):
        p["day_chart"] = ["bad"]

    rc, summary, result = _run(tmp_path, mutate)
    assert rc != 0
    assert "Traceback" not in result.stderr
    assert summary["final_transit_structure_pass"] is False
    assert summary["final_house_structure_pass"] is False


def test_facts_wrong_container_no_traceback(tmp_path) -> None:
    def mutate(p):
        p["day_summary"]["facts"] = ["bad"]

    rc, summary, result = _run(tmp_path, mutate)
    assert rc != 0
    assert "Traceback" not in result.stderr
    assert summary["moon_phase"]["pass"] is None
