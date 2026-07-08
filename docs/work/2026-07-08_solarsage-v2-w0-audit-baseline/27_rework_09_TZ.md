# Rework 09 TZ: Make W0 Green Under Canonical Full Backend Suite

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Finish W0 acceptance by making the canonical backend test suite green without weakening the W0 trust contracts.

The previous W0-specific gates pass, but the full backend suite fails after the retrograde schema hardening. Fix the tests/fixtures and import path issues so `cd apps/api && python -m pytest tests/ -q` passes.

## Non-Negotiable Architectural Rules

1. Do not revert `NatalChartPlanet.retrograde` or `NatalPreviewChartPlanet.retrograde` to `False` defaults.
2. Do not allow sidecar planet schemas to silently default missing retrograde to `False`.
3. A valid sidecar planet must include either:
   - explicit `retrograde`; or
   - `speed`, from which `retrograde = speed < 0` is derived.
4. Rejection tests must fail for the intended reason, not because unrelated planet fields are invalid.
5. The canonical test cwd is `apps/api`; tests must pass from there.

## Findings To Fix

### 1. `test_natal_report_service.py` fixtures

All `NatalChartPlanet(...)` test fixtures must include explicit `retrograde`.

Known locations:

```text
apps/api/tests/test_natal_report_service.py:74
apps/api/tests/test_natal_report_service.py:75
apps/api/tests/test_natal_report_service.py:76
apps/api/tests/test_natal_report_service.py:77
apps/api/tests/test_natal_report_service.py:78
apps/api/tests/test_natal_report_service.py:79
apps/api/tests/test_natal_report_service.py:80
apps/api/tests/test_natal_report_service.py:107
apps/api/tests/test_natal_report_service.py:108
apps/api/tests/test_natal_report_service.py:733
apps/api/tests/test_natal_report_service.py:734
apps/api/tests/test_natal_report_service.py:809
apps/api/tests/test_natal_report_service.py:810
apps/api/tests/test_natal_report_service.py:884
apps/api/tests/test_natal_report_service.py:885
apps/api/tests/test_natal_report_service.py:1101
apps/api/tests/test_natal_report_service.py:1183
```

Preferred implementation:

- Add a small local helper in the test file if it reduces duplication, for example `planet(...)` that always requires or supplies explicit `retrograde`.
- Use realistic values:
  - direct planets: `retrograde=False`;
  - existing Mars retrograde fixture may remain `retrograde=True`.

Do not change production schemas to satisfy these tests.

### 2. `test_natal_context_service.py` sidecar validation fixtures

Known area:

```text
apps/api/tests/test_natal_context_service.py:311-335
```

Update tests so:

- `test_solar_sage_natal_rejects_empty_houses` reaches the "at least one house" validation by providing a valid planet object.
- `test_solar_sage_natal_accepts_valid_response` uses a valid planet with `retrograde` or `speed`.
- `test_solar_sage_transits_accepts_valid_response` uses valid transit planet(s) with `retrograde` or `speed`.

Keep existing tests that explicitly prove missing retrograde+speed is rejected.

### 3. `test_astronomy_oracle.py` helper import path

Current failure from canonical cwd:

```text
ModuleNotFoundError: No module named 'scripts'
```

Fix the import for `resolve_audit_output_dirs` so these pass from `apps/api`:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_astronomy_oracle.py::test_audit_resolve_output_dirs_default \
  tests/test_astronomy_oracle.py::test_audit_resolve_output_dirs_live \
  -q -vv
```

Acceptable approaches:

- insert repo root into `sys.path` inside the test before importing `scripts.audit_today`; or
- load `scripts/audit_today.py` with `importlib.util.spec_from_file_location`.

Keep the helper pure and keep the live-isolation test.

### 4. Cleanup `scripts/audit_today.py` imports

Remove duplicate/unused imports:

```python
from typing import Any
from typing import Any, NamedTuple
from dataclasses import dataclass, field
```

Expected shape:

```python
from dataclasses import dataclass
from typing import Any
```

No behavior change.

## Required Verification

Run these commands and include exact results in the report:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_astronomy_oracle.py \
  apps/api/tests/test_semantic_contexts.py \
  apps/api/tests/test_today_concrete_advice_consistency.py \
  apps/api/tests/test_today_concrete_advice.py \
  apps/api/tests/test_day_endpoints.py \
  apps/api/tests/test_calendar_endpoints.py \
  -q
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_ephemeris_retrograde.py tests/test_services.py -q
```

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

```bash
apps/api/.venv/bin/python scripts/audit_today.py \
  --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
  --date 2026-07-08 \
  --out artifacts/audit/2026-07-08 \
  --live-llm-sample
git diff --exit-code -- artifacts/audit/2026-07-08
rm -rf artifacts/audit/2026-07-08/live
```

```bash
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\| N/A \| N/A \| N/A \||Рекомендация временно недоступна\.|Общайся с близкими.*отнош' \
  artifacts/audit/2026-07-08/14_claims_audit.md \
  artifacts/audit/2026-07-08/11_final_today_payload.json
echo "expected rg exit: 1"
```

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

## Report

Write report:

```text
docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/28_rework_09_report.md
```

The report must include:

- changed files;
- root cause summary;
- exact verification commands and results;
- whether full API suite passes from `apps/api`;
- audit artifact deterministic status;
- live sample isolation status;
- commit SHA;
- push status `NOT_ATTEMPTED`.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W0 Rework 09 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/28_rework_09_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/26_rework_08_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/27_rework_09_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
