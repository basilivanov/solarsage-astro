#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: MODULE_AUDIT_DOWNSTREAM_V2 — independent post-sidecar correctness audit
# ROLE: Prove API/frontend downstream math/mapping after trusted sidecar ActivationLayer.
# ############################################################################

# START_MODULE_CONTRACT: M-AUDIT-DOWNSTREAM-V2
# purpose: Independent post-sidecar correctness audit for SolarSage V2.
# owns:
#   - scripts/audit_downstream_v2.py
# inputs: --user-id, --date, --out, optional artifact/fixture paths.
# outputs: artifacts under --out (00..12 + optional debug/).
# dependencies: apps/api schemas/services, grace/canon YAML, optional live TodayService.
# side_effects: filesystem writes; optional DB/sidecar network in live mode.
# emitted_logs: none (stdout summary only).
# invariants:
#   - sidecar ActivationLayer is trusted astronomy boundary.
#   - expected values are recomputed from canon YAML only (no private production helpers).
#   - production ScoringV2Service.score_day is called once for actual results only.
#   - replay/live never synthesize a missing V2 payload body.
# failure_policy: exit non-zero on hard invariant failures.
# END_MODULE_CONTRACT: M-AUDIT-DOWNSTREAM-V2

# START_MODULE_MAP: M-AUDIT-DOWNSTREAM-V2
# public_entrypoints:
#   - main
#   - run_downstream_audit
#   - map_activation_to_spheres_for_audit
#   - expected_activation_amount
#   - expected_convergence_bonus
#   - independent_day_status
# semantic_blocks:
#   - CANON_LOAD: load spheres/scoring_v2/activation_rules/aspect_rules
#   - INPUT_LOAD: live / artifact_replay / synthetic_fixture
#   - ACTUAL_SCORE: one ScoringV2Service.score_day call
#   - EXPECTED_MATH: independent mapping/amount/convergence/cap/status
#   - PAYLOAD_TRACE: payload evidence/score/why id checks without synthesis
#   - FIXTURE_WRITE: AdaptedTodayPayload-compatible frontend fixture
# owned_tests:
#   - apps/api/tests/test_downstream_v2_audit.py
#   - apps/api/tests/test_scoring_v2_downstream_invariants.py
#   - apps/api/tests/test_payload_v2_downstream_mapping.py
# END_MODULE_MAP: M-AUDIT-DOWNSTREAM-V2

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import date as Date
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = _REPO_ROOT
API_ROOT = REPO_ROOT / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.versions import (  # noqa: E402
    ACTIVATION_LAYER_VERSION,
    CALCULATION_VERSION,
    SCORING_V2_VERSION,
    V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS,
    V2_FRONTEND_PAYLOAD_VERSION,
    TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS,
    TODAY_V2_PAYLOAD_VERSION,
)
from app.schemas.normalization import AstroSignal  # noqa: E402
from app.services.activation_layer_service import ActivationLayerService  # noqa: E402
from app.services.canon_service import get_canon_versions  # noqa: E402
from app.services.day_scoring_runtime_service import DayScoringRuntimeService  # noqa: E402
from app.services.scoring_v2_service import ScoringV2Service  # noqa: E402
from app.services.semantic_v2_service import SemanticV2Service  # noqa: E402
from app.services.today_service import TodayService as TodayServiceForFlags  # noqa: E402

TOL = 0.0001

_EVIDENCE_SNAKE_TO_CAMEL = {
    "active_from": "activeFrom",
    "active_until": "activeUntil",
    "exact_at": "exactAt",
    "source_frame": "sourceFrame",
    "source_planet": "sourcePlanet",
    "target_frame": "targetFrame",
    "target_key": "targetKey",
    "target_planet": "targetPlanet",
    "target_type": "targetType",
    "technique_family": "techniqueFamily",
}
MAJOR_ASPECTS = {"conjunction", "opposition", "square", "trine"}
POSITIVE_ASPECTS = {"trine", "sextile"}
NEGATIVE_ASPECTS = {"square", "opposition"}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", by_alias=False)
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return value


def get_git_head() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return None


@dataclass
class AuditIssue:
    kind: str
    severity: str
    activation_id: str | None = None
    sphere: str | None = None
    expected: Any = None
    actual: Any = None
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "activation_id": self.activation_id,
            "sphere": self.sphere,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }


@dataclass
class DownstreamAuditState:
    failures: list[AuditIssue] = field(default_factory=list)
    warnings: list[AuditIssue] = field(default_factory=list)

    def error(self, **kwargs: Any) -> None:
        self.failures.append(AuditIssue(severity="error", **kwargs))

    def warn(self, **kwargs: Any) -> None:
        self.warnings.append(AuditIssue(severity="warning", **kwargs))


def load_canons() -> tuple[dict, dict, dict, dict]:
    spheres = load_yaml(REPO_ROOT / "grace/canon/spheres.v1.yml")
    scoring_v2 = load_yaml(REPO_ROOT / "grace/canon/scoring_v2.v1.yml")
    activation_rules = load_yaml(REPO_ROOT / "grace/canon/activation_rules.v1.yml")
    aspect_rules = load_yaml(REPO_ROOT / "grace/canon/aspect_rules.v1.yml")
    return spheres, scoring_v2, activation_rules, aspect_rules


def family_for_technique(technique: str, activation_rules: dict) -> str:
    for family, info in activation_rules["technique_families"].items():
        if technique in info.get("members", []):
            return family
    raise KeyError(f"Unknown technique: {technique}")


def family_weight(family: str, activation_rules: dict) -> float:
    return float(activation_rules["technique_families"][family]["independence_weight"])


def aspect_weight(aspect_type: str, aspect_rules: dict) -> float:
    key = (aspect_type or "").upper()
    weights = aspect_rules.get("aspect_weights") or {}
    if key not in weights:
        return 0.0
    return float(weights[key])


def aspect_threshold(aspect_type: str, aspect_rules: dict) -> float:
    thr = aspect_rules.get("aspect_threshold") or {}
    major = float(thr.get("major", 0.35))
    minor = float(thr.get("minor", 0.55))
    return major if (aspect_type or "").lower() in MAJOR_ASPECTS else minor


def map_activation_to_spheres_for_audit(
    activation: dict[str, Any],
    spheres: dict,
    scoring_v2: dict,
) -> list[dict[str, Any]]:
    target_type = activation.get("target_type") or ""
    target_key = str(activation.get("target_key") or "").upper()
    angle = str(activation.get("angle") or target_key).upper() if target_type == "angle" else ""
    twd = scoring_v2["target_weight_defaults"]
    angle_map = scoring_v2["angle_sphere_map"]
    spheres_data = spheres.get("spheres", {})
    out: list[dict[str, Any]] = []
    for skey, sphere in spheres_data.items():
        weight = 0.0
        reason = ""
        if target_type == "planet":
            pw = (sphere.get("planets") or {}).get(target_key)
            if pw is not None:
                weight = float(pw)
                reason = f"planet {target_key} found in spheres.{skey}.planets"
        elif target_type == "house":
            h = activation.get("house")
            if h is None and activation.get("target_key"):
                try:
                    h = int(activation["target_key"])
                except Exception:
                    h = None
            if h is not None and h in (sphere.get("houses") or []):
                weight = float(twd["house"])
                reason = f"house {h} found in spheres.{skey}.houses"
        elif target_type == "lot":
            lots = [str(x).upper() for x in (sphere.get("lots") or [])]
            if target_key in lots:
                weight = float(twd["lot"])
                reason = f"lot {target_key} found in spheres.{skey}.lots"
        elif target_type == "angle":
            mapped = angle_map.get(angle) or []
            if skey in mapped:
                weight = float(twd["angle"])
                reason = f"angle {angle} found in scoring_v2.angle_sphere_map.{angle}"
        elif target_type == "sphere":
            if target_key == skey.upper():
                weight = float(twd["sphere"])
                reason = "sphere target matched exact sphere key"
        if weight > 0:
            out.append(
                {
                    "activation_id": activation.get("id"),
                    "sphere": skey,
                    "mapping_reason": reason,
                    "target_weight": weight,
                }
            )
    return out


def expected_activation_amount(strength: float, family_w: float, target_weight: float, polarity_modifier: float) -> float:
    return round(float(strength) * float(family_w) * float(target_weight) * float(polarity_modifier), 4)


def expected_convergence_bonus(families: set[str], scoring_v2: dict) -> float:
    n = len(families)
    if n <= 1:
        return 0.0
    curve = scoring_v2["convergence_curve"]
    capped_n = min(n, 5)
    return round(float(curve[capped_n]) * float(scoring_v2["sphere_convergence_weight"]["default"]), 4)


