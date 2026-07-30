# ############################################################################
# AI_HEADER: TEST_CORPUS_SHARD_AGGREGATOR — unit tests for replay shard merge.
# ROLE: Proves cross-shard validation, public metrics, and tense streak logic.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CORPUS-SHARD-AGGREGATOR
# purpose: Verify the stdlib-only corpus shard aggregator with tiny fixtures.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_aggregate_corpus_shards.py
# inputs: pytest tmp_path fixtures.
# outputs: assertions only.
# dependencies: pytest; aggregate_corpus_shards.
# side_effects: writes temporary checkpoint JSON.
# emitted_logs: none.
# invariants: fixtures use the exact v2 checkpoint public contract.
# failure_policy: test failure blocks report tooling acceptance.
# END_MODULE_CONTRACT: M-TEST-CORPUS-SHARD-AGGREGATOR

# START_MODULE_MAP: M-TEST-CORPUS-SHARD-AGGREGATOR
# public_entrypoints: none
# semantic_blocks:
#   - FIXTURES: compact v2 checkpoint builder.
#   - TESTS: merge and duplicate/fingerprint rejection cases.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_aggregate_corpus_shards.py
# END_MODULE_MAP: M-TEST-CORPUS-SHARD-AGGREGATOR

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aggregate_corpus_shards import aggregate_shards


# START_BLOCK: FIXTURES
def _write_checkpoint(
    directory: Path,
    *,
    chart_id: str,
    fingerprint: str = "fingerprint-a",
    tense: tuple[bool, ...] = (True, True, False),
) -> Path:
    daily = []
    for index, value in enumerate(tense, start=1):
        daily.append(
            {
                "date": f"2026-01-0{index}",
                "state": "convergence_today" if index == 1 else "quiet_day",
                "diagnostic_state": "hero" if index == 1 else "single_impulse",
                "n_public": 5,
                "n_significant": 2,
                "n_independent_units": 2,
                "n_groups": 1,
                "n_selected_public_units": 1,
                "tense": value,
                "hero_spheres": ["work"] if index == 1 else [],
            }
        )
    payload = {
        "schema_version": "today-convergence-corpus-chart.v2",
        "status": "ok",
        "source_fingerprint_sha256": fingerprint,
        "chart": {"chart_id": chart_id},
        "date_range": ["2026-01-01", f"2026-01-0{len(tense)}"],
        "elapsed_s": 12.5,
        "errors": [],
        "modes": {
            "exact": {
                "n_days": len(daily),
                "state_distribution": {
                    "convergence_today": 1,
                    "quiet_day": len(daily) - 1,
                },
                "diagnostic_state_distribution": {
                    "hero": 1,
                    "single_impulse": len(daily) - 1,
                },
                "hero_days_n": 1,
                "excluded_reasons": {},
                "tense_days": sum(tense),
                "zero_public_days": 0,
                "raw_activations": 10,
                "raw_ledger": 11,
                "invalid_ledger": 0,
                "duplicate_ledger": 1,
                "timing_deferred": 2,
                "daily": daily,
            }
        },
    }
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{chart_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
# END_BLOCK: FIXTURES


# START_BLOCK: TESTS
def test_aggregate_shards_combines_metrics_and_tense_streaks(tmp_path: Path) -> None:
    first = _write_checkpoint(tmp_path / "a", chart_id="chart-a")
    second = _write_checkpoint(
        tmp_path / "b",
        chart_id="chart-b",
        tense=(False, True, True),
    )

    result = aggregate_shards([first, second], expected_charts=2)

    assert result["charts"] == 2
    assert result["source_fingerprint_sha256"] == "fingerprint-a"
    assert len(result["checkpoint_set_sha256"]) == 64
    exact = result["modes"]["exact"]
    assert exact["days"] == 6
    assert exact["hero_days"] == 2
    assert exact["hero_rate"] == pytest.approx(1 / 3, abs=1e-6)
    assert exact["tense_streak_max"] == 2
    assert exact["selected_public_units_median"] == 1.0
    assert exact["invalid_ledger"] == 0


def test_aggregate_shards_rejects_duplicate_chart_ids(tmp_path: Path) -> None:
    first = _write_checkpoint(tmp_path / "a", chart_id="same")
    second = _write_checkpoint(tmp_path / "b", chart_id="same")

    with pytest.raises(ValueError, match="duplicate chart_id"):
        aggregate_shards([first, second])


def test_aggregate_shards_rejects_fingerprint_drift(tmp_path: Path) -> None:
    first = _write_checkpoint(tmp_path / "a", chart_id="chart-a")
    second = _write_checkpoint(
        tmp_path / "b",
        chart_id="chart-b",
        fingerprint="fingerprint-b",
    )

    with pytest.raises(ValueError, match="fingerprint drift"):
        aggregate_shards([first, second])
# END_BLOCK: TESTS
