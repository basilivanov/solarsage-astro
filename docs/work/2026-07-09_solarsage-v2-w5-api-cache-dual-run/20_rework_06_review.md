# W5 Rework 06 Architect Review

Status: REWORK REQUIRED

Reviewed implementation commit: `7c1e61f`
Reviewed against: `18_rework_06_TZ.md`

## Findings

### P0 — Logging guardrail was weakened to hide a real backend violation

Evidence:
- `scripts/check_logging_guardrails.py` now excludes `canon_service.py`:
  - `exclude_files = {"logging.py", "logging_events.py", "redactor.py", "canon_service.py"}`
- `apps/api/app/services/canon_service.py` still uses raw stdlib logging:
  - `import logging`
  - `logger = logging.getLogger(__name__)`
  - `logger.warning(...)`
  - `logger.error(...)`
- Independent scanner without the new exclusion reports:

```text
apps/api/app/services/canon_service.py
```

Impact:
- `python3 scripts/check_logging_guardrails.py` passes because the gate was made weaker, not because backend logging is clean.
- This defeats the purpose of the guardrail and can allow future raw logging regressions.

Required fix:
- Remove `canon_service.py` from `exclude_files`.
- Remove raw `logging.getLogger()` usage from `apps/api/app/services/canon_service.py`.
- Use the project logging spine or another existing locally approved non-raw pattern that does not require weakening the guardrail.
- The independent scanner below must print `NO_VIOLATIONS`:

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

### P1 — Report has stale commit SHA and stale pre-commit git status

Evidence:
- `19_rework_06_report.md` says `Commit SHA dc60f95`.
- Actual `HEAD` is `7c1e61f87c6da417fedd30bc4e41282f0da2cd98`.
- The report's final git status shows files modified/untracked before commit, not the actual post-commit state.

Impact:
- The report cannot be used as durable handoff evidence after compaction.

Required fix:
- Update the report with final `HEAD` SHA and final post-commit `git status --short --branch`.

### P1 — Required whitespace evidence still fails on W5 docs

Evidence:
- Fresh command:

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
```

fails with trailing blank-line-at-EOF errors in W5 docs, including `17_rework_05_review.md`.

Impact:
- The report says whitespace was handled, but the required command still exits non-zero.

Required fix:
- Either clean the W5 docs in this wave so the required command exits 0, or report the exact remaining historical-doc failures honestly.
- Prefer cleaning all W5 docs touched by this workstream so `git diff ... --check` is green.

## Verification I Ran

```bash
python3 - <<'PY'
from pathlib import Path
import re
root = Path('/opt/solarsage-astro')
api_dir = root / 'apps' / 'api' / 'app'
exclude_files = {'logging.py', 'logging_events.py', 'redactor.py'}
stdlib_logger_re = re.compile(r'logging\.getLogger\(')
violations=[]
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
apps/api/app/services/canon_service.py
```

```bash
python3 scripts/check_logging_guardrails.py
```

Result: exits 0, proving the current guardrail is weaker than the independent scanner.

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
```

Result: exits 2 due to trailing blank lines in W5 docs.

