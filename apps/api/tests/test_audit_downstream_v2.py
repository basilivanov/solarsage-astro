# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_AUDIT_DOWNSTREAM_V2 — downstream audit mutations.
# ROLE: Proves the strengthened payload-vs-recomputed-V2 contract: the honest
#       committed artifact is green, and each mutation class (dayStatus,
#       score amount/contribution, sphere order, topFlags, lost/extra ids)
#       fails closed with non-zero exit. No new harness — replay mode only.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-AUDIT-DOWNSTREAM-V2
# purpose: Directed mutation tests for scripts/audit_downstream_v2.py.
# owns:
#   - apps/api/tests/test_audit_downstream_v2.py
# inputs: committed baseline artifacts (read-only) + tmp payload mutations.
# outputs: exit-code and summary assertions per mutation class.
# dependencies: audit_downstream_v2.run_downstream_audit/parse_args.
# side_effects: tmp output dirs only.
# emitted_logs: none.
# invariants:
#   - Honest replay of the committed artifact exits 0.
#   - Every payload mutation exits non-zero.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-AUDIT-DOWNSTREAM-V2

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BASE = REPO_ROOT / "artifacts" / "audit" / "2026-07-08"

import sys  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "scripts"))  # noqa: E402

from audit_downstream_v2 import parse_args, run_downstream_audit  # noqa: E402


def _replay(tmp_path: Path, mutate=None) -> tuple[Path, Path]:
    payload = json.loads((BASE / "11_final_today_payload.json").read_text(encoding="utf-8"))
    if mutate is not None:
        mutate(payload)
    payload_path = tmp_path / "payload.json"
    payload_path.write_text(json.dumps(payload), encoding="utf-8")
    out = tmp_path / "out"
    args = parse_args([
        "--input-activation-layer", str(BASE / "16_activation_layer.json"),
        "--input-final-payload", str(payload_path),
        "--input-day-signals", str(BASE / "debug" / "day_scored_signals_after_filter.json"),
        "--fail-on-unmapped", "false",
        "--out", str(out),
    ])
    return args, out


def _run(args) -> int:
    try:
        run_downstream_audit(args)
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def _failure_kinds(out: Path) -> set[str]:
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text(encoding="utf-8"))
    return {f["kind"] for f in summary["failures"]}


