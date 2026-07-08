# Rework 05 Report: Wave W0 SolarSage V2 Audit Baseline

## Architecture for Cold-Cache-Safe Deterministic Baseline

**Design**: Stable canonical projection with baseline LLM fixture.

The default `make audit-day` is a **baseline verifier** that:
1. Recomputes all deterministic astrology/scoring/evidence fields from scratch (profile, transits, natal context, signals, scoring, semantic contexts, day summary facts, concrete advice keys/verdicts/evidence, oracle comparisons).
2. Loads volatile LLM narrative text (headline, reading, notes, why sections, concrete advice text, planet interpretations) from the committed canonical `11_final_today_payload.json` baseline fixture.
3. Merges fresh deterministic fields with frozen LLM fields to produce the 16 canonical output files.
4. Normalizes `meta.generated_at` and `meta.cached` for stability.

This ensures the baseline is fully deterministic regardless of:
- Absence of `TodayPayloadCache` in the database
- Changes in LLM output between runs
- Clean CI environments without pre-existing cache

The baseline fixture is created on the first `make audit-day` run (which generates fresh LLM text). Subsequent runs use the frozen fixture. To refresh the baseline, run `scripts/audit_today.py --live-llm-sample` and commit the resulting canonical artifacts.

**Live-LLM sample mode** (`--live-llm-sample`):
- Writes fresh output to `artifacts/audit/<DATE>/live/<timestamp>/`
- Never overwrites canonical root files (00-15)
- After running, inspect the live output; commit it to the canonical path only if it should become the new baseline

## Live Sample Output Path

```
artifacts/audit/2026-07-08/live/<YYYYMMDDTHHMMSS>/
├── 14_claims_audit.md
└── final_today_payload.json
```

## Advice Contradiction Fix (WhyThisHappens)

`apps/api/app/services/semantic_service.py` practical_meaning section now checks `sphere_scores["relationships_partnership"]` before including a relationship-related bullet item. When the score is below 2.0 (mapping to "avoid" verdict), the "Общайся с близкими — аспекты благоприятствуют отношениям." bullet is omitted, preventing payload-level contradiction with the `ConcreteAdvice.relationships.verdict = "avoid"` row.

## Verification Results

| Command | Result |
|---|---|
| `pytest` (API suite) | **37 passed** |
| `pytest` (sidecar suite) | **5 passed** |
| `scripts/test_audit_scoring_oracle.py` | **exit 0** |
| Two consecutive `make audit-day` runs | **Deterministic (zero diff)** |
| Live-LLM sample does not change canonical root files (00-15) | **PASS** |
| `git diff 2f9173f..HEAD --check` | **Clean** (verified) |
| `git show --check HEAD` | **Clean** (verified) |
| `git status --short --branch` | Only expected untracked files remain |

## Commit SHAs
- **Implementation commits**: `ebb5538`, `73de154`
- **Note**: Final callback HEAD is intentionally not embedded to avoid self-reference in a single document.

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
