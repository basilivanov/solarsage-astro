# Rework 06 Report: Wave W0 SolarSage V2 Audit Baseline

## Changed Files
- `scripts/audit_today.py` — Major architecture refactoring (see below)
- `artifacts/audit/2026-07-08/11_final_today_payload.json` — Regenerated baseline
- `artifacts/audit/2026-07-08/14_claims_audit.md` — Regenerated baseline

## Architecture Decisions

### 1. Default canonical mode is now LLM-free with fail-fast on missing baseline

The default `make audit-day` is a **baseline verifier** that:
- Checks for the existence of `artifacts/audit/<DATE>/11_final_today_payload.json` (committed baseline fixture) before any LLM-capable code path.
- If the baseline fixture is missing, exits non-zero with a clear error message before writing canonical files or calling `TodayService`.
- Recomputes all deterministic astrology/scoring/evidence fields from scratch (profile, transits, natal context, signals, scoring, semantic contexts, oracle comparisons).
- Skips `TodayService.get_today_payload()` entirely in default mode — no production payload is fetched, no cache is mutated, no LLM is called.
- Writes fresh deterministic files (`00_*` through `10_*`, `12-13_*`, `15_*`) to the canonical root.
- Keeps `11_final_today_payload.json` and `14_claims_audit.md` frozen from the committed baseline — never overwrites them.

### 2. Live-LLM sample mode is fully isolated

In `--live-llm-sample` mode:
- All output routes to `artifacts/audit/<DATE>/live/<timestamp>/`
- Debug files go under `artifacts/audit/<DATE>/live/<timestamp>/debug/`
- Zero files are written to the canonical `artifacts/audit/<DATE>/` root or `debug/` directory
- `git diff --exit-code -- artifacts/audit/2026-07-08` passes after live mode without any manual file restoration

### 3. Advice contradiction fixed and proven in baseline

The `WhyThisHappens` practical_meaning section in `semantic_service.py` conditionally omits the "Общайся с близкими — аспекты благоприятствуют отношениям." bullet when `sphere_scores["relationships_partnership"] < 2.0`. The regenerated baseline `11_final_today_payload.json` has 0 matches for `Общайся с близкими.*отнош` (confirmed by `rg`).

## Verification Results

| Check | Result |
|---|---|
| `pytest` (API suite, 6 files) | **37 passed** |
| `pytest` (sidecar suite, 2 files) | **5 passed** |
| `scripts/test_audit_scoring_oracle.py` | **exit 0** |
| `make audit-day` + `git diff --exit-code` | **Deterministic (zero diff)** |
| Live sample + `git diff --exit-code` | **Isolated (zero diff after live, no restoration)** |
| `rg` for N/A, fallback text, relationship outreach in payload | **No matches** (stale history section excluded) |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| `git status --short --branch` | Only known unrelated untracked files |

## Commit SHA
- **Implementation commit**: `0ac418c3654a6ac0588fcde22e90cc7a04acf437`
- **Note**: Final callback HEAD is intentionally not embedded to avoid self-reference.

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