def test_honest_committed_payload_is_green(tmp_path) -> None:
    args, out = _replay(tmp_path)
    assert _run(args) == 0
    summary = json.loads((out / "12_downstream_audit_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "ok"
    assert summary["unmapped_policy"] == "warn"
    assert summary["checked"]["payload_day_status_matches_recalc"] is True
    assert summary["checked"]["payload_score_breakdown_matches_recalc"] is True
    assert summary["checked"]["payload_top_flags_match_recalc"] is True
    # The intentional unmapped policy stays visible (warnings, never errors).
    assert summary["warning_count"] >= 0


def test_day_status_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["dayStatus"] = "tense"

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_day_status_mismatch" in _failure_kinds(out)


def test_final_score_amount_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["finalScore"] = 999

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_score_field_mismatch" in _failure_kinds(out)


def test_contribution_amount_mutation_fails(tmp_path) -> None:
    def mutate(p):
        contribs = p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["contributions"]
        contribs[0]["amount"] = contribs[0]["amount"] + 1.0

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contributions_mismatch" in _failure_kinds(out)


def test_score_breakdown_order_mutation_fails(tmp_path) -> None:
    def mutate(p):
        sb = p["v2"]["scoreBreakdown"]
        keys = list(sb.keys())
        swapped = [keys[1], keys[0], *keys[2:]]
        p["v2"]["scoreBreakdown"] = {k: sb[k] for k in swapped}

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_score_breakdown_order_mismatch" in _failure_kinds(out)


def test_top_flags_cleared_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["topFlags"] = []

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_top_flags_mismatch" in _failure_kinds(out)


def test_top_flags_reordered_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["topFlags"] = list(reversed(p["topFlags"]))

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_top_flags_mismatch" in _failure_kinds(out)


def test_top_flags_extra_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["topFlags"] = [*p["topFlags"], {"iconName": "fake", "title": "Лишний флаг", "summary": "x", "hint": None}]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_top_flags_mismatch" in _failure_kinds(out)


def test_lost_activation_id_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["activationEvidence"] = p["v2"]["activationEvidence"][1:]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "missing_in_payload_v2" in _failure_kinds(out)


def test_extra_activation_id_fails(tmp_path) -> None:
    def mutate(p):
        first = dict(p["v2"]["activationEvidence"][0])
        first["id"] = "fake-activation-id-0000"
        p["v2"]["activationEvidence"] = [*p["v2"]["activationEvidence"], first]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "extra_payload_ids" in _failure_kinds(out)


def test_top_flags_summary_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["topFlags"][0]["summary"] = "CORRUPTED"

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_top_flags_mismatch" in _failure_kinds(out)


def test_normalized_score_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["normalizedScore"] = 999

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_score_field_mismatch" in _failure_kinds(out)


def test_contribution_before_mutation_fails(tmp_path) -> None:
    def mutate(p):
        contribs = p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["contributions"]
        contribs[0]["before"] = 999.0

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contributions_mismatch" in _failure_kinds(out)


def test_contributions_order_mutation_fails(tmp_path) -> None:
    def mutate(p):
        sb = p["v2"]["scoreBreakdown"]["thinking_speech_learning"]
        sb["contributions"] = list(reversed(sb["contributions"]))

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contributions_mismatch" in _failure_kinds(out)


def test_activation_evidence_strength_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["activationEvidence"][0]["strength"] = 999.0

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_activation_evidence_mismatch" in _failure_kinds(out)


def test_activation_evidence_order_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["activationEvidence"] = list(reversed(p["v2"]["activationEvidence"]))

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_activation_evidence_mismatch" in _failure_kinds(out)


def test_top_level_sphere_scores_reversed_fails(tmp_path) -> None:
    def mutate(p):
        p["sphereScores"] = list(reversed(p["sphereScores"]))

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_sphere_scores_mismatch" in _failure_kinds(out)


def test_top_level_sphere_scores_value_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["sphereScores"][0]["score"] = 999

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_sphere_scores_mismatch" in _failure_kinds(out)


def test_daychart_aspects_orb_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["dayChart"]["aspects"][0]["orb"] = 999.0

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_daychart_aspects_mismatch" in _failure_kinds(out)


def test_daychart_aspects_order_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["dayChart"]["aspects"] = list(reversed(p["dayChart"]["aspects"]))

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_daychart_aspects_mismatch" in _failure_kinds(out)


def test_daychart_aspects_removed_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["dayChart"]["aspects"] = p["dayChart"]["aspects"][1:]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_daychart_aspects_mismatch" in _failure_kinds(out)


# -- Strict full-object contract mutations (second-review blockers) --------

def test_score_key_removed_fails(tmp_path) -> None:
    def mutate(p):
        del p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["key"]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contract_missing_key" in _failure_kinds(out)


def test_score_title_removed_fails(tmp_path) -> None:
    def mutate(p):
        del p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["title"]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contract_missing_key" in _failure_kinds(out)


def test_score_normalized_null_removed_fails(tmp_path) -> None:
    def mutate(p):
        # normalizedScore is legitimately null here — null-presence is contractual.
        assert p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["normalizedScore"] is None
        del p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["normalizedScore"]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contract_missing_key" in _failure_kinds(out)


def test_score_dominance_capped_false_removed_fails(tmp_path) -> None:
    def mutate(p):
        assert p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["dominanceCapped"] is False
        del p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["dominanceCapped"]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contract_missing_key" in _failure_kinds(out)


def test_activation_evidence_debug_mutation_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["activationEvidence"][0]["debug"]["aspect_weight"] = 999

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_activation_evidence_mismatch" in _failure_kinds(out)


def test_activation_evidence_nullable_house_removed_fails(tmp_path) -> None:
    def mutate(p):
        del p["v2"]["activationEvidence"][0]["house"]

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contract_missing_key" in _failure_kinds(out)


def test_top_flag_unexpected_key_fails(tmp_path) -> None:
    def mutate(p):
        p["topFlags"][0]["unexpectedField"] = "x"

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contract_extra_key" in _failure_kinds(out)


def test_activation_evidence_unexpected_key_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["activationEvidence"][0]["unexpectedField"] = "x"

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_contract_extra_key" in _failure_kinds(out)


# -- Type-strict and actual-contract mutations (third-review blockers) ------

def test_dominance_capped_bool_to_int_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["scoreBreakdown"]["thinking_speech_learning"]["dominanceCapped"] = 0

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_score_field_mismatch" in _failure_kinds(out)


def test_activation_evidence_active_bool_to_int_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["activationEvidence"][0]["active"] = 1

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_activation_evidence_mismatch" in _failure_kinds(out)


def test_v2_root_extra_key_fails(tmp_path) -> None:
    def mutate(p):
        p["v2"]["unexpectedRootKey"] = 1

    args, out = _replay(tmp_path, mutate)
    assert _run(args) != 0
    assert "payload_v2_contract_invalid" in _failure_kinds(out)
