# ############################################################################
# AI_HEADER: MODULE_TEST_DOWNSTREAM_V2_AUDIT — W11 downstream audit script tests
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DOWNSTREAM-V2-AUDIT
# purpose: Prove audit_downstream_v2 artifacts, independent checks, and hard fails.
# owns:
#   - apps/api/tests/test_downstream_v2_audit.py
# inputs: fixtures/downstream_v2/*
# outputs: pytest assertions
# dependencies: scripts.audit_downstream_v2
# side_effects: temp artifact directories under pytest tmp_path
# emitted_logs: none
# invariants: no private production scoring helpers used for expected math
# failure_policy: pytest fail
# END_MODULE_CONTRACT: M-TEST-DOWNSTREAM-V2-AUDIT

# START_MODULE_MAP: M-TEST-DOWNSTREAM-V2-AUDIT
# public_entrypoints:
#   - test_audit_writes_all_required_artifacts
#   - test_audit_ok_synthetic
#   - test_v1_replay_fails
#   - mutation/hard-fail tests
# END_MODULE_MAP: M-TEST-DOWNSTREAM-V2-AUDIT

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
REQUIRED = [
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


def _run(out: Path, fixture: str, fail_on_unmapped: bool = True):
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
    summary = _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    assert summary["status"] == "ok"
    for name in REQUIRED:
        assert (out / name).exists(), name
    meta = json.loads((out / "00_input_metadata.json").read_text())
    assert meta["mode"] == "synthetic_fixture"
    fixture = json.loads((out / "11_frontend_fixture.json").read_text())
    assert fixture["assertions"]["has_v2"] is True
    assert fixture["payload"]["v2"] is not None


def test_audit_ok_synthetic_and_fixture_self_consistent(tmp_path):
    out = tmp_path / "ok"
    summary = _run(out, "08_convergence_multi_family.json", fail_on_unmapped=False)
    assert summary["status"] == "ok"
    fx = json.loads((out / "11_frontend_fixture.json").read_text())
    assert fx["assertions"]["has_v2"] == (fx["payload"].get("v2") is not None)
    assert fx["assertions"]["activation_evidence_count"] == len(fx["payload"]["v2"]["activationEvidence"])


def test_v1_replay_fails_without_synthesis(tmp_path):
    out = tmp_path / "v1replay"
    # minimal V1 payload + activation layer from fixture
    layer = json.loads((FIXTURE_DIR / "12_payload_mapping.json").read_text())["activation_layer"]
    layer_path = tmp_path / "layer.json"
    payload_path = tmp_path / "payload.json"
    layer_path.write_text(json.dumps(layer))
    payload_path.write_text(
        json.dumps(
            {
                "meta": {"payload_version": "today.v1", "scoring_version": 1, "frontend_payload_version": 1},
                "headline": "v1",
                "day_status": "steady",
                "v2": None,
            }
        )
    )
    args = audit.parse_args(
        [
            "--input-activation-layer",
            str(layer_path),
            "--input-final-payload",
            str(payload_path),
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
    assert any(f["kind"] == "payload_v2_missing" for f in summary["failures"])
    # 09 must be null copy, not synthesized block
    assert json.loads((out / "09_payload_v2.json").read_text()) is None


def test_lost_sidecar_id_fails(tmp_path, monkeypatch):
    out = tmp_path / "lost"
    from app.schemas.activation import ActivationLayer

    def bad_build(self, **kwargs):
        layer = ActivationLayer.model_validate(kwargs["sidecar_activation_layer"])
        layer.activations = []
        layer.by_planet = {}
        return layer

    monkeypatch.setattr(audit.ActivationLayerService, "build", bad_build)
    with pytest.raises(SystemExit):
        _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "sidecar_ids_not_preserved" for f in summary["failures"])


def test_missing_scoring_contribution_fails(tmp_path, monkeypatch):
    out = tmp_path / "miss"
    real = audit.ScoringV2Service.score_day

    def drop_contribs(self, day_signals, activation_layer=None):
        res = real(self, day_signals, activation_layer)
        for ss in res.sphere_scores.values():
            ss.contributions = [c for c in ss.contributions if c.source != "activation"]
        return res

    monkeypatch.setattr(audit.ScoringV2Service, "score_day", drop_contribs)
    with pytest.raises(SystemExit):
        _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "missing_scoring_contribution" for f in summary["failures"])


def test_contribution_amount_mismatch_fails(tmp_path, monkeypatch):
    out = tmp_path / "amt"
    real = audit.ScoringV2Service.score_day

    def bump(self, day_signals, activation_layer=None):
        res = real(self, day_signals, activation_layer)
        for ss in res.sphere_scores.values():
            for c in ss.contributions:
                if c.source == "activation":
                    c.amount = float(c.amount) + 0.5
        return res

    monkeypatch.setattr(audit.ScoringV2Service, "score_day", bump)
    with pytest.raises(SystemExit):
        _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "contribution_amount_mismatch" for f in summary["failures"])


