# Rework 04 Report: Wave W0 SolarSage V2 Audit Baseline

## Root Cause Summary

`make audit-day` was not a deterministic baseline command because `scripts/audit_today.py` unconditionally invalidated the production `TodayPayload` cache on every run, causing fresh LLM text generation each time. This made the canonical audit artifacts non-reproducible across consecutive runs.

## Design for Deterministic Canonical Artifacts

**Default path** (deterministic baseline):
- `make audit-day` (without flags) no longer calls `TodayService.invalidate_cache()`.
- It uses the cached `TodayPayload`, which is stable once generated.
- Volatile fields (`meta.generated_at`, `meta.cached`) are normalized to fixed values:
  - `generated_at` → `{target_date}T12:00:00Z`
  - `cached` → `false`
- Run `make audit-day` twice consecutively and `git diff --exit-code -- artifacts/...` is clean.

**Live LLM sampling** (opt-in):
- `scripts/audit_today.py --live-llm-sample` bypasses the cache and generates fresh LLM text.
- Only available via direct Python invocation (or a future `make audit-day-live` target).
- Output written into the `debug/` subdirectory alongside the canonical artifacts.
- An architect targeting live sampling must commit the resulting canonical artifacts if they are to become the new baseline.

## Claims Audit Gate Strengthening

- Added `Рекомендация временно недоступна.` (fallback advice text) to the N/A placeholder check in `test_audit_claims_report_has_no_na_placeholders_for_present_data`.
- The committed W0 canonical baseline must not contain fallback advice text.
- Live LLM sampling may produce fallback text, which the test correctly catches and reports as a degradation.

## Verification Results

| Command | Result |
|---|---|
| `pytest` (API suite) | **37 passed** |
| `pytest` (sidecar suite) | **5 passed** |
| `scripts/test_audit_scoring_oracle.py` | **exit 0** |
| `jq` checks (content_version, cached, moon_phase, retrograde, day_status, top_signals) | **All pass** |
| `rg` for N/A / fallback text in claims report | **No matches** |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| **Two consecutive `make audit-day` runs** | **Deterministic (zero diff)** |
| `git status --short --branch` | Only expected untracked files remain |

## Commit SHA
- **Implementation commit**: `313f114385bcf005f7c083253bd292cd350f261a`

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
