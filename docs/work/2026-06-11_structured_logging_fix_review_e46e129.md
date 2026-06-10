# Review: structured logging fixes W-LOG-FIX-1..5

Date: 2026-06-11
Reviewed commit: `e46e129b199d18723753ff232845315234d8508f`
Scope: follow-up review after P0/P1 blockers B1-B11.

## Verdict

**MOSTLY ACCEPTED, WITH 3 REMAINING CHANGES.**

The fix commit materially closes the main correctness holes from the previous review:

- canon event list now contains the expanded auth/profile/horary/natal/chat/ui.fetch/payment events;
- Python and TS event unions visually match the canon event set;
- middleware now binds `slice/module/block` before `system.request`;
- `/api/_log` now has required non-empty canonical fields and preserves the incoming envelope instead of rebuilding it;
- frontend redactor exists and `logEvent()` redacts payload/msg before ship;
- production console logging is off unless explicitly enabled.

However, I would **not mark the logging spine fully locked** until the remaining issues below are fixed.

---

## Status by previous blocker

### B1 — Registry drift

Status: **mostly closed**

Evidence:

- `grace/canon/observability.xml:199-362` declares the expanded canonical events, including `payment.intent_created`, horary/natal/chat and ui.fetch events.
- `apps/api/app/core/logging_events.py:16-89` contains the same visible event names.
- `lib/log/events.gen.ts:11-83` contains the same visible event names.

Remaining concern:

- There is still no visible guardrail in `scripts/guardrails.sh` that mechanically parses XML/Python/TS and fails on drift. This means the current sync can regress later.

### B2 — Backend event validation

Status: **partially closed**

What improved:

- `build_envelope()` now imports/uses `LogEventName` in its signature.
- Strict runtime validation exists behind `PYTHON_LOG_STRICT=1`.

Evidence:

- `apps/api/app/core/logging.py:120-164`
- `apps/api/app/core/logging.py:188-204`

Remaining problem:

- Public `log_event()` still accepts `event: str`, so normal call sites are not statically typed.
- Runtime validation is optional and only enabled with `PYTHON_LOG_STRICT=1`.
- In non-strict mode, unknown event names can still be emitted.

Required change:

- Change `log_event(event: str, ...)` to `log_event(event: LogEventName, ...)`.
- Either make runtime registry validation always on, or make strict mode part of tests/CI/guardrails.

### B3 — `system.request` missing slice/module/block

Status: **closed**

Evidence:

- `apps/api/app/middleware/correlation.py:89-99` now binds `slice="W-1.6"`, `module="M-OBSERVABILITY-CORRELATION"`, `block="CORRELATION_MIDDLEWARE"`.
- `system.request` is emitted after that context is bound.

### B4 — `/api/_log` drops incoming frontend fields

Status: **closed for preservation path**

Evidence:

- `apps/api/app/api/_log.py:26-53` defines canonical envelope fields.
- `apps/api/app/services/log_intake.py:84-89` redacts and emits the same envelope directly without rebuilding.

Remaining improvement:

- `_emit_line()` opens fd 1 per event; this is probably OK for low volume, but centralizing through the same `_emit()` helper would be cleaner and easier to test.

### B5 — `/api/_log` clears middleware context

Status: **closed**

Evidence:

- `apps/api/app/services/log_intake.py` no longer imports/binds/clears logging context in the happy path.
- Service contract explicitly says it never clears/modifies request-level contextvars.

### B6 — `/api/_log` validation too weak

Status: **mostly closed**

Evidence:

- `apps/api/app/api/_log.py:29-38` makes required envelope fields non-empty.
- `level` has a regex enum.

Remaining problem:

- `event` is only `min_length=1`, not validated against the registry.
- `env` and `service` are only non-empty, not restricted to canon enum values.
- `LogIntakeService.REQUIRED_FIELDS` still checks only `ts/level/event/service`, although Pydantic currently catches more before service call.

Required change:

- Add Pydantic validation for `event` against generated registry.
- Add enum restrictions for `env` and `service`.
- Align `REQUIRED_FIELDS` with the full canon-required list or remove duplicate service-level validation and rely on the strict Pydantic model.