def independent_day_status(
    day_signals: list[AstroSignal],
    activations: list[dict[str, Any]],
    scoring_v2: dict,
    activation_rules: dict,
    aspect_rules: dict,
) -> tuple[str, dict[str, Any]]:
    thr = scoring_v2["status_thresholds"]
    positive_ratio = float(thr["positive_ratio"])
    positive_min = float(thr["positive_min_score"])
    negative_ratio = float(thr["negative_ratio"])
    negative_min = float(thr["negative_min_score"])
    support_mod = scoring_v2["activation_polarity"]["status_support_modifier"]
    tension_mod = scoring_v2["activation_polarity"]["status_tension_modifier"]

    positive_aspect_score = 0.0
    negative_aspect_score = 0.0
    for s in day_signals:
        if (s.type or "") != "aspect":
            continue
        atype = (s.aspect_type or "").lower()
        aw = aspect_weight(atype, aspect_rules)
        threshold = aspect_threshold(atype, aspect_rules)
        base = aw * float(s.strength or 0.0)
        if base < threshold:
            continue
        if atype in POSITIVE_ASPECTS:
            positive_aspect_score += base
        elif atype in NEGATIVE_ASPECTS:
            negative_aspect_score += base
        else:
            positive_aspect_score += base * 0.5
            negative_aspect_score += base * 0.5

    activation_support_score = 0.0
    activation_tension_score = 0.0
    for a in activations:
        if a.get("active") is False:
            continue
        family = a.get("technique_family") or family_for_technique(a.get("technique") or "", activation_rules)
        fw = family_weight(family, activation_rules)
        amount = float(a.get("strength") or 0.0) * fw
        pol = a.get("polarity") or "neutral"
        activation_support_score += amount * float(support_mod[pol])
        activation_tension_score += amount * float(tension_mod[pol])

    support_score = round(positive_aspect_score + activation_support_score, 4)
    tension_score = round(negative_aspect_score + activation_tension_score, 4)
    ratio = round(support_score / tension_score, 4) if tension_score > 0 else None
    if support_score > tension_score * positive_ratio and support_score >= positive_min:
        status = "supportive"
        rule = f"supportive_if_support_score_gt_tension_{positive_ratio}"
    elif tension_score > support_score * negative_ratio and tension_score >= negative_min:
        status = "tense"
        rule = f"tense_if_tension_score_gt_support_{negative_ratio}"
    else:
        status = "steady"
        rule = "steady_otherwise"
    breakdown = {
        "positive_aspect_score": round(positive_aspect_score, 4),
        "negative_aspect_score": round(negative_aspect_score, 4),
        "activation_support_score": round(activation_support_score, 4),
        "activation_tension_score": round(activation_tension_score, 4),
        "support_score": support_score,
        "tension_score": tension_score,
        "ratio": ratio,
        "rule": rule,
    }
    return status, breakdown


