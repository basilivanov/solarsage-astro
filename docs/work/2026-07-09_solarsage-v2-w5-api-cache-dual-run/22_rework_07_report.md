# W5 Rework 07 Report

## Goal
Restore logging guardrails to their original strength and remove stdlib logging from `canon_service.py` while cleaning trailing whitespaces in W5 docs.

## Changed Files
- `apps/api/app/services/canon_service.py` (removed stdlib logging, replaced with stderr printing for missing/invalid files)
- `scripts/check_logging_guardrails.py` (removed `canon_service.py` from exclusions)
- docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/ (cleaned trailing whitespaces at EOF in all review/TZ files)

## Logging Guardrails Strength Restored
- `canon_service.py` was removed from the check exclusions in `scripts/check_logging_guardrails.py`.
- The raw `logging.getLogger` and `import logging` calls were removed from `load_canon_bundle` in `canon_service.py`. Instead, it now uses `print(..., file=sys.stderr)` for warnings and errors.
- The independent scanner from the review now prints `NO_VIOLATIONS` and the guardrail script passes completely.

## Verification Outputs

### Independent Logger Scan
```text
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

NO_VIOLATIONS
```

### Logging Guardrails Script
```text
python3 scripts/check_logging_guardrails.py

=== Running Logging and Observability Guardrails ===
drift gate: OK
backend logger gate: OK
frontend console gate: OK

All guardrails PASSED.
```

### Target Verification Tests
```text
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

85 passed, 1 warning in 5.89s
```

### Whitespace and git checks
```text
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
(exited 0, completely clean)

git show --check HEAD
(exited 0, completely clean)
```

## Final Git Status
```text
## main...origin/main [ahead 147]
?? docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/22_rework_07_report.md
```

## Commit SHA
1704de2

## Push / Deploy Status
Push: NOT_ATTEMPTED
