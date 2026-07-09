# W5 Rework 07 TZ — Do Not Weaken Logging Guardrails

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W5 Rework 06 (`7c1e61f`)
Push/deploy: do not push or deploy.

## Goal

Resolve all findings from:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/20_rework_06_review.md
```

This is a narrow cleanup/rework. Do not redo W5 tests. Do not weaken guardrails.

## Required Work

### 1. Restore logging guardrail strength

- Remove `canon_service.py` from `scripts/check_logging_guardrails.py` backend logger exclusions.
- Remove raw stdlib logger usage from `apps/api/app/services/canon_service.py`.
- Keep `scripts/check_logging_guardrails.py` valid and non-duplicated.
- Keep `.grace` / `.next-prod` frontend scan exclusions if they are needed for generated/local output noise.
- Keep `lib/log/events.gen.ts` aligned with XML/Python if `scoring.v2_diff` is canonical.

Acceptance:

```bash
python3 scripts/check_logging_guardrails.py
```

passes, and the independent scanner from the review prints:

```text
NO_VIOLATIONS
```

### 2. Fix report metadata

Update:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/19_rework_06_report.md
```

with:
- actual final `HEAD` commit SHA after this rework;
- actual final post-commit `git status --short --branch`;
- exact note that Rework 07 fixed the guardrail weakening from Rework 06.

If you prefer, create an additional report:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/22_rework_07_report.md
```

but `19_rework_06_report.md` must no longer claim stale SHA/status as final evidence.

### 3. Fix whitespace evidence

Make the required whitespace commands honest:

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
```

Preferred: clean trailing blank-line-at-EOF issues in W5 docs so both commands exit 0.

If any older historical doc cannot be changed for a concrete reason, report exact remaining files and reason. Do not say whitespace is clean if the command exits non-zero.

## Required Verification

Run and report exact commands/results, without `tail`:

```bash
python3 - <<'PY'
from pathlib import Path
import re
root = Path('/opt/solarsage-astro')
api_dir = root / 'apps' / 'api' / 'app'
exclude_files = {'logging.py', 'logging_events.py', 'redactor.py'}
stdlib_logger_re = re.compile(r'logging\.getLogger\(')
violations = []
for path in api_dir.rglob('*.py'):
    if path.name in exclude_files:
        continue
    content = path.read_text(encoding='utf-8')
    if stdlib_logger_re.search(content):
        violations.append(str(path.relative_to(root)))
print('\n'.join(violations) or 'NO_VIOLATIONS')
PY
```

```bash
python3 scripts/check_logging_guardrails.py
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_scoring_v2_runtime_flags.py \
  tests/test_today_cache_v2_key.py \
  tests/test_today_service_v2_dual_run.py \
  tests/test_calendar_v2_dual_run.py \
  tests/test_today_meta_versions.py \
  tests/test_day_endpoints.py \
  tests/test_calendar_endpoints.py \
  tests/test_alembic_roundtrip.py \
  tests/test_log_envelope_shape.py -q
```

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

Full API suite is optional for this tiny cleanup if unchanged since Rework 06. If you skip it, say explicitly that it was not rerun in Rework 07 and preserve Rework 06's full-suite evidence as prior evidence.

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/22_rework_07_report.md
```

Include:
- changed files;
- exact explanation of how `canon_service.py` no longer weakens/violates guardrails;
- exact verification outputs;
- final `HEAD` SHA;
- final git status;
- `Push: NOT_ATTEMPTED`.

Commit implementation and report. Do not push/deploy.

## Callback

After implementation, verification, report, and commit:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W5 Rework 07 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/22_rework_07_report.md. Review: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/20_rework_06_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/21_rework_07_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
