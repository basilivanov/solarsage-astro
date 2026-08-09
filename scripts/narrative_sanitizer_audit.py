#!/usr/bin/env python3

# ############################################################################
# AI_HEADER: NARRATIVE_SANITIZER_AUDIT — offline rule-hit audit for saved eval claims.
# ROLE: Replays the production sanitizer against immutable raw narrative traces
#       and emits a masked, deterministic distribution for the S21 rebalance.
# ############################################################################

# START_MODULE_CONTRACT: M-SCRIPTS-NARRATIVE-SANITIZER-AUDIT
# purpose: Audit sanitizer pass/null decisions and rule hits from a saved
#   narrative model evaluation without contacting a provider or writing raw text.
# owns:
#   - scripts/narrative_sanitizer_audit.py
# inputs: saved raw response directory and the matching masked inputs.json.
# outputs: masked per-claim audit JSON with rule-class counts and facet matrix.
# dependencies: narrative_model_eval response normalization and the production
#   narrative_sanitizer pattern tables.
# side_effects: writes one compact JSON report only.
# emitted_logs: none.
# invariants: raw provider responses are never copied to the report; each claim
#   is evaluated with the same public sanitizer predicates used by the scorer;
#   output ordering is deterministic.
# failure_policy: malformed input paths or report data fail closed with a nonzero
#   process exit; malformed individual responses are recorded by class.
# END_MODULE_CONTRACT: M-SCRIPTS-NARRATIVE-SANITIZER-AUDIT

# START_MODULE_MAP: M-SCRIPTS-NARRATIVE-SANITIZER-AUDIT
# public_entrypoints:
#   - main
# semantic_blocks:
#   - LOAD: immutable run and expected-input loading.
#   - CLASSIFY: production pattern replay and rule-hit attribution.
#   - REPORT: masked deterministic JSON report.
# owned_tests: none
# END_MODULE_MAP: M-SCRIPTS-NARRATIVE-SANITIZER-AUDIT

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
import json
import re
import sys
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUN = REPO_ROOT / ".eval-runs" / "narrative-model-eval-v1" / "20260809T082931Z"
DEFAULT_INPUTS = REPO_ROOT / "evals" / "tasks" / "today-narrative-v5-models" / "inputs.json"
DEFAULT_OUTPUT = REPO_ROOT / "evals" / "results" / "20260809T082931Z" / "sanitizer-audit.json"
CLAIMS = ("summary", "meaning", "action")
RULE_CLASSES = ("facet_conflict", "sphere_conflict", "polarity_antonym", "forbidden_token")


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"missing JSON: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON: {path}: {exc}") from exc