def test_convergence_mismatch_fails(tmp_path, monkeypatch):
    out = tmp_path / "conv"
    real = audit.ScoringV2Service.score_day

    def bad_conv(self, day_signals, activation_layer=None):
        res = real(self, day_signals, activation_layer)
        for ss in res.sphere_scores.values():
            if ss.convergence_bonus:
                ss.convergence_bonus = float(ss.convergence_bonus) + 0.25
        return res

    monkeypatch.setattr(audit.ScoringV2Service, "score_day", bad_conv)
    with pytest.raises(SystemExit):
        _run(out, "08_convergence_multi_family.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "convergence_mismatch" for f in summary["failures"])


def test_missing_payload_evidence_fails(tmp_path, monkeypatch):
    out = tmp_path / "pay"
    real = audit.SemanticV2Service.build_v2_block

    def strip_evidence(self, **kwargs):
        block = real(self, **kwargs)
        block.activation_evidence = []
        return block

    monkeypatch.setattr(audit.SemanticV2Service, "build_v2_block", strip_evidence)
    with pytest.raises(SystemExit):
        _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "missing_in_payload_v2" for f in summary["failures"])


def test_unmapped_policy_true_and_false(tmp_path):
    out = tmp_path / "u1"
    with pytest.raises(SystemExit):
        _run(out, "06_unmapped_activation.json", fail_on_unmapped=True)
    s1 = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "unmapped_activation" for f in s1["failures"])

    out2 = tmp_path / "u2"
    s2 = _run(out2, "06_unmapped_activation.json", fail_on_unmapped=False)
    assert s2["warning_count"] >= 1
    assert any(w["kind"] == "unmapped_activation" for w in s2["warnings"])


def test_no_private_production_helpers_imported_for_expected():
    src = Path(_ROOT / "scripts/audit_downstream_v2.py").read_text(encoding="utf-8")
    for banned in [
        "_compute_day_status_v2",
        "_map_activation_to_spheres",
        "_compute_convergence_bonus",
        "_apply_dominance_cap",
    ]:
        assert f"import {banned}" not in src
        # allow mentioning in comments only if not called; ensure not invoked
        assert f"{banned}(" not in src


def test_contribution_trace_csv_has_formula_inputs(tmp_path):
    out = tmp_path / "csv"
    summary = _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    assert summary["status"] == "ok"
    import csv

    rows = list(csv.DictReader((out / "05_contribution_trace.csv").open(encoding="utf-8")))
    mapped = [r for r in rows if r.get("status") == "ok"]
    assert mapped, "expected mapped ok contribution rows"
    for r in mapped:
        for col in ("strength", "family_weight", "target_weight", "polarity_modifier"):
            assert r[col] not in (None, ""), f"{col} empty for {r['activation_id']}/{r['sphere']}"
            float(r[col])  # must be numeric


