# W5 Rework 07 Architect Review

Status: ACCEPTED

Reviewed commit: `1704de26a442fc3358668fd3897310e395fd68be`
Reviewed against:
- `20_rework_06_review.md`
- `21_rework_07_TZ.md`

## Findings

No blocking findings.

## Notes

- The coder report still lists `f309039` as its commit SHA. This is a stale report field caused by a self-amend loop: the agent wrote `HEAD` into the report, amended the same commit, and changed `HEAD` again. I stopped the tmux session with `Esc Esc` per process rules.
- The durable reviewed SHA for W5 Rework 07 is the commit named above: `1704de26a442fc3358668fd3897310e395fd68be`.
- `canon_service.py` no longer uses `logging.getLogger()`, and `scripts/check_logging_guardrails.py` no longer excludes `canon_service.py`.
- `canon_service.py` now uses stderr prints in its best-effort `load_canon_bundle()` path. This is acceptable for this narrow rework because API startup uses strict `validate_canon_bundle()`, and this wave's binding requirement was to restore the no-raw-logger guardrail without weakening it. A future observability cleanup can introduce a startup-safe structured logging helper for best-effort startup utilities.

## Verification I Ran

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

Result:

```text
NO_VIOLATIONS
```

```bash
python3 scripts/check_logging_guardrails.py
```

Result:

```text
=== Running Logging and Observability Guardrails ===
drift gate: OK
backend logger gate: OK
frontend console gate: OK

All guardrails PASSED.
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

Result:

```text
85 passed, 1 warning in 6.56s
```

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check --oneline HEAD
git status --short --branch
```

Result:

```text
1704de2 W5 Rework 07: restore logging guardrails + remove raw logging from canon_service
## main...origin/main [ahead 149]
?? .grace/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? grace.db
?? skills/
```

The untracked files are pre-existing local artifacts and are not part of W5.
