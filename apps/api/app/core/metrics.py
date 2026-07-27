# ############################################################################
# AI_HEADER: MODULE_METRICS
# ROLE: Prometheus/in-memory counters and metrics for Today valence engine observability.
# DEPENDENCIES: None (lightweight in-memory counters with Prometheus format export)
# GRACE_ANCHORS: [VALENCE_METRICS]
# ############################################################################

# START_MODULE_CONTRACT: M-API-METRICS
# purpose: Track today day status, sphere verdicts, deduplicated factors, and effective family factors metrics (§13).
# owns:
#   - apps/api/app/core/metrics.py
# inputs: version, status, verdict, source_pair, family
# outputs: in-memory counter increments and metrics snapshot
# dependencies: none
# side_effects: updates in-memory counters
# emitted_logs: none
# failure_policy: never raises (fail-safe counters)
# END_MODULE_CONTRACT: M-API-METRICS

# START_MODULE_MAP: M-API-METRICS
# public_entrypoints:
#   - inc_day_status_total
#   - inc_sphere_verdict_total
#   - inc_duplicate_factors
#   - inc_effective_factors
#   - get_metrics_snapshot
# semantic_blocks: none
# owned_tests:
#   - apps/api/tests/test_day_valence_shadow.py
# END_MODULE_MAP: M-API-METRICS

from __future__ import annotations

from typing import Any

_DAY_STATUS_TOTAL: dict[tuple[str, str], int] = {}
_SPHERE_VERDICT_TOTAL: dict[tuple[str, str], int] = {}
_DUPLICATE_FACTORS: dict[str, int] = {}
_EFFECTIVE_FACTORS: dict[str, int] = {}


def inc_day_status_total(version: str, status: str) -> None:
    key = (version, status)
    _DAY_STATUS_TOTAL[key] = _DAY_STATUS_TOTAL.get(key, 0) + 1


def inc_sphere_verdict_total(version: str, verdict: str) -> None:
    key = (version, verdict)
    _SPHERE_VERDICT_TOTAL[key] = _SPHERE_VERDICT_TOTAL.get(key, 0) + 1


def inc_duplicate_factors(source_pair: str, count: int = 1) -> None:
    _DUPLICATE_FACTORS[source_pair] = _DUPLICATE_FACTORS.get(source_pair, 0) + count


def inc_effective_factors(family: str, count: int = 1) -> None:
    _EFFECTIVE_FACTORS[family] = _EFFECTIVE_FACTORS.get(family, 0) + count


def get_metrics_snapshot() -> dict[str, Any]:
    return {
        "today_day_status_total": dict(_DAY_STATUS_TOTAL),
        "today_sphere_verdict_total": dict(_SPHERE_VERDICT_TOTAL),
        "today_valence_duplicate_factors": dict(_DUPLICATE_FACTORS),
        "today_valence_effective_factors": dict(_EFFECTIVE_FACTORS),
    }
