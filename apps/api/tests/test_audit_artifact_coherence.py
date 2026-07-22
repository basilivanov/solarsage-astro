# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_AUDIT_ARTIFACT_COHERENCE — baseline package.
# ROLE: Proves the committed audit artifact package is ONE generation:
#       same user/profile/date across input profile, wire payload, claims
#       and summary; payload V2 identity coherent; frozen artifact_source
#       deterministic (no dynamic git HEAD); downstream audit green.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-AUDIT-ARTIFACT-COHERENCE
# purpose: Fail closed on mixed-generation or self-referencing artifact sets.
# owns:
#   - apps/api/tests/test_audit_artifact_coherence.py
# inputs: committed artifacts/audit/2026-07-08 package (read-only).
# outputs: assertions on cross-file coherence.
# dependencies: none (json/re only).
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - One user_id and one date across 00/11/14/15.
#   - meta.payloadVersion V2 series + coherent frontend + v2 block; the
#     schemaVersion literal is canonically "today/v1".
#   - Frozen artifact_source carries no dynamic git_head.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-AUDIT-ARTIFACT-COHERENCE

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE = REPO_ROOT / "artifacts" / "audit" / "2026-07-08"

V2_FRONTEND_BY_PAYLOAD_VERSION = {"today.v2": 2, "today.v2.1": 3}


def _read(name: str):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def test_single_user_and_date_across_package() -> None:
    profile = _read("00_input_profile.json")
    user_id = profile["user_id"]
    payload = _read("11_final_today_payload.json")
    date = payload["date"]
    assert date == "2026-07-08"

    claims = (BASE / "14_claims_audit.md").read_text(encoding="utf-8")
    assert user_id in claims
    assert date in claims
    assert payload["headline"] in claims
    assert payload["dayStatus"] in claims

    summary = (BASE / "15_audit_summary.md").read_text(encoding="utf-8")
    assert user_id in summary
    assert date in summary


def test_payload_v2_identity_coherent() -> None:
    payload = _read("11_final_today_payload.json")
    meta = payload["meta"]
    assert meta["schemaVersion"] == "today/v1"  # canonical literal for ALL series
    expected_frontend = V2_FRONTEND_BY_PAYLOAD_VERSION.get(meta["payloadVersion"])
    assert expected_frontend is not None, f"payloadVersion {meta['payloadVersion']} is not a V2 series"
    assert meta["frontendPayloadVersion"] == expected_frontend
    assert payload.get("v2") is not None
    assert "generatedAt" in meta and "generated_at" not in meta  # wire camelCase root


def test_frozen_artifact_source_is_deterministic() -> None:
    source = _read("artifact_source.json")
    # A commit can never know its own SHA in advance: the tracked frozen
    # provenance carries no dynamic git HEAD (live keeps it separately).
    assert source.get("git_head") is None
    assert source["mode"] == "frozen-baseline"
    assert source["final_has_v2_block"] is True


def test_activation_layer_and_downstream_green() -> None:
    layer = _read("16_activation_layer.json")
    payload = _read("11_final_today_payload.json")
    assert layer.get("target_date") == payload["date"]
    assert layer.get("target_tz") == "Europe/Moscow"

    downstream = _read("downstream/12_downstream_audit_summary.json")
    assert downstream["status"] == "ok"
    assert downstream["failure_count"] == 0
    assert downstream["unmapped_policy"] == "warn"


def test_oracle_artifacts_green() -> None:
    astronomy = _read("13_astronomy_oracle_summary.json")
    assert astronomy["longitude_pass"] is True
    assert astronomy["retrograde_flag_pass"] is True
    assert astronomy["house_pass"] is True
    assert astronomy["moon_phase"]["pass"] is True

    scoring = _read("12_scoring_oracle_comparison.json")
    assert "oracle" in scoring and "comparison" in scoring


def test_sidecar_provenance_identity_pinned() -> None:
    provenance = _read("provenance_sidecar.json")
    assert provenance["image"] == "solarsage-sidecar-readiness:62b756a"
    assert provenance["image_id"] == (
        "sha256:6d20eb612c79660cfb1068fae4bed8a31c17d8ab7f600a81975654277ee1ca7d"
    )
    assert provenance["revision"] == provenance["release_sha"]
    assert provenance["engine"] == "swieph"
    assert provenance["fallback"] is False
    assert provenance["calculation_version"] == "ss-calc-1.2.0"
    assert provenance["ephemeris_artifact_id"] == "se-stellium-1800-2399-20260721"
    assert len(provenance["ephemeris_manifest_sha256"]) == 64
    # The live run directory must not be re-committed next to this file.
    assert not (BASE / "live").exists()
