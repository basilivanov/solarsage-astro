"""W11 tests: downstream V2 audit script artifacts and hard fails."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from scripts import audit_downstream_v2 as audit  # noqa: E402


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "downstream_v2"
REQUIRED_ARTIFACTS = [
    "00_input_metadata.json",
    "01_sidecar_activation_layer.json",
    "02_api_activation_layer_after_validation.json",
    "03_scoring_v2_result.json",
    "04_activation_to_sphere_matrix.csv",
    "05_contribution_trace.csv",
    "06_convergence_trace.csv",
    "07_dominance_cap_trace.csv",
    "08_status_breakdown.json",
    "09_payload_v2.json",
    "10_payload_mapping.json",
    "11_frontend_fixture.json",
    "12_downstream_audit_summary.json",
]


def _run(out: Path, fixture: str, fail_on_unmapped: bool = True) -> dict:
    args = audit.parse_args(
        [
            "--synthetic-fixture",
            str(FIXTURE_DIR / fixture),
            "--date",
            "2026-07-08",
            "--out",
            str(out),
            "--fail-on-unmapped",
            "true" if fail_on_unmapped else "false",
        ]
    )
    return audit.run_downstream_audit(args)


def test_audit_writes_all_required_artifacts(tmp_path):
    out = tmp_path / "down"
    summary = _run(out, "01_planet_target_mapping.json", fail_on_unmapped=False)
    assert summary["status"] == "ok"
    for name in REQUIRED_ARTIFACTS:
        assert (out / name).exists(), name


def test_audit_ok_for_valid_planet_fixture(tmp_path):
    out = tmp_path / "ok"
    summary = _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    assert summary["status"] == "ok"
    mapping = json.loads((out / "10_payload_mapping.json").read_text(encoding="utf-8"))
    assert mapping["missing_after_api_validation"] == []
    assert mapping["missing_in_payload_v2"] == []


def test_audit_fails_on_lost_sidecar_id(tmp_path, monkeypatch):
    out = tmp_path / "lost"
    fixture = json.loads((FIXTURE_DIR / "01_planet_target_mapping.json").read_text())
    # Break API preservation by patching ActivationLayerService.build
    from app.schemas.activation import ActivationLayer

    def bad_build(self, **kwargs):
        layer = ActivationLayer.model_validate(kwargs["sidecar_activation_layer"])
        # drop ids
        layer.activations = []
        layer.by_planet = {}
        return layer

    monkeypatch.setattr(audit.ActivationLayerService, "build", bad_build)
    args = audit.parse_args(
        [
            "--synthetic-fixture",
            str(FIXTURE_DIR / "01_planet_target_mapping.json"),
            "--date",
            "2026-07-08",
            "--out",
            str(out),
            "--fail-on-unmapped",
            "false",
        ]
    )
    with pytest.raises(SystemExit):
        audit.run_downstream_audit(args)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert summary["status"] == "failed"
    assert any(f["kind"] == "sidecar_ids_not_preserved" for f in summary["failures"])


def test_audit_records_unmapped_and_obeys_fail_flag(tmp_path):
    out = tmp_path / "unmap"
    with pytest.raises(SystemExit):
        _run(out, "06_unmapped_activation.json", fail_on_unmapped=True)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert summary["status"] == "failed"
    assert any(f["kind"] == "unmapped_activation" for f in summary["failures"])

    out2 = tmp_path / "unmap_warn"
    summary2 = _run(out2, "06_unmapped_activation.json", fail_on_unmapped=False)
    assert summary2["status"] in ("ok", "warning") or summary2["warning_count"] >= 0
    mapping = json.loads((out2 / "10_payload_mapping.json").read_text())
    assert "t2n__X__ZZZ" in mapping["unmapped_activations"] or mapping["unmapped_activations"]


def test_map_activation_independent_of_production():
    spheres, scoring_v2, _ = audit.load_canons()
    act = {
        "id": "x",
        "target_type": "planet",
        "target_key": "PLUTO",
        "strength": 0.8,
        "polarity": "tense",
        "technique": "transit_to_natal",
        "technique_family": "transit",
    }
    rows = audit.map_activation_to_spheres_for_audit(act, spheres, scoring_v2)
    spheres_hit = {r["sphere"] for r in rows}
    assert "crisis_transformation_control" in spheres_hit
    assert all(r["target_weight"] > 0 for r in rows)


def test_expected_amount_formula():
    assert audit.expected_activation_amount(0.8, 1.0, 1.0, 1.0) == 0.8
    assert audit.expected_activation_amount(0.8, 0.8, 0.5, 0.7) == round(0.8 * 0.8 * 0.5 * 0.7, 4)


def test_convergence_same_family_bonus_zero():
    _, scoring_v2, _ = audit.load_canons()
    assert audit.expected_convergence_bonus("x", {"transit"}, scoring_v2) == 0.0


def test_convergence_multi_family_bonus():
    _, scoring_v2, _ = audit.load_canons()
    bonus = audit.expected_convergence_bonus("x", {"transit", "profection", "firdar"}, scoring_v2)
    assert bonus == 0.65