def _load_production_modules() -> tuple[Any, Any]:
    """Load scorer normalization and the production sanitizer read-only."""
    app_root = REPO_ROOT / "apps" / "api"
    scripts_root = REPO_ROOT / "scripts"
    contracts_root = REPO_ROOT / "packages" / "py-contracts"
    for path in (str(app_root), str(contracts_root), str(scripts_root), str(REPO_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)
    import narrative_model_eval as eval_module
    from app.services import narrative_sanitizer

    return eval_module, narrative_sanitizer


def _mask_claim(text: str, name_token: str) -> str:
    """Mask the committed eval name token and the owner's Russian name forms."""
    masked = text
    tokens = {
        name_token,
        "Василий",
        "Василия",
        "Василию",
        "Василием",
        "Василии",
    }
    for token in sorted((item for item in tokens if item), key=len, reverse=True):
        masked = re.sub(re.escape(token), "ИМЯ", masked, flags=re.IGNORECASE)
    return masked


def _pattern_hits(
    text: str,
    *,
    expected: Mapping[str, Any],
    sanitizer: Any,
) -> list[dict[str, str]]:
    """Replay every sanitizer rule in the same fail-closed precedence family."""
    hits: list[dict[str, str]] = []

    for index, pattern in enumerate(sanitizer._FORBIDDEN_PATTERNS):
        if pattern.search(text) is not None:
            hits.append(
                {
                    "class": "forbidden_token",
                    "pattern_id": f"forbidden:{index}",
                    "pair": "token",
                }
            )

    masked_text = sanitizer._mask_lot_names(text)
    allowed_spheres = {str(expected.get("sphere"))}
    allowed_facets = {
        str(expected["facet"])
    } if expected.get("facet") is not None else set()
    detected_facets: dict[str, list[str]] = {}
    for facet, patterns in sanitizer._HARD_FACET_PATTERNS.items():
        pattern_ids = [
            f"facet:{facet}:{index}"
            for index, pattern in enumerate(patterns)
            if pattern.search(masked_text) is not None
        ]
        if pattern_ids:
            detected_facets[facet] = pattern_ids
    for facet, pattern_ids in detected_facets.items():
        if facet not in allowed_facets:
            for pattern_id in pattern_ids:
                hits.append(
                    {
                        "class": "facet_conflict",
                        "pattern_id": pattern_id,
                        "pair": f"{expected.get('facet') or 'null'}×{facet}",
                    }
                )

    detected_spheres: dict[str, list[str]] = {}
    for sphere, patterns in sanitizer._HARD_SPHERE_PATTERNS.items():
        pattern_ids = [
            f"sphere:{sphere}:{index}"
            for index, pattern in enumerate(patterns)
            if pattern.search(masked_text) is not None
        ]
        if pattern_ids:
            detected_spheres[sphere] = pattern_ids
    allowed_facet_owners = {
        sanitizer._FACET_TO_SPHERE[facet]
        for facet in detected_facets
        if facet in allowed_facets
    }
    for sphere, pattern_ids in detected_spheres.items():
        if sphere in allowed_spheres or sphere in allowed_facet_owners:
            continue
        for pattern_id in pattern_ids:
            hits.append(
                {
                    "class": "sphere_conflict",
                    "pattern_id": pattern_id,
                    "pair": f"{expected.get('sphere') or 'null'}×{sphere}",
                }
            )

    if "health" in allowed_spheres:
        for index, pattern in enumerate(sanitizer._HEALTH_DIAGNOSIS_PATTERNS):
            if pattern.search(text) is not None:
                hits.append(
                    {
                        "class": "sphere_conflict",
                        "pattern_id": f"health_diagnosis:{index}",
                        "pair": "health×health_diagnosis",
                    }
                )

    if allowed_facets and detected_spheres and detected_spheres.keys() & allowed_spheres:
        if sanitizer._BROAD_SCOPE_RE.search(masked_text) is not None:
            hits.append(
                {
                    "class": "sphere_conflict",
                    "pattern_id": "broad_scope",
                    "pair": f"{expected.get('facet')}×{expected.get('sphere')}",
                }
            )
    polarity = str(expected.get("polarity"))
    for index, pattern in enumerate(sanitizer._POLARITY_CONFLICT_PATTERNS.get(polarity, ())):
        for match in pattern.finditer(masked_text):
            if sanitizer._is_contextual_tense_easy(masked_text, match, polarity):
                continue
            prefix = masked_text[max(0, match.start() - 40) : match.start()]
            boundary = max(
                (prefix.rfind(marker) for marker in ".!?;\n"),
                default=-1,
            )
            window = prefix[boundary + 1 :]
            if sanitizer._POLARITY_NEGATION_MARKER_PATTERN.search(window) is None:
                hits.append(
                    {
                        "class": "polarity_antonym",
                        "pattern_id": f"polarity:{polarity}:{index}",
                        "pair": f"{polarity}×antonym",
                    }
                )
                break

    return hits


def _block_metadata(expected: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    blocks: dict[str, Mapping[str, Any]] = {}
    for item in expected.get("convergences", []):
        if isinstance(item, Mapping):
            blocks[str(item["groupId"])] = item
    main_event = expected.get("main_event")
    if isinstance(main_event, Mapping):
        blocks[str(main_event["eventId"])] = main_event
    for item in expected.get("impulses", []):
        if isinstance(item, Mapping):
            blocks[str(item["eventId"])] = item
    return blocks


def _iter_claims(normalized: Mapping[str, Any], expected: Mapping[str, Any]):
    metadata = _block_metadata(expected)
    ordered_blocks: list[tuple[str, Any]] = []
    ordered_blocks.extend((str(item["groupId"]), normalized["convergences"].get(str(item["groupId"]))) for item in expected.get("convergences", []))
    main_event = expected.get("main_event")
    if isinstance(main_event, Mapping):
        ordered_blocks.append((str(main_event["eventId"]), normalized.get("main_event")))
    ordered_blocks.extend((str(item["eventId"]), normalized["impulses"].get(str(item["eventId"]))) for item in expected.get("impulses", []))
    for block_id, block in ordered_blocks:
        block_meta = metadata[block_id]
        if not isinstance(block, Mapping):
            continue
        for claim_name in CLAIMS:
            claim = block.get(claim_name)
            if not isinstance(claim, Mapping) or not isinstance(claim.get("text"), str):
                continue
            text = claim["text"].strip()
            if text:
                yield block_id, claim_name, text, block_meta


def _audit(run_dir: Path, inputs_path: Path) -> dict[str, Any]:
    eval_module, sanitizer = _load_production_modules()
    inputs_document = _load_json(inputs_path)
    inputs = {
        str(record["input_id"]): record
        for record in inputs_document.get("inputs", [])
        if isinstance(record, Mapping) and record.get("input_id")
    }
    raw_paths = sorted(
        path
        for path in run_dir.glob("*.json")
        if path.name not in {"manifest.json", "review-key.json"}
    )
    if not raw_paths:
        raise SystemExit(f"no raw response files in: {run_dir}")

    claims: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    verdict_counts: Counter[str] = Counter()
    facet_matrix: defaultdict[str, Counter[str]] = defaultdict(Counter)
    response_errors: Counter[str] = Counter()
    by_model_arm: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"claims": 0, "passed": 0, "nulled": 0})

    for path in raw_paths:
        envelope = _load_json(path)
        input_id = str(envelope.get("input_id", ""))
        expected_record = inputs.get(input_id)
        if expected_record is None:
            response_errors["missing_input"] += 1
            continue
        normalized, error = eval_module._normalize_response(
            envelope.get("response"),
            str(envelope.get("arm", "")),
            expected_record.get("expected", {}),
        )
        if normalized is None:
            response_errors[str(error or "invalid_response")] += 1
            continue
        model_arm = f"{envelope.get('model_key', 'unknown')}|{envelope.get('arm', 'unknown')}"
        name_token = str(expected_record.get("name_token", "ИМЯ"))
        for block_id, claim_name, text, block_meta in _iter_claims(normalized, expected_record["expected"]):
            rule_hits = _pattern_hits(text, expected=block_meta, sanitizer=sanitizer)
            verdict = "null" if rule_hits else "pass"
            verdict_counts[verdict] += 1
            by_model_arm[model_arm]["claims"] += 1
            by_model_arm[model_arm]["nulled" if verdict == "null" else "passed"] += 1
            for hit in rule_hits:
                class_name = hit["class"]
                class_counts[class_name] += 1
                pair = hit["pair"]
                if class_name == "facet_conflict":
                    claimed, detected = pair.split("×", 1)
                    facet_matrix[claimed][detected] += 1
            claims.append(
                {
                    "model_key": str(envelope.get("model_key", "")),
                    "arm": str(envelope.get("arm", "")),
                    "input_id": input_id,
                    "repeat": envelope.get("repeat"),
                    "block_id": block_id,
                    "claim": claim_name,
                    "sphere": block_meta.get("sphere"),
                    "facet": block_meta.get("facet"),
                    "polarity": block_meta.get("polarity"),
                    "verdict": verdict,
                    "text": _mask_claim(text, name_token),
                    "rule_hits": rule_hits,
                }
            )

    claims.sort(
        key=lambda item: (
            item["input_id"],
            item["model_key"],
            item["arm"],
            int(item["repeat"] or 0),
            item["block_id"],
            item["claim"],
        )
    )
    return {
        "schema_version": 1,
        "source": {
            "raw_run": str(run_dir.relative_to(REPO_ROOT)),
            "inputs": str(inputs_path.relative_to(REPO_ROOT)),
            "raw_response_files": len(raw_paths),
            "normalized_response_errors": dict(sorted(response_errors.items())),
        },
        "summary": {
            "claims": len(claims),
            "pass": verdict_counts["pass"],
            "null": verdict_counts["null"],
            "pass_rate": round(verdict_counts["pass"] / (len(claims) or 1), 6),
            "rule_hits_by_class": {name: class_counts[name] for name in RULE_CLASSES},
            "by_model_arm": {
                key: value for key, value in sorted(by_model_arm.items())
            },
        },
        "facet_matrix": {
            claimed: dict(sorted(detected.items()))
            for claimed, detected in sorted(facet_matrix.items())
        },
        "claims": claims,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline narrative sanitizer rule-hit audit")
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    report = _audit(args.run, args.inputs)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = report["summary"]
    print(
        "narrative_sanitizer_audit: PASS "
        f"files={report['source']['raw_response_files']} claims={summary['claims']} "
        f"pass={summary['pass']} null={summary['null']} output={args.out}"
    )
    print(f"rule_hits_by_class={json.dumps(summary['rule_hits_by_class'], ensure_ascii=False, sort_keys=True)}")
    print(f"facet_matrix={json.dumps(report['facet_matrix'], ensure_ascii=False, sort_keys=True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