### B7 — Frontend redaction before console/ship

Status: **mostly closed**

Evidence:

- `lib/log/redactor.ts:11-40` defines frontend PII keys and value patterns.
- `lib/log/index.ts:35-41` redacts payload/msg before ship.
- `lib/log/index.ts:43-55` gates console output and ships redacted envelope.
- `lib/log/redactor.ts:83-88` disables production console logging unless forced.

Remaining problem:

- Console prints `meta?.msg` rather than `envelope.msg`. If `meta.msg` contained PII, console could still show it even though the shipped envelope is redacted.

Required change:

- Console should print `envelope.msg ?? ""`, not `meta?.msg ?? ""`.

### B8 — Backend redaction for `msg` and `http`

Status: **not fully closed in backend `log_event()` path**

Evidence:

- `redact_dict()` can redact strings and dicts generally.
- But `log_event()` only calls redaction for `payload` and `error`.
- There is no redaction call for `envelope["msg"]` or `envelope["http"]` in `apps/api/app/core/logging.py:207-217`.

Required change:

- In `log_event()`, redact `msg` and `http` before `_emit()`:
  - `envelope["msg"] = redact_dict(envelope["msg"])`
  - `envelope["http"] = redact_dict(envelope["http"])`
- Add backend canary tests proving emails/JWT/Bearer/IP do not leak through `msg` or `http`.

### B9 — Legacy/raw logging and guardrails

Status: **not closed**

Evidence:

- Commit message itself says `W-LOG-FIX-5: pending guardrails implementation`.
- `scripts/guardrails.sh` still runs docs/secrets/contracts/backend/frontend/prod checks, but no visible checks for:
  - canon/Python/TS event drift;
  - production console usage outside logging layer;
  - raw `logging.getLogger(__name__)` in feature code;
  - `from app.core.logging import logger` legacy imports;
  - unknown event negative checks.

Evidence locations:

- `scripts/guardrails.sh:159-217`
- `scripts/guardrails.sh:218-270`

Required change:

Add the W-LOG-FIX-5 guardrails as real scripts and wire them into `strict` at minimum, ideally `full` as well.

### B10 — Production console logging always on

Status: **closed**

Evidence:

- `lib/log/redactor.ts:83-88` disables console logging when `NODE_ENV=production` unless `NEXT_PUBLIC_GRACE_LOG_CONSOLE=true`.
- `lib/log/index.ts:43-55` calls console only through `shouldConsoleLog()`.

### B11 — `apiFetch()` duration in payload instead of top-level

Status: **still open / minor**

Evidence:

- `lib/api-fetch.ts:83-97` still passes `duration_ms` inside payload, not as `meta.duration_ms`.
- `logEvent()` supports top-level `duration_ms` via meta.

Required change:

- For success/failure, call:

```ts
logEvent("ui.fetch_succeeded", { route, method, status }, { duration_ms: durationMs })
```

and same for failed.

---

## Remaining must-fix list

### R1 — Make backend event validation non-bypassable

- `log_event(event: LogEventName, ...)`, not `str`.
- Runtime unknown-event validation either always on or mandatory in tests/CI.
- `/api/_log` validates `event` against generated registry.

### R2 — Finish privacy redaction gaps

- Backend `log_event()` redacts `msg` and `http`.
- Frontend console prints already-redacted `envelope.msg`, not raw `meta.msg`.
- Add tests for both.

### R3 — Add actual guardrails

- XML/Python/TS event drift gate.
- No raw backend logger gate.
- No production console usage gate.
- Unknown event negative tests.
- Wire into `scripts/guardrails.sh strict`.

---

## Final assessment

This is now a solid logging spine foundation. I would allow moving on to business-event retrofit only if R1/R2/R3 are immediately queued as a small hardening slice.

If this is meant to be a hard acceptance gate for P0+P1, then status remains: **REQUEST CHANGES — small hardening required**.

If this is meant to unblock parallel feature work, then status can be: **ACCEPT WITH FOLLOW-UP HARDENING**, because the original major architectural mistakes are mostly corrected.