def test_missing_convergence_debug_fails(tmp_path, monkeypatch):
    out = tmp_path / "conv_dbg"
    real = audit.ScoringV2Service.score_day

    def drop_debug(self, day_signals, activation_layer=None):
        res = real(self, day_signals, activation_layer)
        # Keep numeric bonus but omit debug families entry
        res.debug = dict(res.debug or {})
        res.debug["convergence_by_sphere"] = {}
        return res

    monkeypatch.setattr(audit.ScoringV2Service, "score_day", drop_debug)
    with pytest.raises(SystemExit):
        _run(out, "08_convergence_multi_family.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "convergence_debug_missing" for f in summary["failures"])


def test_wrong_status_rule_fails(tmp_path, monkeypatch):
    out = tmp_path / "status_rule"
    real = audit.ScoringV2Service.score_day

    def bad_rule(self, day_signals, activation_layer=None):
        res = real(self, day_signals, activation_layer)
        bd = dict(res.status_breakdown or {})
        bd["rule"] = "wrong_rule_value"
        res.status_breakdown = bd
        return res

    monkeypatch.setattr(audit.ScoringV2Service, "score_day", bad_rule)
    with pytest.raises(SystemExit):
        _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "day_status_mismatch" for f in summary["failures"])


def test_wrong_status_ratio_nullability_fails(tmp_path, monkeypatch):
    out = tmp_path / "status_ratio"
    real = audit.ScoringV2Service.score_day

    def bad_ratio(self, day_signals, activation_layer=None):
        res = real(self, day_signals, activation_layer)
        bd = dict(res.status_breakdown or {})
        # Force nullability mismatch: if ratio is numeric make null, else invent a number
        if bd.get("ratio") is None:
            bd["ratio"] = 1.23
        else:
            bd["ratio"] = None
        res.status_breakdown = bd
        return res

    monkeypatch.setattr(audit.ScoringV2Service, "score_day", bad_ratio)
    with pytest.raises(SystemExit):
        _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "day_status_mismatch" for f in summary["failures"])


def test_unexpected_cap_contribution_fails(tmp_path, monkeypatch):
    out = tmp_path / "uncap"
    real = audit.ScoringV2Service.score_day
    from app.schemas.scoring_v2 import SphereContribution

    def inject_cap(self, day_signals, activation_layer=None):
        res = real(self, day_signals, activation_layer)
        # Prefer a positive raw, non-capped sphere so the main cap branch also sees it
        candidates = sorted(
            res.sphere_scores.items(),
            key=lambda kv: (0 if float(kv[1].raw_score) > 0 else 1, kv[0]),
        )
        for skey, ss in candidates:
            if ss.dominance_capped or any(c.source == "cap" for c in ss.contributions):
                continue
            ss.contributions = list(ss.contributions) + [
                SphereContribution(
                    sphere=skey,
                    source="cap",
                    source_id=f"cap:{skey}",
                    amount=-0.01,
                    before=float(ss.raw_score),
                    after=float(ss.final_score),
                    evidence="injected unexpected cap",
                )
            ]
            break
        return res

    monkeypatch.setattr(audit.ScoringV2Service, "score_day", inject_cap)
    with pytest.raises(SystemExit):
        _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "dominance_cap_unexpected" for f in summary["failures"])


def test_unknown_payload_score_source_fails(tmp_path, monkeypatch):
    out = tmp_path / "unksrc"
    real = audit.SemanticV2Service.build_v2_block

    def inject_unknown(self, **kwargs):
        block = real(self, **kwargs)
        # Mutate first sphere score breakdown contribution source to unknown
        sb = block.score_breakdown
        if isinstance(sb, dict):
            for _k, ss in sb.items():
                contribs = getattr(ss, "contributions", None)
                if contribs is None and isinstance(ss, dict):
                    contribs = ss.get("contributions")
                if not contribs:
                    continue
                c0 = contribs[0]
                if hasattr(c0, "source"):
                    c0.source = "mystery_source"
                elif isinstance(c0, dict):
                    c0["source"] = "mystery_source"
                break
        return block

    monkeypatch.setattr(audit.SemanticV2Service, "build_v2_block", inject_unknown)
    with pytest.raises(SystemExit):
        _run(out, "12_payload_mapping.json", fail_on_unmapped=False)
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text())
    assert any(f["kind"] == "payload_score_unknown_source" for f in summary["failures"])