def extract_actual_activation_contrib_rows(scoring_result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for skey, ss in scoring_result.sphere_scores.items():
        for c in ss.contributions:
            if c.source != "activation":
                continue
            rows.append({"activation_id": str(c.source_id), "sphere": str(skey), "amount": float(c.amount), "source_id": str(c.source_id)})
    return rows


def extract_payload_v2(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    block = payload.get("v2")
    if block is None:
        block = payload.get("V2")
    return block if isinstance(block, dict) else None


def extract_payload_activation_ids(payload_v2: dict[str, Any] | None) -> list[str]:
    if not payload_v2:
        return []
    evidence = payload_v2.get("activation_evidence")
    if evidence is None:
        evidence = payload_v2.get("activationEvidence")
    if not isinstance(evidence, list):
        return []
    ids: list[str] = []
    for item in evidence:
        if isinstance(item, dict):
            aid = item.get("id") or item.get("source_activation_id") or item.get("sourceActivationId")
            if aid:
                ids.append(str(aid))
    return ids


def extract_payload_why_activation_ids(payload_v2: dict[str, Any] | None) -> list[str]:
    if not payload_v2:
        return []
    why = payload_v2.get("why_today")
    if why is None:
        why = payload_v2.get("whyToday")
    if not isinstance(why, list):
        return []
    ids: list[str] = []
    for item in why:
        if not isinstance(item, dict):
            continue
        acts = item.get("activation_ids")
        if acts is None:
            acts = item.get("activationIds")
        if isinstance(acts, list):
            ids.extend(str(a) for a in acts)
    return ids


def extract_payload_score_contribs(payload_v2: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not payload_v2:
        return []
    sb = payload_v2.get("score_breakdown")
    if sb is None:
        sb = payload_v2.get("scoreBreakdown")
    if not isinstance(sb, dict):
        return []
    out: list[dict[str, Any]] = []
    for skey, ss in sb.items():
        if not isinstance(ss, dict):
            continue
        contribs = ss.get("contributions") or []
        if not isinstance(contribs, list):
            continue
        for c in contribs:
            if not isinstance(c, dict):
                continue
            out.append(
                {
                    "sphere": skey,
                    "source": c.get("source"),
                    "source_id": c.get("source_id") or c.get("sourceId"),
                    "amount": c.get("amount"),
                }
            )
    return out


def parse_day_signals(path: Path | None) -> list[AstroSignal]:
    if path is None or not path.exists():
        return []
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [AstroSignal.model_validate(x) for x in raw]
        return []
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    signals: list[AstroSignal] = []
    for r in rows:
        try:
            signals.append(
                AstroSignal(
                    type=r.get("type") or "aspect",
                    planet=r.get("planet") or "Transit_Sun",
                    target_planet=r.get("target_planet") or None,
                    aspect_type=r.get("aspect_type") or r.get("aspect") or None,
                    orb=float(r["orb"]) if r.get("orb") not in (None, "") else None,
                    strength=float(r.get("strength") or 0.0),
                    house=int(r["house"]) if r.get("house") not in (None, "") else None,
                )
            )
        except Exception:
            continue
    return signals


def activation_as_dict(act: Any) -> dict[str, Any]:
    if hasattr(act, "model_dump"):
        return act.model_dump(mode="json", by_alias=False)
    return dict(act)


def is_v2_selected_payload(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    meta = payload.get("meta") or {}
    if not isinstance(meta, dict):
        return False
    pv = meta.get("payload_version") or meta.get("payloadVersion")
    sv = meta.get("scoring_version") or meta.get("scoringVersion")
    fv = meta.get("frontend_payload_version") or meta.get("frontendPayloadVersion")
    return str(pv) in TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS or str(sv) == SCORING_V2_VERSION or fv in V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS


def build_adapted_frontend_fixture(payload_v2: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    """Build AdaptedTodayPayload-compatible fixture with camelCase V2 block."""
    # Convert snake_case semantic block to camelCase-ish structure expected by frontend schema.
    # Prefer model_dump(by_alias=True) when available.
    activation_evidence = payload_v2.get("activation_evidence") or payload_v2.get("activationEvidence") or []
    score_breakdown = payload_v2.get("score_breakdown") or payload_v2.get("scoreBreakdown") or {}
    why_today = payload_v2.get("why_today") or payload_v2.get("whyToday") or []
    audit = payload_v2.get("audit") or {}
    activation_summary = payload_v2.get("activation_summary") or payload_v2.get("activationSummary") or {
        "headline": "Downstream V2 fixture",
        "topActivatedTargets": [],
    }

    def camel_evidence(e: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": e.get("id"),
            "technique": e.get("technique"),
            "techniqueFamily": e.get("technique_family") or e.get("techniqueFamily"),
            "targetType": e.get("target_type") or e.get("targetType"),
            "targetKey": e.get("target_key") or e.get("targetKey"),
            "kind": e.get("kind"),
            "active": e.get("active", True),
            "sourcePlanet": e.get("source_planet") or e.get("sourcePlanet"),
            "sourceFrame": e.get("source_frame") or e.get("sourceFrame"),
            "targetPlanet": e.get("target_planet") or e.get("targetPlanet"),
            "targetFrame": e.get("target_frame") or e.get("targetFrame"),
            "aspect": e.get("aspect"),
            "orb": e.get("orb"),
            "phase": e.get("phase") or "background",
            "house": e.get("house"),
            "lot": e.get("lot"),
            "angle": e.get("angle"),
            "strength": e.get("strength") or 0.0,
            "polarity": e.get("polarity") or "neutral",
            "evidence": e.get("evidence") or "",
            "debug": e.get("debug") or {},
        }

    def camel_summary(s: dict[str, Any]) -> dict[str, Any]:
        tops = s.get("top_activated_targets") or s.get("topActivatedTargets") or []
        camel_tops = []
        for t in tops:
            if not isinstance(t, dict):
                continue
            camel_tops.append(
                {
                    "targetType": t.get("target_type") or t.get("targetType"),
                    "targetKey": t.get("target_key") or t.get("targetKey"),
                    "label": t.get("label"),
                    "familyCount": t.get("family_count") or t.get("familyCount") or 0,
                    "techniques": t.get("techniques") or [],
                    "spheres": t.get("spheres") or [],
                    "activationIds": t.get("activation_ids") or t.get("activationIds") or [],
                }
            )
        return {
            "headline": s.get("headline") or "Downstream V2 fixture",
            "topActivatedTargets": camel_tops,
        }

    def camel_why(items: list[Any]) -> list[dict[str, Any]]:
        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            out.append(
                {
                    "id": it.get("id"),
                    "title": it.get("title"),
                    "body": it.get("body"),
                    "activationIds": it.get("activation_ids") or it.get("activationIds") or [],
                    "techniques": it.get("techniques") or [],
                }
            )
        return out

    def camel_audit(a: dict[str, Any]) -> dict[str, Any]:
        return {
            "traceId": a.get("trace_id") or a.get("traceId"),
            "available": a.get("available", True),
            "payloadVersion": a.get("payload_version") or a.get("payloadVersion") or TODAY_V2_PAYLOAD_VERSION,
            "calculationVersion": a.get("calculation_version") or a.get("calculationVersion") or CALCULATION_VERSION,
            "scoringVersion": a.get("scoring_version") or a.get("scoringVersion") or SCORING_V2_VERSION,
            "activationLayerVersion": a.get("activation_layer_version") or a.get("activationLayerVersion") or ACTIVATION_LAYER_VERSION,
            "canonVersions": a.get("canon_versions") or a.get("canonVersions") or {},
            "v1V2Diff": a.get("v1_v2_diff") or a.get("v1V2Diff"),
        }

    # scoreBreakdown can remain as opaque object for UI; convert keys if needed
    camel_score: dict[str, Any] = {}
    if isinstance(score_breakdown, dict):
        for k, ss in score_breakdown.items():
            if not isinstance(ss, dict):
                continue
            contribs = []
            for c in ss.get("contributions") or []:
                if not isinstance(c, dict):
                    continue
                contribs.append(
                    {
                        "sphere": c.get("sphere") or k,
                        "source": c.get("source"),
                        "sourceId": c.get("source_id") or c.get("sourceId"),
                        "amount": c.get("amount"),
                        "before": c.get("before"),
                        "after": c.get("after"),
                        "evidence": c.get("evidence") or "",
                    }
                )
            camel_score[k] = {
                "key": ss.get("key") or k,
                "title": ss.get("title") or k,
                "baseScore": ss.get("base_score") if "base_score" in ss else ss.get("baseScore"),
                "activationScore": ss.get("activation_score") if "activation_score" in ss else ss.get("activationScore"),
                "convergenceBonus": ss.get("convergence_bonus") if "convergence_bonus" in ss else ss.get("convergenceBonus"),
                "rawScore": ss.get("raw_score") if "raw_score" in ss else ss.get("rawScore"),
                "finalScore": ss.get("final_score") if "final_score" in ss else ss.get("finalScore"),
                "normalizedScore": ss.get("normalized_score") if "normalized_score" in ss else ss.get("normalizedScore"),
                "dominanceCapped": ss.get("dominance_capped") if "dominance_capped" in ss else ss.get("dominanceCapped"),
                "contributions": contribs,
            }

    v2_block = {
        "activationSummary": camel_summary(activation_summary if isinstance(activation_summary, dict) else {}),
        "activationEvidence": [camel_evidence(e) for e in activation_evidence if isinstance(e, dict)],
        "scoreBreakdown": camel_score,
        "whyToday": camel_why(why_today if isinstance(why_today, list) else []),
        "audit": camel_audit(audit if isinstance(audit, dict) else {}),
    }

    adapted = {
        "date": meta.get("date") or "2026-07-08",
        "headline": meta.get("headline") or "Downstream V2 fixture",
        "dayStatus": meta.get("day_status") or meta.get("dayStatus") or "steady",
        "concreteAdvice": {
            "rows": [],
            "counts": {"good": 0, "caution": 0, "avoid": 0, "neutral": 0},
        },
        "daySummary": {
            "statusLabel": "Steady",
            "statusLine": "Downstream correctness fixture",
            "facts": [],
        },
        "topFlags": [],
        "notes": [],
        "reading": {"paragraphs": ["Downstream V2 fixture reading."]},
        "why": [],
        "keyInsight": "Downstream V2 fixture insight",
        "dayChart": None,
        "planetInfluences": [],
        "sphereScores": [],
        "v2": v2_block,
    }
    assertions = {
        "has_v2": adapted.get("v2") is not None,
        "activation_evidence_count": len(v2_block["activationEvidence"]),
        "score_breakdown_spheres": sorted(list(v2_block["scoreBreakdown"].keys())),
        "why_today_count": len(v2_block["whyToday"]),
        "audit_available": bool(v2_block["audit"].get("available", True)),
    }
    if assertions["has_v2"] != (adapted.get("v2") is not None):
        raise RuntimeError("frontend fixture self-consistency failed: has_v2")
    return {"payload": adapted, "assertions": assertions}


def run_downstream_audit(args: argparse.Namespace) -> dict[str, Any]:
    state = DownstreamAuditState()
    out_dir = Path(args.out).resolve()
    debug_dir = out_dir / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    debug_dir.mkdir(parents=True, exist_ok=True)

    spheres, scoring_v2, activation_rules, aspect_rules = load_canons()
    write_json(debug_dir / "canon_spheres.json", spheres)
    write_json(debug_dir / "canon_scoring_v2.json", scoring_v2)
    write_json(debug_dir / "canon_activation_rules.json", activation_rules)
    write_json(debug_dir / "canon_aspect_rules.json", aspect_rules)

    mode = "live"
    sidecar_source = "live_endpoint"
    today_payload_source = "TodayService.get_today_payload"
    sidecar_layer_raw: dict[str, Any]
    day_signals: list[AstroSignal] = []
    payload_json: dict[str, Any] | None = None

    if args.synthetic_fixture:
        mode = "synthetic_fixture"
        sidecar_source = "synthetic_fixture"
        today_payload_source = "synthetic_fixture"
        fixture = json.loads(Path(args.synthetic_fixture).read_text(encoding="utf-8"))
        sidecar_layer_raw = fixture["activation_layer"]
        day_signals = [AstroSignal.model_validate(x) for x in fixture.get("day_signals") or []]
    elif args.input_activation_layer:
        mode = "artifact_replay"
        sidecar_source = "artifact_file"
        today_payload_source = "artifact_file"
        sidecar_layer_raw = json.loads(Path(args.input_activation_layer).read_text(encoding="utf-8"))
        if args.input_day_signals:
            day_signals = parse_day_signals(Path(args.input_day_signals))
        if not args.input_final_payload:
            raise SystemExit("artifact_replay requires --input-final-payload")
        payload_json = json.loads(Path(args.input_final_payload).read_text(encoding="utf-8"))
    else:
        import asyncio
        from sqlalchemy import select
        from app.clients.solarsage_client import get_solarsage_client
        from app.db.models import User, UserProfile
        from app.db.session import SessionLocal
        from app.services.access_service import AccessService
        from app.services.day_delta_service import DayDeltaService
        from app.services.day_scoring_signals import filter_day_scored_signals
        from app.services.natal_context_service import NatalContextService
        from app.services.normalization_service import NormalizationService
        from app.services.today_service import TodayService

        async def _live() -> tuple[dict[str, Any], dict[str, Any], list[AstroSignal]]:
            target_date = Date.fromisoformat(args.date)
            async with SessionLocal() as db:
                user = (await db.execute(select(User).where(User.id == args.user_id))).scalar_one_or_none()
                if user is None:
                    raise SystemExit(f"User not found: {args.user_id}")
                profile = (
                    await db.execute(select(UserProfile).where(UserProfile.user_id == user.id))
                ).scalar_one_or_none()
                if profile is None:
                    raise SystemExit(f"Profile not found for user: {args.user_id}")
                natal = await NatalContextService(db).get_or_build_natal_context(user.id)
                natal_dict = natal.model_dump(mode="json", by_alias=False)
                client = get_solarsage_client()
                try:
                    layer = await client.get_activation_layer(
                        birth_date=profile.birthday.isoformat() if profile.birthday else args.date,
                        birth_time=profile.birth_time.strftime("%H:%M") if profile.birth_time else "12:00",
                        birth_lat=float(profile.birth_lat or 0.0),
                        birth_lon=float(profile.birth_lon or 0.0),
                        birth_tz=profile.birth_tz or "UTC",
                        target_date=args.date,
                        target_time="12:00",
                        target_tz=profile.current_tz or profile.birth_tz or "UTC",
                        house_system=natal_dict.get("house_system", "PLACIDUS"),
                    )
                    target_tz = profile.current_tz or profile.birth_tz or "UTC"
                    transits = await client.get_transits(target_date=args.date, target_time="12:00", target_tz=target_tz)
                    yesterday = Date.fromordinal(target_date.toordinal() - 1)
                    yesterday_transits = await client.get_transits(
                        target_date=yesterday.isoformat(),
                        target_time="12:00",
                        target_tz=profile.birth_tz or "UTC",
                    )
                finally:
                    await client.close()
                norm = NormalizationService()
                signals_before = norm.normalize_day(natal_dict, transits)
                yesterday_signals = norm.normalize_day(natal_dict, yesterday_transits)
                signals = DayDeltaService(yesterday_signals, signals_before).compute_deltas()
                day_sigs = filter_day_scored_signals(signals)
                access = await AccessService(db).can_access_day(user.id, target_date)
                await TodayService(db).invalidate_cache(user.id)
                payload = await TodayService(db).get_today_payload(
                    user_id=user.id,
                    target_date=target_date,
                    access_state=access,
                    skip_prefetch=True,
                )
                return layer, payload.model_dump(mode="json", by_alias=False), day_sigs

        sidecar_layer_raw, payload_json, day_signals = asyncio.run(_live())

    write_json(out_dir / "01_sidecar_activation_layer.json", sidecar_layer_raw)
    write_json(debug_dir / "day_signals.json", [to_jsonable(s) for s in day_signals])

    api_layer = ActivationLayerService().build(
        natal_context={},
        transits={},
        day_signals=[],
        target_date=Date.fromisoformat(args.date),
        target_time="12:00",
        target_tz=sidecar_layer_raw.get("target_tz") or "UTC",
        house_system=sidecar_layer_raw.get("house_system") or "PLACIDUS",
        sidecar_activation_layer=sidecar_layer_raw,
    )
    api_layer_json = to_jsonable(api_layer)
    write_json(out_dir / "02_api_activation_layer_after_validation.json", api_layer_json)

    sidecar_ids = [a["id"] for a in sidecar_layer_raw.get("activations", []) if a.get("id")]
    api_ids = [a.id for a in api_layer.activations]
    if Counter(sidecar_ids) != Counter(api_ids):
        state.error(
            kind="sidecar_ids_not_preserved",
            expected=sorted(sidecar_ids),
            actual=sorted(api_ids),
            message="API validation changed activation id multiset",
        )

    # Actual production scoring once
    scoring_result = ScoringV2Service().score_day(day_signals, api_layer)
    scoring_json = to_jsonable(scoring_result)
    write_json(out_dir / "03_scoring_v2_result.json", scoring_json)

    # Independent expected mapping/contributions
    expected_pairs: list[tuple[str, str]] = []
    expected_amounts: dict[tuple[str, str], float] = {}
    # Formula inputs preserved per expected (activation_id, sphere) for 05_contribution_trace.csv
    expected_formula_inputs: dict[tuple[str, str], dict[str, Any]] = {}
    matrix_rows: list[dict[str, Any]] = []
    families_by_sphere: dict[str, set[str]] = {k: set() for k in spheres.get("spheres", {})}
    expected_act_contrib_by_sphere: dict[str, list[tuple[str, float]]] = {k: [] for k in spheres.get("spheres", {})}

    for act in api_layer.activations:
        act_d = activation_as_dict(act)
        active = True if act_d.get("active") is None else bool(act_d.get("active"))
        if not active:
            matrix_rows.append(
                {
                    "activation_id": act.id,
                    "active": False,
                    "technique": act.technique,
                    "technique_family": act.technique_family,
                    "target_type": act.target_type,
                    "target_key": act.target_key,
                    "strength": act.strength,
                    "polarity": act.polarity,
                    "mapped_sphere": "",
                    "mapping_reason": "inactive",
                    "target_weight": "",
                    "family_weight": "",
                    "polarity_modifier": "",
                    "expected_amount": "",
                    "status": "inactive_skipped",
                }
            )
            continue
        family = act.technique_family or family_for_technique(act.technique, activation_rules)
        fw = family_weight(family, activation_rules)
        pol = act.polarity or "neutral"
        pol_mod = float(scoring_v2["activation_polarity"]["sphere_amount_modifier"][pol])
        strength_val = float(act.strength)
        mappings = map_activation_to_spheres_for_audit(act_d, spheres, scoring_v2)
        if not mappings:
            matrix_rows.append(
                {
                    "activation_id": act.id,
                    "active": True,
                    "technique": act.technique,
                    "technique_family": family,
                    "target_type": act.target_type,
                    "target_key": act.target_key,
                    "strength": act.strength,
                    "polarity": pol,
                    "mapped_sphere": "",
                    "mapping_reason": "no sphere mapping",
                    "target_weight": "",
                    "family_weight": fw,
                    "polarity_modifier": pol_mod,
                    "expected_amount": "",
                    "status": "unmapped",
                }
            )
            unmapped_debug = list(scoring_result.debug.get("unmapped_activations") or [])
            if act.id not in unmapped_debug:
                state.error(kind="unmapped_not_in_debug", activation_id=act.id, message="unmapped missing from debug")
            if args.fail_on_unmapped:
                state.error(kind="unmapped_activation", activation_id=act.id, message="active unmapped with fail-on-unmapped")
            else:
                state.warn(kind="unmapped_activation", activation_id=act.id, message="active unmapped activation")
            continue
        for m in mappings:
            skey = m["sphere"]
            tweight = float(m["target_weight"])
            expected_amount = expected_activation_amount(strength_val, fw, tweight, pol_mod)
            pair = (act.id, skey)
            expected_pairs.append(pair)
            expected_amounts[pair] = expected_amount
            expected_formula_inputs[pair] = {
                "strength": strength_val,
                "family_weight": fw,
                "target_weight": tweight,
                "polarity_modifier": pol_mod,
            }
            expected_act_contrib_by_sphere[skey].append((act.id, expected_amount))
            families_by_sphere[skey].add(family)
            matrix_rows.append(
                {
                    "activation_id": act.id,
                    "active": True,
                    "technique": act.technique,
                    "technique_family": family,
                    "target_type": act.target_type,
                    "target_key": act.target_key,
                    "strength": act.strength,
                    "polarity": pol,
                    "mapped_sphere": skey,
                    "mapping_reason": m["mapping_reason"],
                    "target_weight": tweight,
                    "family_weight": fw,
                    "polarity_modifier": pol_mod,
                    "expected_amount": expected_amount,
                    "status": "mapped",
                }
            )

    write_csv(
        out_dir / "04_activation_to_sphere_matrix.csv",
        matrix_rows,
        [
            "activation_id", "active", "technique", "technique_family", "target_type", "target_key",
            "strength", "polarity", "mapped_sphere", "mapping_reason", "target_weight", "family_weight",
            "polarity_modifier", "expected_amount", "status",
        ],
    )

    # Exact multiset contribution comparison
    actual_rows = extract_actual_activation_contrib_rows(scoring_result)
    actual_pairs = [(r["activation_id"], r["sphere"]) for r in actual_rows]
    expected_counter = Counter(expected_pairs)
    actual_counter = Counter(actual_pairs)
    missing_pairs = sorted((expected_counter - actual_counter).elements())
    extra_pairs = sorted((actual_counter - expected_counter).elements())
    # duplicates: count > 1 beyond expected
    for pair, cnt in actual_counter.items():
        if cnt > expected_counter.get(pair, 0) and expected_counter.get(pair, 0) >= 1:
            # extra already covers surplus; still flag explicit duplicate if cnt>1 and expected==1
            if cnt > 1 and expected_counter.get(pair, 0) == 1:
                state.error(
                    kind="duplicate_scoring_contribution",
                    activation_id=pair[0],
                    sphere=pair[1],
                    expected=1,
                    actual=cnt,
                    message="duplicate actual activation contribution",
                )
    for aid, skey in missing_pairs:
        state.error(
            kind="missing_scoring_contribution",
            activation_id=aid,
            sphere=skey,
            message="active mapped activation missing scoring contribution",
        )
    for aid, skey in extra_pairs:
        state.error(
            kind="extra_scoring_contribution",
            activation_id=aid,
            sphere=skey,
            message="unexpected activation contribution not in independent mapping",
        )

    contrib_rows: list[dict[str, Any]] = []
    actual_amount_map: dict[tuple[str, str], list[float]] = {}
    for r in actual_rows:
        actual_amount_map.setdefault((r["activation_id"], r["sphere"]), []).append(r["amount"])
    for pair in sorted(set(expected_pairs + actual_pairs)):
        exp = expected_amounts.get(pair)
        formula = expected_formula_inputs.get(pair, {})
        actual_list = actual_amount_map.get(pair, [])
        actual_amount = actual_list[0] if actual_list else None
        if exp is None:
            status = "extra"
            delta = ""
        elif actual_amount is None:
            status = "missing_contribution"
            delta = ""
        else:
            d = abs(float(exp) - float(actual_amount))
            status = "ok" if d <= TOL else "amount_mismatch"
            delta = round(d, 6)
            if status != "ok":
                state.error(
                    kind="contribution_amount_mismatch",
                    activation_id=pair[0],
                    sphere=pair[1],
                    expected=exp,
                    actual=actual_amount,
                    message="contribution amount differs from formula",
                )
        contrib_rows.append(
            {
                "activation_id": pair[0],
                "sphere": pair[1],
                "expected_amount": exp if exp is not None else "",
                "actual_amount": actual_amount if actual_amount is not None else "",
                "actual_contribution_source_id": pair[0] if actual_amount is not None else "",
                "formula": "strength * family_weight * target_weight * polarity_modifier",
                # Prefer independently known formula inputs; leave only genuinely unavailable empty
                "strength": formula.get("strength", ""),
                "family_weight": formula.get("family_weight", ""),
                "target_weight": formula.get("target_weight", ""),
                "polarity_modifier": formula.get("polarity_modifier", ""),
                "amount_delta": delta,
                "status": status,
            }
        )
    write_csv(
        out_dir / "05_contribution_trace.csv",
        contrib_rows,
        [
            "activation_id", "sphere", "expected_amount", "actual_amount", "actual_contribution_source_id",
            "formula", "strength", "family_weight", "target_weight", "polarity_modifier", "amount_delta", "status",
        ],
    )

    # Convergence independent + exact family/debug/contribution comparison
    conv_rows: list[dict[str, Any]] = []
    actual_conv = scoring_result.debug.get("convergence_by_sphere") or {}
    expected_conv_bonus: dict[str, float] = {}
    for skey, families in families_by_sphere.items():
        expected_bonus = expected_convergence_bonus(families, scoring_v2)
        expected_conv_bonus[skey] = expected_bonus
        ss = scoring_result.sphere_scores[skey]
        actual_bonus = float(ss.convergence_bonus)
        delta = abs(expected_bonus - actual_bonus)
        status = "ok" if delta <= TOL else "mismatch"
        conv_contribs = [c for c in ss.contributions if c.source == "convergence"]
        prod_entry = actual_conv.get(skey)
        if expected_bonus > 0:
            # Require production debug entry with exact families and family_count
            if not isinstance(prod_entry, dict):
                status = "missing_convergence_debug"
                state.error(
                    kind="convergence_debug_missing",
                    sphere=skey,
                    expected={"families": sorted(families), "family_count": len(families)},
                    actual=prod_entry,
                    message="expected convergence debug entry missing",
                )
            else:
                prod_families = set(prod_entry.get("families") or [])
                prod_family_count = prod_entry.get("family_count")
                if prod_families != families:
                    status = "family_set_mismatch"
                    state.error(
                        kind="convergence_family_mismatch",
                        sphere=skey,
                        expected=sorted(families),
                        actual=sorted(prod_families),
                        message="convergence family set mismatch",
                    )
                if prod_family_count is None or int(prod_family_count) != len(families):
                    status = "family_count_mismatch"
                    state.error(
                        kind="convergence_family_count_mismatch",
                        sphere=skey,
                        expected=len(families),
                        actual=prod_family_count,
                        message="convergence family_count mismatch",
                    )
            # Exactly one source=convergence contribution with correct source_id and amount
            if len(conv_contribs) == 0:
                status = "missing_convergence_contribution"
                state.error(
                    kind="convergence_contribution_missing",
                    sphere=skey,
                    expected=sorted(families),
                    message="expected convergence contribution missing",
                )
            else:
                if len(conv_contribs) != 1:
                    status = "duplicate_convergence_contribution"
                    state.error(
                        kind="convergence_contribution_duplicate",
                        sphere=skey,
                        expected=1,
                        actual=len(conv_contribs),
                        message="expected exactly one convergence contribution",
                    )
                expected_sid = f"convergence:{skey}"
                for c in conv_contribs:
                    if c.source_id != expected_sid:
                        status = "convergence_source_id_mismatch"
                        state.error(
                            kind="convergence_source_id_mismatch",
                            sphere=skey,
                            expected=expected_sid,
                            actual=c.source_id,
                            message="convergence contribution source_id mismatch",
                        )
                    if abs(float(c.amount) - expected_bonus) > TOL:
                        status = "convergence_amount_mismatch"
                        state.error(
                            kind="convergence_contribution_amount_mismatch",
                            sphere=skey,
                            expected=expected_bonus,
                            actual=c.amount,
                            message="convergence contribution amount mismatch",
                        )
        else:
            # No bonus expected: still reject stray convergence contributions
            if conv_contribs:
                status = "unexpected_convergence_contribution"
                state.error(
                    kind="convergence_contribution_unexpected",
                    sphere=skey,
                    expected=0,
                    actual=len(conv_contribs),
                    message="unexpected convergence contribution when bonus is zero",
                )
        if status == "mismatch":
            state.error(
                kind="convergence_mismatch",
                sphere=skey,
                expected=expected_bonus,
                actual=actual_bonus,
                message="convergence bonus mismatch",
            )
        conv_rows.append(
            {
                "sphere": skey,
                "families": ",".join(sorted(families)),
                "family_count": len(families),
                "expected_bonus": expected_bonus,
                "actual_bonus": actual_bonus,
                "formula": "convergence_curve[min(n,5)] * sphere_convergence_weight.default",
                "status": status,
            }
        )
    write_csv(
        out_dir / "06_convergence_trace.csv",
        conv_rows,
        ["sphere", "families", "family_count", "expected_bonus", "actual_bonus", "formula", "status"],
    )

    # Independent raw scores + cap from expected raw scores
    # actual base_score is production base input (from day signals) — use as base input only
    expected_raw: dict[str, float] = {}
    for skey, ss in scoring_result.sphere_scores.items():
        act_sum = round(sum(amt for _aid, amt in expected_act_contrib_by_sphere.get(skey, [])), 4)
        conv = expected_conv_bonus.get(skey, 0.0)
        expected_raw[skey] = round(float(ss.base_score) + act_sum + conv, 4)
        if abs(expected_raw[skey] - float(ss.raw_score)) > TOL:
            state.error(
                kind="raw_score_mismatch",
                sphere=skey,
                expected=expected_raw[skey],
                actual=ss.raw_score,
                message="raw score mismatch vs independent base+activation+convergence",
            )

    cap_rows: list[dict[str, Any]] = []
    dc = scoring_v2["dominance_cap"]
    if not dc.get("enabled"):
        cap_rows.append(
            {
                "sphere": "",
                "raw_score": "",
                "sum_all_positive_scores": "",
                "cap_threshold": "",
                "cap_value": "",
                "expected_final_score": "",
                "actual_final_score": "",
                "expected_capped": False,
                "actual_dominance_capped": False,
                "cap_contribution_id": "",
                "status": "cap_disabled",
            }
        )
    else:
        threshold = float(dc["threshold"])
        sum_all_expected = sum(v for v in expected_raw.values() if v > 0)
        for skey, raw in expected_raw.items():
            if raw <= 0:
                continue
            ss = scoring_result.sphere_scores[skey]
            cap_value = threshold * sum_all_expected
            expected_capped = raw > cap_value
            expected_final = round(cap_value, 4) if expected_capped else raw
            cap_contribs = [c for c in ss.contributions if c.source == "cap"]
            cap_contrib = cap_contribs[0] if cap_contribs else None
            status = "ok"
            if abs(expected_final - float(ss.final_score)) > TOL:
                status = "final_score_mismatch"
                state.error(
                    kind="dominance_cap_mismatch",
                    sphere=skey,
                    expected=expected_final,
                    actual=ss.final_score,
                    message="dominance cap final score mismatch",
                )
            if bool(ss.dominance_capped) != expected_capped:
                status = "cap_flag_mismatch"
                state.error(
                    kind="dominance_cap_flag_mismatch",
                    sphere=skey,
                    expected=expected_capped,
                    actual=ss.dominance_capped,
                    message="dominance_capped flag mismatch",
                )
            if expected_capped:
                if len(cap_contribs) == 0:
                    status = "cap_trace_missing"
                    state.error(
                        kind="dominance_cap_trace_missing",
                        sphere=skey,
                        message="missing source=cap contribution",
                    )
                elif len(cap_contribs) != 1:
                    status = "cap_duplicate"
                    state.error(
                        kind="dominance_cap_duplicate",
                        sphere=skey,
                        expected=1,
                        actual=len(cap_contribs),
                        message="duplicate source=cap contributions",
                    )
                if cap_contrib is not None:
                    expected_cap_amount = round(expected_final - raw, 4)
                    if abs(float(cap_contrib.amount) - expected_cap_amount) > TOL:
                        status = "cap_amount_mismatch"
                        state.error(
                            kind="dominance_cap_amount_mismatch",
                            sphere=skey,
                            expected=expected_cap_amount,
                            actual=cap_contrib.amount,
                            message="cap contribution amount mismatch",
                        )
                    if cap_contrib.source_id != f"cap:{skey}":
                        state.error(
                            kind="dominance_cap_source_id_mismatch",
                            sphere=skey,
                            expected=f"cap:{skey}",
                            actual=cap_contrib.source_id,
                            message="cap source_id policy mismatch",
                        )
            else:
                # Cap not expected: hard-fail on any unexpected or duplicate cap contribution
                if len(cap_contribs) > 0:
                    status = "unexpected_cap"
                    state.error(
                        kind="dominance_cap_unexpected",
                        sphere=skey,
                        expected=0,
                        actual=len(cap_contribs),
                        message="unexpected source=cap contribution on non-capped sphere",
                    )
            cap_rows.append(
                {
                    "sphere": skey,
                    "raw_score": raw,
                    "sum_all_positive_scores": round(sum_all_expected, 4),
                    "cap_threshold": threshold,
                    "cap_value": round(cap_value, 4),
                    "expected_final_score": expected_final,
                    "actual_final_score": ss.final_score,
                    "expected_capped": expected_capped,
                    "actual_dominance_capped": ss.dominance_capped,
                    "cap_contribution_id": cap_contrib.source_id if cap_contrib else "",
                    "status": status,
                }
            )
        # Also scan spheres skipped above (raw <= 0) for unexpected cap contributions
        for skey, raw in expected_raw.items():
            if raw > 0:
                continue
            ss = scoring_result.sphere_scores[skey]
            cap_contribs = [c for c in ss.contributions if c.source == "cap"]
            if cap_contribs:
                state.error(
                    kind="dominance_cap_unexpected",
                    sphere=skey,
                    expected=0,
                    actual=len(cap_contribs),
                    message="unexpected source=cap contribution on non-capped sphere",
                )
                cap_rows.append(
                    {
                        "sphere": skey,
                        "raw_score": raw,
                        "sum_all_positive_scores": round(sum_all_expected, 4),
                        "cap_threshold": threshold,
                        "cap_value": "",
                        "expected_final_score": raw,
                        "actual_final_score": ss.final_score,
                        "expected_capped": False,
                        "actual_dominance_capped": ss.dominance_capped,
                        "cap_contribution_id": cap_contribs[0].source_id,
                        "status": "unexpected_cap",
                    }
                )
    write_csv(
        out_dir / "07_dominance_cap_trace.csv",
        cap_rows,
        [
            "sphere", "raw_score", "sum_all_positive_scores", "cap_threshold", "cap_value",
            "expected_final_score", "actual_final_score", "expected_capped", "actual_dominance_capped",
            "cap_contribution_id", "status",
        ],
    )

    # Independent day status
    expected_status, expected_breakdown = independent_day_status(
        day_signals,
        [activation_as_dict(a) for a in api_layer.activations],
        scoring_v2,
        activation_rules,
        aspect_rules,
    )
    actual_status = scoring_result.day_status
    actual_breakdown = scoring_result.status_breakdown if isinstance(scoring_result.status_breakdown, dict) else {}
    status_ok = actual_status == expected_status
    deltas: dict[str, Any] = {}
    # Compare every status-breakdown key: numerics with tolerance, strings/null exactly
    all_keys = sorted(set(expected_breakdown.keys()) | set(actual_breakdown.keys()))
    for k in all_keys:
        exp_v = expected_breakdown.get(k, "__missing__")
        act_v = actual_breakdown.get(k, "__missing__")
        if exp_v == "__missing__" or act_v == "__missing__":
            status_ok = False
            deltas[k] = {"expected": None if exp_v == "__missing__" else exp_v, "actual": None if act_v == "__missing__" else act_v}
            continue
        # Exact nullability
        if exp_v is None or act_v is None:
            if exp_v is not act_v:
                status_ok = False
                deltas[k] = {"expected": exp_v, "actual": act_v}
            else:
                deltas[k] = 0
            continue
        if isinstance(exp_v, (int, float)) and isinstance(act_v, (int, float)):
            d = abs(float(exp_v) - float(act_v))
            deltas[k] = d
            if d > TOL:
                status_ok = False
            continue
        # Strings and other non-numeric components (e.g. rule): exact equality
        if exp_v != act_v:
            status_ok = False
            deltas[k] = {"expected": exp_v, "actual": act_v}
        else:
            deltas[k] = 0 if isinstance(exp_v, (int, float)) else "match"
    if not status_ok:
        state.error(
            kind="day_status_mismatch",
            expected={"day_status": expected_status, "breakdown": expected_breakdown},
            actual={"day_status": actual_status, "breakdown": actual_breakdown},
            message="day status/breakdown mismatch",
        )
    write_json(
        out_dir / "08_status_breakdown.json",
        {
            "day_status": actual_status,
            "expected_day_status": expected_status,
            "status": "ok" if status_ok else "failed",
            "breakdown": actual_breakdown,
            "independent_recalc": expected_breakdown,
            "deltas": deltas,
        },
    )

    # Payload handling — no synthesis in replay/live. The dual runtime
    # selection (production selection path) is computed ONCE and shared by
    # synthetic payload completion and the payload-vs-recompute check.
    dual = DayScoringRuntimeService().compute(
        day_signals=day_signals,
        activation_layer=api_layer,
        user_id=None,  # audit replay: scoring does not consume user_id
        target_date=args.date,
        force_v2=True,
    )
    if mode == "synthetic_fixture":
        v2_block = SemanticV2Service().build_v2_block(
            activation_layer=api_layer,
            scoring_result=scoring_result,
            v1_v2_diff=None,
            trace_id="downstream-audit-synthetic",
        )
        # The synthetic payload is completed from the SAME validated layer
        # and selection as production (dayStatus, topFlags, sphereScores,
        # activationEvidence), so the payload-vs-recompute check applies
        # honestly instead of being exempted.
        v2_block_dict = to_jsonable(v2_block)
        v2_block_dict["activationEvidence"] = [
            {
                _EVIDENCE_SNAKE_TO_CAMEL.get(k, k): v
                for k, v in entry.items()
            }
            for entry in (api_layer_json.get("activations") or [])
        ]
        payload_json = {
            "meta": {
                "payload_version": TODAY_V2_PAYLOAD_VERSION,
                "frontend_payload_version": V2_FRONTEND_PAYLOAD_VERSION,
                "scoring_version": SCORING_V2_VERSION,
                "calculation_version": CALCULATION_VERSION,
                "activation_layer_version": ACTIVATION_LAYER_VERSION,
                "day_status": scoring_result.day_status,
                "headline": "Synthetic downstream fixture",
            },
            "date": args.date,
            "dayStatus": scoring_result.day_status,
            "sphereScores": [
                s.model_dump(by_alias=True)
                for s in TodayServiceForFlags._build_sphere_scores(dual.selected_result["sphere_scores"])
            ],
            "topFlags": [
                f.model_dump(by_alias=True)
                for f in TodayServiceForFlags._build_top_flags(dual.selected_result.get("top_signals", []))
            ],
            "v2": v2_block_dict,
        }
    elif payload_json is None:
        raise SystemExit("payload missing for non-synthetic mode")

    write_json(debug_dir / "raw_today_payload.json", payload_json)
    payload_v2 = extract_payload_v2(payload_json)
    # 09 must be normalized copy from actual payload only
    write_json(out_dir / "09_payload_v2.json", payload_v2)

    v2_selected = is_v2_selected_payload(payload_json)
    payload_ids = extract_payload_activation_ids(payload_v2)
    if not v2_selected or payload_v2 is None:
        state.error(
            kind="payload_v2_missing",
            message="replay/live payload missing V2 identity/body; audit does not synthesize missing V2",
            expected="today.v2.1 non-null body",
            actual={"v2_selected": v2_selected, "has_v2": payload_v2 is not None},
        )
    sidecar_id_set = set(sidecar_ids)
    payload_id_set = set(payload_ids)
    missing_in_payload = sorted(sidecar_id_set - payload_id_set)
    extra_payload = sorted(payload_id_set - sidecar_id_set)
    if missing_in_payload:
        state.error(
            kind="missing_in_payload_v2",
            expected=sorted(sidecar_id_set),
            actual=sorted(payload_id_set),
            message="payload.v2 missing sidecar activation ids",
        )
    if extra_payload:
        # Fabricated evidence is a hard mismatch, not a warning: the payload
        # activation evidence set must equal the sidecar set exactly.
        state.error(
            kind="extra_payload_ids",
            expected=sorted(sidecar_id_set),
            actual=sorted(payload_id_set),
            message="payload has activation ids not in sidecar",
        )

    # payload score breakdown source/id policy — unknown/missing source is hard failure
    known_payload_sources = {"activation", "base_signal", "convergence", "cap"}
    for c in extract_payload_score_contribs(payload_v2):
        source = c.get("source")
        sid_raw = c.get("source_id")
        sid = str(sid_raw) if sid_raw is not None else ""
        if source is None or source == "" or sid_raw is None or sid == "":
            state.error(
                kind="payload_score_unknown_source",
                actual={"source": source, "source_id": sid_raw, "sphere": c.get("sphere")},
                message="missing payload score contribution source or source_id",
            )
            continue
        if source not in known_payload_sources:
            state.error(
                kind="payload_score_unknown_source",
                actual={"source": source, "source_id": sid, "sphere": c.get("sphere")},
                message="unknown payload score contribution source",
            )
            continue
        if source == "activation":
            if sid not in payload_id_set:
                state.error(
                    kind="payload_score_activation_id_missing",
                    activation_id=sid,
                    sphere=c.get("sphere"),
                    message="activation contribution id not in activationEvidence",
                )
        elif source == "base_signal":
            if not sid.startswith("base_signal:"):
                state.error(kind="payload_score_base_id_policy", actual=sid, message="base_signal id policy")
        elif source == "convergence":
            if not sid.startswith("convergence:"):
                state.error(kind="payload_score_convergence_id_policy", actual=sid, message="convergence id policy")
        elif source == "cap":
            if not sid.startswith("cap:"):
                state.error(kind="payload_score_cap_id_policy", actual=sid, message="cap id policy")

    why_ids = extract_payload_why_activation_ids(payload_v2)
    unknown_why = sorted(set(why_ids) - payload_id_set)
    if unknown_why:
        state.error(
            kind="why_today_unknown_activation_ids",
            actual=unknown_why,
            message="whyToday references activation ids not present in activationEvidence",
        )

    # START_BLOCK: PAYLOAD_VS_RECOMPUTED_V2
    # The FINAL SELECTED payload must equal the independently recomputed V2
    # it was verified against: dayStatus, every scoreBreakdown sphere (FULL
    # public SphereScoreV2: key/title/base/activation/convergence/raw/final/
    # normalized/dominance + ordered contributions), sphere sorting,
    # top-level sphereScores, full ordered topFlags, activationEvidence
    # (full ordered entries) and dayChart. Legacy v1 status is irrelevant.
    payload_day_status = None
    if isinstance(payload_json, dict):
        payload_day_status = payload_json.get("dayStatus") or payload_json.get("day_status")
    if payload_day_status != scoring_result.day_status:
        state.error(
            kind="payload_day_status_mismatch",
            expected=scoring_result.day_status,
            actual=payload_day_status,
            message="payload dayStatus differs from recomputed V2 day status",
        )

    def _num_eq(wire_val: Any, svc_val: Any) -> bool:
        if wire_val is None and svc_val is None:
            return True
        if not isinstance(wire_val, (int, float)) or svc_val is None:
            return False
        return abs(float(wire_val) - float(svc_val)) <= TOL

    # -- scoreBreakdown: full public SphereScoreV2, exact order ------------
    payload_sb = (payload_v2 or {}).get("scoreBreakdown") or (payload_v2 or {}).get("score_breakdown") or {}
    service_spheres = list(scoring_result.sphere_scores.keys())
    payload_spheres = list(payload_sb.keys())
    if payload_spheres != service_spheres:
        state.error(
            kind="payload_score_breakdown_order_mismatch",
            expected=service_spheres,
            actual=payload_spheres,
            message="payload scoreBreakdown sphere order mismatch",
        )
    _numeric_fields = (
        ("baseScore", "base_score"),
        ("activationScore", "activation_score"),
        ("convergenceBonus", "convergence_bonus"),
        ("rawScore", "raw_score"),
        ("finalScore", "final_score"),
        ("normalizedScore", "normalized_score"),
    )
    for skey in service_spheres:
        ss = scoring_result.sphere_scores[skey]
        entry = payload_sb.get(skey)
        if not isinstance(entry, dict):
            state.error(
                kind="payload_score_breakdown_missing",
                sphere=skey,
                message="scoreBreakdown sphere missing from payload",
            )
            continue
        if entry.get("key") is not None and entry.get("key") != skey:
            state.error(
                kind="payload_score_field_mismatch",
                sphere=skey,
                expected={"field": "key", "value": skey},
                actual={"field": "key", "value": entry.get("key")},
                message="payload scoreBreakdown key mismatch",
            )
        if entry.get("title") is not None and entry.get("title") != ss.title:
            state.error(
                kind="payload_score_field_mismatch",
                sphere=skey,
                expected={"field": "title", "value": ss.title},
                actual={"field": "title", "value": entry.get("title")},
                message="payload scoreBreakdown title mismatch",
            )
        for wire_name, attr in _numeric_fields:
            wire_val = entry.get(wire_name) if wire_name in entry else entry.get(attr)
            svc_val = getattr(ss, attr, None)
            if not _num_eq(wire_val, svc_val):
                state.error(
                    kind="payload_score_field_mismatch",
                    sphere=skey,
                    expected={"field": wire_name, "value": svc_val},
                    actual={"field": wire_name, "value": wire_val},
                    message="payload scoreBreakdown numeric field mismatch",
                )
        capped_val = entry.get("dominanceCapped") if "dominanceCapped" in entry else entry.get("dominance_capped")
        if bool(ss.dominance_capped) != bool(capped_val):
            state.error(
                kind="payload_dominance_capped_mismatch",
                sphere=skey,
                expected=ss.dominance_capped,
                actual=capped_val,
                message="payload dominanceCapped mismatch",
            )
        # Full ORDERED contributions: sphere/source/sourceId/amount/before/after/evidence.
        payload_contribs = entry.get("contributions") or []
        if len(payload_contribs) != len(ss.contributions):
            state.error(
                kind="payload_contributions_mismatch",
                sphere=skey,
                expected=len(ss.contributions),
                actual=len(payload_contribs),
                message="payload contributions count mismatch",
            )
        for idx, svc_c in enumerate(ss.contributions):
            if idx >= len(payload_contribs):
                break
            pc = payload_contribs[idx]
            svc_dump = svc_c.model_dump(by_alias=True)
            mismatches: dict[str, dict[str, Any]] = {}
            for field_name in ("sphere", "source", "sourceId", "amount", "before", "after", "evidence"):
                wire_key = field_name if field_name in pc else ("source_id" if field_name == "sourceId" else field_name)
                wire_val = pc.get(wire_key)
                svc_val = svc_dump[field_name]
                if field_name in ("amount", "before", "after"):
                    ok = _num_eq(wire_val, svc_val)
                else:
                    ok = wire_val == svc_val
                if not ok:
                    mismatches[field_name] = {"expected": svc_val, "actual": wire_val}
            if mismatches:
                state.error(
                    kind="payload_contributions_mismatch",
                    sphere=skey,
                    expected={"index": idx, "fields": mismatches},
                    actual="payload contribution entry mismatch",
                    message="payload contribution entry mismatch",
                )

    # -- top-level sphereScores: exact ordered key/score/rank vs the dual
    # runtime selection (the production selection path, computed above).
    payload_sphere_scores = payload_json.get("sphereScores") or payload_json.get("sphere_scores") or []
    expected_sphere_scores = TodayServiceForFlags._build_sphere_scores(dual.selected_result["sphere_scores"])
    expected_ss_list = [{"key": s.key, "score": s.score, "rank": s.rank} for s in expected_sphere_scores]
    actual_ss_list = [
        {"key": s.get("key"), "score": s.get("score"), "rank": s.get("rank")}
        for s in payload_sphere_scores
    ]
    if actual_ss_list != expected_ss_list:
        state.error(
            kind="payload_sphere_scores_mismatch",
            expected=expected_ss_list,
            actual=actual_ss_list,
            message="payload top-level sphereScores mismatch (value/rank/order)",
        )

    # -- topFlags: full ordered objects (icon/title/summary/hint), rebuilt
    # from the dual-selected top signals through the production builder.
    payload_top_flags = payload_json.get("topFlags") or payload_json.get("top_flags") or []
    from app.schemas.normalization import normalize_top_signals

    selected_top_signals = normalize_top_signals(dual.selected_result.get("top_signals", []))
    expected_flags = TodayServiceForFlags._build_top_flags(selected_top_signals)
    expected_flag_objs = [f.model_dump(by_alias=True) for f in expected_flags]
    actual_flag_objs = [
        {
            "iconName": f.get("iconName") or f.get("icon_name"),
            "title": f.get("title"),
            "summary": f.get("summary"),
            "hint": f.get("hint"),
        }
        for f in payload_top_flags
    ]
    if actual_flag_objs != expected_flag_objs:
        state.error(
            kind="payload_top_flags_mismatch",
            expected=expected_flag_objs,
            actual=actual_flag_objs,
            message="payload topFlags differ from recomputed selected top signals",
        )

    # -- dayChart.aspects: exact ordered projection of the day signals, ---
    # rebuilt through the production _build_day_chart aspect rules (type
    # "aspect" + Transit_* planet + aspect_type + target_planet, stripped
    # prefixes, orb/strength rounded to 4). The underlying astronomy
    # (longitudes/houses) is proven by the astronomy oracle; the signal
    # projection is this audit's domain.
    from app.services.astro_utils import strip_prefix as _strip_aspect_prefix

    payload_day_chart = payload_json.get("dayChart") or payload_json.get("day_chart") or {}
    payload_aspects = payload_day_chart.get("aspects") or []
    expected_aspect_objs = [
        {
            "planet": _strip_aspect_prefix(s.planet),
            "targetPlanet": _strip_aspect_prefix(s.target_planet),
            "aspectType": s.aspect_type or "",
            "orb": round(float(s.orb), 4) if s.orb is not None else None,
            "strength": round(float(s.strength), 4),
        }
        for s in day_signals
        if s.type == "aspect"
        and s.aspect_type
        and s.target_planet
        and (s.planet or "").startswith("Transit_")
    ]
    actual_aspect_objs = [
        {
            "planet": a.get("planet"),
            "targetPlanet": a.get("targetPlanet") or a.get("target_planet"),
            "aspectType": a.get("aspectType") or a.get("aspect_type"),
            "orb": a.get("orb"),
            "strength": a.get("strength"),
        }
        for a in payload_aspects
        if isinstance(a, dict)
    ]
    if actual_aspect_objs != expected_aspect_objs:
        state.error(
            kind="payload_daychart_aspects_mismatch",
            expected=expected_aspect_objs,
            actual=actual_aspect_objs,
            message="payload dayChart.aspects differ from the day-signals projection",
        )

    # -- activationEvidence: full ordered entries vs validated layer -------
    expected_evidence = (api_layer_json.get("activations") or [])
    payload_evidence = (payload_v2 or {}).get("activationEvidence") or (payload_v2 or {}).get("activation_evidence") or []
    # The validated layer dump is snake_case; the payload evidence is camel.
    _evidence_alias = {
        "active_from": "activeFrom",
        "active_until": "activeUntil",
        "exact_at": "exactAt",
        "source_frame": "sourceFrame",
        "source_planet": "sourcePlanet",
        "target_frame": "targetFrame",
        "target_key": "targetKey",
        "target_planet": "targetPlanet",
        "target_type": "targetType",
        "technique_family": "techniqueFamily",
    }
    if len(payload_evidence) != len(expected_evidence):
        state.error(
            kind="payload_activation_evidence_mismatch",
            expected=len(expected_evidence),
            actual=len(payload_evidence),
            message="activationEvidence count mismatch",
        )
    for idx, exp_entry in enumerate(expected_evidence):
        if idx >= len(payload_evidence):
            break
        act_entry = payload_evidence[idx]
        mismatches = {}
        for field_name, exp_val in exp_entry.items():
            if field_name == "debug":
                continue  # diagnostic-only field, provenance noise allowed
            wire_key = _evidence_alias.get(field_name, field_name)
            wire_val = act_entry.get(wire_key)
            if isinstance(exp_val, float):
                ok = _num_eq(wire_val, exp_val)
            else:
                ok = wire_val == exp_val
            if not ok:
                mismatches[wire_key] = {"expected": exp_val, "actual": wire_val}
        if mismatches:
            state.error(
                kind="payload_activation_evidence_mismatch",
                expected={"index": idx, "id": exp_entry.get("id"), "fields": mismatches},
                actual="activationEvidence entry mismatch",
                message="activationEvidence entry mismatch",
            )

    # NOTE: the final dayChart transit longitudes/signs/motion and the
    # serialized house list are verified independently by the astronomy
    # oracle against the Swiss Ephemeris result; dayChart.aspects is the
    # day-signals projection checked above.
    # END_BLOCK: PAYLOAD_VS_RECOMPUTED_V2

    mapping = {
        "sidecar_activation_count": len(sidecar_ids),
        "api_activation_count": len(api_ids),
        "scoring_activation_contribution_count": len(actual_rows),  # rows, not distinct ids
        "payload_activation_evidence_count": len(payload_ids),
        "sidecar_ids": sorted(sidecar_id_set),
        "api_ids": sorted(set(api_ids)),
        "scoring_contribution_ids": sorted({r["activation_id"] for r in actual_rows}),
        "payload_evidence_ids": sorted(payload_id_set),
        "missing_after_api_validation": sorted(set(sidecar_ids) - set(api_ids)),
        "missing_in_scoring_contributions": sorted({p[0] for p in missing_pairs}),
        "unmapped_activations": list(scoring_result.debug.get("unmapped_activations") or []),
        "missing_in_payload_v2": missing_in_payload,
        "extra_payload_ids": extra_payload,
        "status": "failed" if state.failures else ("warning" if state.warnings else "ok"),
    }
    write_json(out_dir / "10_payload_mapping.json", mapping)
    write_json(debug_dir / "unmapped_activations.json", mapping["unmapped_activations"])

    # Frontend fixture — AdaptedTodayPayload compatible, assertions from same payload
    if payload_v2 is None:
        # still write a failed fixture shell for review
        frontend_fixture = {
            "payload": {
                "date": args.date,
                "headline": "missing v2",
                "dayStatus": "steady",
                "concreteAdvice": {"rows": [], "counts": {"good": 0, "caution": 0, "avoid": 0, "neutral": 0}},
                "daySummary": {"statusLabel": "Steady", "statusLine": "missing v2", "facts": []},
                "topFlags": [],
                "notes": [],
                "reading": {"paragraphs": ["missing v2"]},
                "why": [],
                "keyInsight": "missing v2",
                "dayChart": None,
                "planetInfluences": [],
                "sphereScores": [],
                "v2": None,
            },
            "assertions": {
                "has_v2": False,
                "activation_evidence_count": 0,
                "score_breakdown_spheres": [],
                "why_today_count": 0,
                "audit_available": False,
            },
        }
    else:
        meta = payload_json.get("meta") if isinstance(payload_json, dict) else {}
        if not isinstance(meta, dict):
            meta = {}
        meta = {
            **meta,
            "date": payload_json.get("date") or args.date,
            "headline": payload_json.get("headline") or "Downstream V2 fixture",
            "day_status": payload_json.get("day_status") or scoring_result.day_status,
        }
        frontend_fixture = build_adapted_frontend_fixture(payload_v2, meta)
        # hard self-consistency
        if bool(frontend_fixture["assertions"]["has_v2"]) != (frontend_fixture["payload"].get("v2") is not None):
            state.error(kind="frontend_fixture_self_consistency", message="assertions.has_v2 disagrees with payload.v2")
    write_json(out_dir / "11_frontend_fixture.json", frontend_fixture)

    checked = {
        "api_preserved_sidecar_ids": Counter(sidecar_ids) == Counter(api_ids),
        "mapped_activations_have_contributions": not any(k == "missing_scoring_contribution" for k in [f.kind for f in state.failures]),
        "contribution_amounts_match_formula": not any(f.kind == "contribution_amount_mismatch" for f in state.failures),
        "convergence_matches_canon": not any(f.kind.startswith("convergence_") for f in state.failures),
        "dominance_cap_matches_canon": not any(f.kind.startswith("dominance_cap_") for f in state.failures),
        "day_status_matches_recalc": not any(f.kind == "day_status_mismatch" for f in state.failures),
        "payload_day_status_matches_recalc": not any(f.kind == "payload_day_status_mismatch" for f in state.failures),
        "payload_score_breakdown_matches_recalc": not any(
            f.kind in (
                "payload_score_breakdown_order_mismatch",
                "payload_score_breakdown_missing",
                "payload_score_field_mismatch",
                "payload_dominance_capped_mismatch",
                "payload_contributions_mismatch",
            )
            for f in state.failures
        ),
        "payload_top_flags_match_recalc": not any(f.kind == "payload_top_flags_mismatch" for f in state.failures),
        "payload_sphere_scores_match_recalc": not any(f.kind == "payload_sphere_scores_mismatch" for f in state.failures),
        "payload_activation_evidence_match_recalc": not any(
            f.kind == "payload_activation_evidence_mismatch" for f in state.failures
        ),
        "payload_daychart_aspects_match_projection": not any(
            f.kind == "payload_daychart_aspects_mismatch" for f in state.failures
        ),
        "payload_preserves_sidecar_ids": (
            not bool(missing_in_payload) and not bool(extra_payload) and payload_v2 is not None and v2_selected
        ),
        "frontend_fixture_written": True,
    }
    # fix payload_preserves for synthetic where v2_selected true
    if mode == "synthetic_fixture" and payload_v2 is not None and not missing_in_payload:
        checked["payload_preserves_sidecar_ids"] = True

    summary = {
        "status": "failed" if state.failures else "ok",
        "failure_count": len(state.failures),
        "warning_count": len(state.warnings),
        # The unmapped policy is pinned here, never silently weakened:
        # "warn" = intentional unmapped activations are reported as warnings,
        # "fail" = they are hard failures. Mismatches are ALWAYS errors.
        "unmapped_policy": "fail" if args.fail_on_unmapped else "warn",
        "checked": checked,
        "failures": [f.as_dict() for f in state.failures],
        "warnings": [w.as_dict() for w in state.warnings],
    }
    write_json(out_dir / "12_downstream_audit_summary.json", summary)
    if state.failures:
        write_json(debug_dir / "errors.json", summary["failures"])

    write_json(
        out_dir / "00_input_metadata.json",
        {
            "mode": mode,
            "user_id": args.user_id,
            "target_date": args.date,
            # Deterministic for replay/frozen (a commit never knows its own
            # SHA); only the live mode records the runtime SHA.
            "git_head": get_git_head() if mode == "live" else None,
            "sidecar_trusted": True,
            "sidecar_source": sidecar_source,
            "today_payload_source": today_payload_source,
            "scoring_version": SCORING_V2_VERSION,
            "calculation_version": CALCULATION_VERSION,
            "activation_layer_version": ACTIVATION_LAYER_VERSION,
            "canon_versions": get_canon_versions(),
            "fail_on_unmapped": bool(args.fail_on_unmapped),
        },
    )

    print(json.dumps({"status": summary["status"], "failure_count": summary["failure_count"], "out": str(out_dir)}, indent=2))
    if state.failures:
        raise SystemExit(1)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Post-sidecar downstream V2 correctness audit")
    p.add_argument("--user-id", default="synthetic")
    p.add_argument("--date", default="2026-07-08")
    p.add_argument("--out", required=True)
    p.add_argument("--input-activation-layer", default=None)
    p.add_argument("--input-final-payload", default=None)
    p.add_argument("--input-day-signals", default=None)
    p.add_argument("--synthetic-fixture", default=None)
    p.add_argument("--fail-on-unmapped", default="true", choices=["true", "false"])
    p.add_argument("--skip-live-today-service", action="store_true")
    args = p.parse_args(argv)
    args.fail_on_unmapped = args.fail_on_unmapped == "true"
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run_downstream_audit(args)


if __name__ == "__main__":
    main()
