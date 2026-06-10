# Final review: `fix/logging-hardening` after RC1/RC2 fixes

Date: 2026-06-11
Branch: `fix/logging-hardening`
Reviewed visible head: `19843b6ae74deb41a52f4b3957d7e7925c35134f`
Note: the handoff mentioned `ce932e1`, but the GitHub connector resolved the branch head to `19843b6...` with the expected fix message and diff.

## Verdict

**ACCEPTED — ready to merge after normal CI / local gate confirmation.**

The two previous blockers are fixed:

1. Frontend bearer-token redaction regex is no longer over-escaped.
2. Console guardrail now excludes logging-layer files by exact relative path instead of excluding every file named `index.ts` / `logger.ts`.

This closes the R3.2 logging hardening review scope.

---

## RC1 — Bearer-token regex

Status: **closed**

Previous issue:

- The frontend redactor used an over-escaped `RegExp` string, so bearer-style authorization values could fail to match.

Current state:

- `lib/log/redactor.ts` now uses the corrected regex-constructor string with proper regex metacharacter escaping.

Evidence:

- `lib/log/redactor.ts:39-44`

Assessment:

- This is now aligned with the intended pattern semantics.
- Recommended but not blocking: add/keep a focused frontend unit test for bearer-style redaction.

---

## RC2 — Console guardrail path allowlist

Status: **closed**

Previous issue:

- `check_frontend_console()` excluded files by basename, so any future production `index.ts` could bypass the console gate.

Current state:

- The guardrail now uses `exclude_paths` with exact relative paths:
  - `lib/log/index.ts`
  - `lib/log/shipper.ts`
  - `lib/log/redactor.ts`
  - `lib/log/logger.ts`
  - `public/telemetry/fetch-interceptor.js`
- `rel = path.relative_to(ROOT).as_posix()` is computed before checking this path allowlist.

Evidence:

- `scripts/check_logging_guardrails.py:134-155`

Assessment:

- This closes the basename-bypass bug.
- Future `components/foo/index.ts` with `console.error(...)` should now be caught.

---

## Previously accepted R3.2 items remain accepted

The following improvements from the previous branch review remain valid:

- `log_event()` is typed as `LogEventName` and validates the closed registry at runtime.
- Backend `log_event()` redacts `payload`, `error`, `msg`, and `http`.
- `/api/_log` validates `env`, `service`, and `event` more strictly.
- `/api/_log` preserves frontend envelopes and emits the redacted original object.
- `apiFetch()` writes `duration_ms` as top-level envelope metadata.
- `log_block()` exists and has context-restore tests.
- Logging guardrails are wired into `scripts/guardrails.sh strict`.

Reference evidence from previous review:

- `apps/api/app/core/logging.py:216-268`
- `apps/api/app/api/_log.py:29-50`
- `apps/api/app/services/log_intake.py:79-104`
- `lib/api-fetch.ts:27-51`
- `scripts/guardrails.sh:64-73`

---

## Non-blocking cleanup

These are not merge blockers:

- `_log.py` still has a duplicate `from typing import Annotated, Any, Literal` import.
- `llm_service.py` still visibly imports `logging`; remove if unused.
- The connector showed no GitHub workflow runs/statuses for the visible branch head, so test pass counts are treated as user-provided/local evidence rather than independently verified CI evidence.

---

## Merge recommendation

**Merge approved after confirming the usual local/CI gates:**

- `bash scripts/guardrails.sh strict`
- backend tests
- frontend tests

No remaining architectural blockers for the logging hardening scope.
