# Review: `fix/logging-hardening` / R3.2 logging hardening

Date: 2026-06-11
Branch: `fix/logging-hardening`
Head: `8e23e213fb127041a27d33b0ff447aeb3162568f`
Base checked against: `main` at `68d5d288def4c1885261c79a423d8a02bb0c814c`

## Verdict

**REQUEST CHANGES — small but important hardening fixes before merge.**

The branch is a strong improvement and closes most of the previous R1/R2/R3 concerns:

- `log_event()` is now typed as `LogEventName` and validates against the generated registry at runtime.
- `msg` and `http` are redacted in the backend `log_event()` path.
- `/api/_log` validates `env`, `service`, and `event` more strictly.
- `apiFetch()` now moves `duration_ms` to the canonical top-level envelope field through log metadata.
- `log_block()` exists and is tested.
- Logging guardrails are now wired into `strict`.
- Backend service logging and frontend console migration are mostly implemented.

Do not merge yet because two guard/privacy issues remain:

1. Frontend bearer-token redaction regex is over-escaped and likely does not match real authorization values.
2. Console guardrail excludes any file named `index.ts` / `logger.ts` globally, not just the logging layer, so production console calls can slip through in common app files.

---

## Confirmed fixed / accepted

### R1 — Backend event validation is now non-bypassable enough for this phase

`log_event()` now takes `event: LogEventName`, and runtime validation always checks `typing.get_args(LogEventName)` before emitting. Unknown event names now raise `ValueError` instead of silently producing off-registry logs.

Evidence:

- `apps/api/app/core/logging.py:216-245`

### R2 — Backend `msg` and `http` redaction is implemented

`log_event()` now redacts `payload`, `error`, `msg`, and `http` before `_emit()`.

Evidence:

- `apps/api/app/core/logging.py:247-268`

There is also a backend test that verifies email/IP redaction in `msg`, and `ip` / `authorization` redaction inside `http`.

Evidence:

- `apps/api/tests/test_log_envelope_shape.py:148-187`

### R2 — Frontend console now prints redacted message

`logEvent()` redacts `envelope.msg` before console/ship, and console prints `envelope.msg`, not raw `meta.msg`.

Evidence:

- `lib/log/index.ts:35-55`

### R3 — Guardrails are present and wired into `strict`

`scripts/check_logging_guardrails.py` now has three gates:

- canon/Python/TS registry drift;
- no raw/legacy backend logging;
- no production console usage outside allowlist.

Evidence:

- `scripts/check_logging_guardrails.py:9-15`
- `scripts/check_logging_guardrails.py:28-83`
- `scripts/check_logging_guardrails.py:88-119`
- `scripts/check_logging_guardrails.py:124-182`

`guardrails.sh strict` now runs `run_logging_guardrails` after `run_backend_grace`.

Evidence:

- `scripts/guardrails.sh:64-73`

### `/api/_log` validation is stronger

The intake model now validates:

- `env` as `Literal["dev", "test", "staging", "prod"]`;
- `service` as `Literal["api", "web", "solarsage", "worker"]`;
- `event` as `LogEventName`;
- non-empty `service_version`, `slice`, `module`, `block`, `correlation_id`.

Evidence:

- `apps/api/app/api/_log.py:29-50`

### `/api/_log` preserves frontend envelopes

The intake service redacts the incoming envelope and emits the same redacted object through centralized `_emit()`, instead of rebuilding it through backend `log_event()`.

Evidence:

- `apps/api/app/services/log_intake.py:79-104`

### `apiFetch()` canonical duration fixed

`duration_ms` is now passed through log metadata, not inside event payload.

Evidence:

- `lib/api-fetch.ts:27-39`
- `lib/api-fetch.ts:42-51`

### `log_block()` is useful and tested

`log_block()` temporarily overrides `slice/module/block/operation_id` and restores previous context after exit.

Evidence:

- `apps/api/app/core/logging.py:118-141`
- `apps/api/tests/test_log_block_context_manager.py:21-68`

---

## Required changes before merge

## RC1 — Frontend bearer-token regex is over-escaped

Severity: **major privacy bug**

In `lib/log/redactor.ts`, the bearer-token pattern is constructed with doubled escaping inside a `RegExp` string. Because this is a string passed to `RegExp`, those doubled backslashes likely compile to a pattern that looks for literal backslash markers rather than a word boundary and whitespace. In practice, frontend strings containing bearer authorization values may not be redacted.

Evidence:

- `lib/log/redactor.ts:39-44`

Why this matters:

- The backend redactor pattern is correct.
- Frontend redaction is supposed to happen before console and before ship.
- Current frontend tests check email and key-based birth data, but not bearer-pattern coverage.

Required fix:

Use either a regex literal for the bearer pattern, or the correctly escaped `RegExp` constructor string with single escaping for regex metacharacters.

Add a frontend test that asserts a string containing a bearer-style authorization value is replaced with `[redacted-bearer]` and the original value is absent.

---

## RC2 — Console guardrail excludes every `index.ts` / `logger.ts` by basename

Severity: **major guardrail gap**

`check_frontend_console()` intends to exclude specific logging files, but the implementation checks only `path.name`. Because `exclude_files` contains `index.ts`, **any** file named `index.ts` anywhere in the repository is skipped.

Evidence:

- `scripts/check_logging_guardrails.py:134-155`

Why this matters:

- Many production modules commonly use `index.ts` as an entrypoint.
- A future production file like `components/foo/index.ts` could contain `console.error(...)` and pass the guardrail.
- Same issue applies to any file named `logger.ts`, even if it is not the canonical logging shim/layer.

Required fix:

Replace basename allowlist with path-specific allowlist, for example exact relative paths such as:

- `lib/log/index.ts`
- `lib/log/shipper.ts`
- `lib/log/redactor.ts`
- `lib/logger.ts`
- `public/telemetry/fetch-interceptor.js`

Then compare `rel = path.relative_to(ROOT).as_posix()` against that exact set.

Add a negative test fixture if possible: a non-allowlisted feature `index.ts` containing `console.error(...)` must fail the guardrail.

---

## Cleanup / nits

### N1 — Duplicate import in `_log.py`

`Annotated`, `Any`, and `Literal` are imported twice.

Evidence:

- `apps/api/app/api/_log.py:11-18`

### N2 — Stale `import logging` in `llm_service.py`

`llm_service.py` still imports `logging`, while the visible replacements use `log_event` / `log_block`.

Evidence:

- `apps/api/app/services/llm_service.py:12-20`

This should be removed if unused. Ruff may or may not be configured to catch this; either way it is dead code.

### N3 — Branch is diverged from `main`

The branch is ahead by 1 and behind by 1. The missing main commit is only the previous blocked review doc, but the PR will be cleaner after rebase/merge.

Evidence:

- compare result: `fix/logging-hardening` is `ahead_by=1`, `behind_by=1`, merge base `8a933cf...`, main `68d5d288...`.

---

## Test evidence note

I did not run tests locally and no GitHub workflow runs/statuses were visible through the connector for branch head `8e23e213...`. The stated `1333 tests pass` is therefore accepted as user-provided evidence, not independently verified here.

Recommended committed/CI evidence before merge:

- `bash scripts/guardrails.sh strict`
- backend tests
- frontend tests
- ideally one artifact/log summary in `docs/work` or CI checks on the PR

---

## Merge recommendation

Merge after RC1 and RC2 are fixed.

After those two changes, I would mark R3.2 as **ACCEPTED** for the logging hardening scope. The remaining cleanup nits are not architectural blockers.
