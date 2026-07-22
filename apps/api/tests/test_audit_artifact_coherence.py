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
    # Every declared check ran and passed — no silent unchecked surface.
    assert all(downstream["checked"].values()), downstream["checked"]
    # The intentional unmapped policy stays visible and pinned: exactly the
    # current 24 known-unmapped activations, reported as warnings only.
    assert downstream["warning_count"] == len(downstream["warnings"]) == 24


def test_scoring_oracle_comparison_all_pass() -> None:
    comparison = _read("12_scoring_oracle_comparison.json")["comparison"]
    assert comparison["day_status"]["pass"] is True
    sphere_scores = comparison["sphere_scores"]
    assert sphere_scores and all(v["pass"] is True for v in sphere_scores.values())
    assert comparison["top_signals"]["pass"] is True


def test_oracle_artifacts_green() -> None:
    astronomy = _read("13_astronomy_oracle_summary.json")
    assert astronomy["longitude_pass"] is True
    assert astronomy["sign_pass"] is True
    assert astronomy["retrograde_flag_pass"] is True
    assert astronomy["house_pass"] is True
    assert astronomy["moon_phase"]["pass"] is True
    # FINAL dayChart proof: exact structure/order/count, transit
    # longitude/sign/retrograde/motion and serialized houses
    # (number/order/cusp/sign) against the independent Swiss result.
    assert astronomy["final_transit_structure_pass"] is True
    assert astronomy["final_transit_longitude_pass"] is True
    assert astronomy["final_transit_sign_pass"] is True
    assert astronomy["final_transit_retrograde_pass"] is True
    assert astronomy["final_motion_pass"] is True
    assert astronomy["final_house_structure_pass"] is True
    assert astronomy["final_house_cusp_pass"] is True
    assert astronomy["final_house_sign_pass"] is True
    # Engine proof: the canonical audit runs on the pinned Swiss artifact,
    # never on the moshier fallback.
    engine = astronomy["engine"]
    assert engine["swieph"] is True
    assert engine["moseph"] is False
    assert engine["engine_pass"] is True
    assert engine["policy"] == "swieph"

    scoring = _read("12_scoring_oracle_comparison.json")
    assert "oracle" in scoring and "comparison" in scoring


def test_wave17_layer_matches_canonical_http_layer() -> None:
    """The standalone wave artifact 17 is generated with the same profile,
    current location and house system as the canonical HTTP layer 16, so
    their ordered activation ids are identical (no return-location fallback)."""
    canonical = _read("16_activation_layer.json")
    wave = _read("17_sidecar_activation_layer.json")
    canonical_ids = [a["id"] for a in canonical["activations"]]
    wave_ids = [a["id"] for a in wave["activations"]]
    assert wave_ids == canonical_ids
    assert wave.get("house_system") == canonical.get("house_system")
    assert not any("return_location_fallback" in w for w in wave.get("warnings", []))


def test_sidecar_provenance_identity_pinned() -> None:
    provenance = _read("provenance_sidecar.json")
    assert provenance["image"] == "solarsage-sidecar-readiness:62b756a"
    assert provenance["image_id"] == (
        "sha256:6d20eb612c79660cfb1068fae4bed8a31c17d8ab7f600a81975654277ee1ca7d"
    )
    # Exact full identity, not just internal consistency.
    assert provenance["revision"] == "62b756a6559ba4a0f501fffe56dca51eb52872b2"
    assert provenance["release_sha"] == "62b756a6559ba4a0f501fffe56dca51eb52872b2"
    assert provenance["engine"] == "swieph"
    assert provenance["fallback"] is False
    assert provenance["calculation_version"] == "ss-calc-1.2.0"
    assert provenance["ephemeris_artifact_id"] == "se-stellium-1800-2399-20260721"
    assert provenance["ephemeris_manifest_sha256"] == (
        "768d5fc920c762028437ad0bff43013c800ff027911a2dc02cb7d45d7ea9db59"
    )
    # The live run directory must not be re-committed next to this file.
    assert not (BASE / "live").exists()
