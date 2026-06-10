# Review: structured logging P0+P1

Date: 2026-06-11
Reviewed commit: `ca46ffe97a113c2dbbcb088d19ae0bd7f3fcc805`
Scope: P0 canon/spine + P1 frontend consolidation after `feat(logging): structured logging audit P0+P1`.

## Verdict

**REQUEST CHANGES.**

The patch is a strong move in the right direction: canon fields were added, a backend `log_event()` spine exists, contextvars exist, middleware emits `system.request/system.error`, redactor coverage is much better, frontend logging API exists, and `/api/_log` accepts a canonical-looking model.

But P0+P1 should not be considered closed yet because there are several correctness gaps that break the “one canonical envelope, closed event registry, redact before every transport, every log has slice/module/block” invariant.

Most important: the generated registries are not actually in sync with `grace/canon/observability.xml`, `/api/_log` rebuilds frontend events and drops canonical fields, frontend logs are printed to console before redaction, and backend `log_event()` accepts arbitrary string events without registry validation.

---

## Positive findings

### OK-1 — Canon envelope now includes `slice`, `module`, `block`

`grace/canon/observability.xml` now declares required `slice`, `module`, `block`, plus optional `phase` and `operation_id`.

Evidence:

- `grace/canon/observability.xml:44-67`

### OK-2 — Backend spine exists and builds canonical-shaped JSON

`apps/api/app/core/logging.py` now has contextvars and a `build_envelope()` / `log_event()` path that emits JSON to stdout.

Evidence:

- `apps/api/app/core/logging.py:52-63`
- `apps/api/app/core/logging.py:125-170`
- `apps/api/app/core/logging.py:175-235`

### OK-3 — Middleware now binds correlation and emits request/error events

`CorrelationMiddleware` reads or mints `X-Correlation-Id`, binds log context, echoes the header, and emits `system.request` / `system.error`.

Evidence:

- `apps/api/app/middleware/correlation.py:79-99`
- `apps/api/app/middleware/correlation.py:107-140`

### OK-4 — Redactor coverage is much closer to canon

`apps/api/app/core/redactor.py` now includes canon PII keys and value-based patterns for JWT/email/bearer/tg-id/ipv4.

Evidence:

- `apps/api/app/core/redactor.py:40-82`
- `apps/api/app/core/redactor.py:86-136`

### OK-5 — Frontend has a real canonical logging API and shipper type

`lib/log/index.ts` has `logEvent`, `logStart`, `logSuccess`, `logFailure`, and `lib/log/shipper.ts` defines `CanonEnvelope` with the expected fields.

Evidence:

- `lib/log/index.ts:118-166`
- `lib/log/index.ts:170-197`
- `lib/log/shipper.ts:36-56`

---

## Blockers / major findings

## B1 — Event registry drift: canon, Python generated file, and TS generated file disagree

Severity: **blocker**

The generated files claim they are generated from `grace/canon/observability.xml`, but they contain events not present in the canon. Python and TS also disagree with each other.

Examples:

- Canon still has `payment.initiated`; Python/TS generated registry has `payment.intent_created` instead.
- Canon does not list horary/natal expanded events like `horary.question_created`, `natal.context_cache_hit`, etc., but generated files do.
- TS registry contains `chat.quota_increased`; Python registry does not.

Evidence:

- `grace/canon/observability.xml:193-299` — canonical events list does not contain horary/natal expanded events and still has `payment.initiated`.
- `apps/api/app/core/logging_events.py:18-88` — Python registry contains auth/profile/horary/natal/payment additions not present in canon.
- `lib/log/events.gen.ts:13-84` — TS registry contains `chat.quota_increased` while Python does not.

Impact:

- Closed registry is not closed.
- Codegen drift gate cannot be trusted.
- Frontend can emit events backend does not type-list, and both can emit events canon does not define.

Required fix:

1. Update `grace/canon/observability.xml` to include every event in both generated files.
2. Regenerate both artifacts from the canon, not by hand.
3. Add a CI/guardrail that fails if generated files differ from canon.
4. Make Python and TS generated files byte-equivalent in event names.

---

## B2 — Backend `log_event()` does not enforce the generated event registry

Severity: **blocker**

`apps/api/app/core/logging.py` contract says input event is from `LogEventName` and depends on `logging_events`, but the implementation accepts `event: str` and does not import/use `LogEventName`, `EVENT_PAYLOAD_TYPES`, or any runtime validation.

Evidence:

- Contract says registry dependency: `apps/api/app/core/logging.py:17-26`.
- Implementation accepts arbitrary string: `apps/api/app/core/logging.py:175-184`.
- Generated registry exists but is unused by `log_event()`: `apps/api/app/core/logging_events.py:18-88`, `apps/api/app/core/logging_events.py:162-185`.

Impact:

- Typos and unregistered business events pass silently.
- Payload schema is not enforced.
- Gate-11 intent is not implemented.

Required fix:

1. Change signature to `event: LogEventName` where static checking can help.
2. Add runtime validation for non-typechecked paths and `/api/_log` intake.
3. Validate payload required fields and enum values against generated metadata.
4. Add negative tests: unknown event must fail/reject.

---

## B3 — `system.request` logs can violate required `slice/module/block`

Severity: **blocker**

Canon marks `slice`, `module`, `block` required. Backend contextvars default these fields to empty strings, and middleware binds only `correlation_id`, `http_route`, `http_method`, `env`. Then middleware emits `system.request` without setting `slice/module/block`, so request logs can have empty required fields.

Evidence:

- Required fields in canon: `grace/canon/observability.xml:44-67`.
- Defaults are empty strings: `apps/api/app/core/logging.py:58-60`.
- Envelope uses those raw context values: `apps/api/app/core/logging.py:138-149`.
- Middleware bind does not set `slice/module/block`: `apps/api/app/middleware/correlation.py:89-95`.
- Middleware emits `system.request`: `apps/api/app/middleware/correlation.py:107-119`.

Impact:

- The most important universal log (`system.request`) is not guaranteed canonical.
- It breaks the user requirement: every log has slice/module/block.

Required fix:

For infra/system events, middleware should bind explicit technical context before emitting:

```python
bind_log_context(
    slice="W-1.6",
    module="M-OBSERVABILITY-CORRELATION",
    block="CORRELATION_MIDDLEWARE",
    ...
)
```

Or `log_event()` must require explicit meta override if context lacks required fields.

---

## B4 — `/api/_log` drops incoming frontend envelope fields and rebuilds the event

Severity: **blocker**

`/api/_log` accepts a `CanonEnvelope`, but `LogIntakeService` does not forward the envelope as-is. It rebuilds a new backend event via `core_log_event()` and only forwards event, level, msg, payload, correlation_id, service. It drops original frontend fields such as:

- `ts`
- `env`
- `service_version`
- `slice`
- `module`
- `block`
- `session_id`
- `user_id_hash`
- `error`
- `duration_ms`
- `http`
- `operation_id`
- `phase`

Evidence:

- API model accepts all fields: `apps/api/app/api/_log.py:52-79`.
- Service redacts then only forwards a subset: `apps/api/app/services/log_intake.py:97-108`.
- `_log_event()` only binds correlation/module/block/service, not incoming slice/block/module: `apps/api/app/services/log_intake.py:141-166`.

Impact:

- Frontend and backend envelopes are not byte-identical.
- Frontend `slice/module/block` is lost.
- Original event timestamp is lost.
- Frontend duration/http/error/session context is lost.
- Log warehouse cannot reconstruct the original user action accurately.

Required fix:

1. After validation/redaction, emit the **incoming redacted envelope** directly to stdout.
2. Do not rebuild it via backend `log_event()`.
3. If backend wants an intake meta-log, emit a separate `system.request` / `log_intake.accepted` event.

---

## B5 — `/api/_log` clears request context inside a request

Severity: **major risk**

`LogIntakeService._log_event()` binds context and then calls `clear_log_context()` after emitting frontend log. If this happens during `/api/_log` request processing, it can wipe middleware-bound request context before middleware emits its final `system.request` event.

Evidence:

- Middleware binds request context before route: `apps/api/app/middleware/correlation.py:89-99`.
- Service clears global contextvars after frontend event: `apps/api/app/services/log_intake.py:151-169`.
- Middleware emits request log after route returns: `apps/api/app/middleware/correlation.py:107-119`.

Impact:

- `/api/_log` request `system.request` can lose correlation/http context.
- Any later log in the same request after frontend event processing can be detached.

Required fix:

Use contextvar tokens and reset only values changed by the function, or avoid rebinding entirely by direct envelope emit.

---

## B6 — `/api/_log` validation is too weak for canon

Severity: **major risk**

The Pydantic model defaults required fields like `env`, `service`, `service_version`, `slice`, `module`, `block`, `correlation_id` instead of requiring non-empty values. Then `_validate_envelope()` checks only `ts`, `level`, `event`, `service`.

Evidence:

- Defaults for required fields: `apps/api/app/api/_log.py:55-64`.
- Validation checks only four fields: `apps/api/app/services/log_intake.py:122-139`.

Impact:

- Empty `slice/module/block/correlation_id` can be accepted.
- Event names are not checked against registry.
- Payload schemas are not checked.
- Canon required fields are effectively optional.

Required fix:

1. Use strict Pydantic model with required non-empty strings for all canon-required fields.
2. Validate enum values: `env`, `service`, `level`.
3. Validate event against generated registry.
4. Validate payload schema per event.
5. Reject unknown top-level fields if canon says envelope is closed.

---

## B7 — Frontend claims redaction before ship, but implementation does not redact before console or ship

Severity: **blocker for privacy**

Canon says redaction runs on both backend and frontend before any transport. Frontend logger contract also says it redacts PII before ship. But `logEvent()` puts raw payload into envelope, prints it to console, then enqueues it. There is no frontend redactor in this path.

Evidence:

- Canon requires redaction before any transport: `grace/canon/observability.xml:80-90`.
- Frontend contract says redacts PII before ship: `lib/log/index.ts:30-35`.
- Implementation assigns payload and immediately console.logs/enqueues: `lib/log/index.ts:151-162`.

Impact:

- PII can leak to browser console.
- PII can be shipped to `/api/_log` if backend intake misses or stores a pre-redacted copy.
- Tests may pass backend redactor canaries while frontend remains unsafe.

Required fix:

1. Implement frontend redactor generated from the same canon or shared static list.
2. Redact `payload`, `msg`, `error`, and safe-check `http` before console and before shipper.
3. In production, disable console transport unless explicitly enabled.
4. Add frontend canary tests for every PII key/pattern.

---

## B8 — Backend redaction does not cover `msg` and `http`, despite canon

Severity: **major risk**

Canon says value-based redaction applies to payload, msg, error.message, and error.stack, and key-based redaction applies to payload/error/http/msg policy. Backend `log_event()` redacts only `payload` and `error`, not `msg` or `http`.

Evidence:

- Canon redaction scope: `grace/canon/observability.xml:82-90`.
- Backend redaction only payload/error: `apps/api/app/core/logging.py:207-212`.

Impact:

- `msg="failed for user email@example.com"` would be emitted with raw email.
- `http` could leak unsafe fields if caller passes raw URL or headers.

Required fix:

1. Redact or reject `msg` if it matches PII patterns.
2. Redact `http` except explicit allowlisted keys.
3. Add tests for `msg` and `http` redaction, not only payload/error.

---

## B9 — Legacy/raw logging paths still exist and guardrails do not block them

Severity: **major risk**

The new logging API exists, but legacy logger is still exported, feature services still use raw `logging.getLogger(__name__)`, and `scripts/guardrails.sh` does not include the no-legacy-logging gates from the audit TZ.

Evidence:

- Deprecated legacy backend logger still exported: `apps/api/app/core/logging.py:265-292`.
- `main.py` still imports deprecated `logger`: `apps/api/app/main.py:54-60`.
- Deprecated frontend shim remains and maps arbitrary strings to `system.request`: `lib/logger.ts:3-28`.
- Guardrails backend/frontend do not include no-legacy logging/no-drift checks: `scripts/guardrails.sh:169-239`, `scripts/guardrails.sh:253-267`.

Impact:

- New code can continue using old logger and bypass event registry.
- P0/P1 can regress silently.
- “Generated from canon” drift can persist.

Required fix:

Add guardrails:

- fail on production `console.*` outside logging layer/tests;
- fail on `logging.getLogger(__name__)` in feature code;
- fail on `from app.core.logging import logger` outside explicit allowlist;
- fail if generated registry files do not match canon;
- fail if `log_event("unknown.event")` exists or runtime tests accept unknown event.

---

## B10 — Frontend production console logging is always on

Severity: **major privacy/noise risk**

`logEvent()` says “Console in dev”, but it does not check `env` or `NODE_ENV`; it always prints to `console.log` before shipper enqueue.

Evidence:

- Comment and unconditional console output: `lib/log/index.ts:156-162`.

Impact:

- Production console noise.
- Possible PII leak before frontend redaction is implemented.

Required fix:

Only console log when `env !== "prod"` or `NEXT_PUBLIC_GRACE_LOG_CONSOLE=true`, and only after redaction.

---

## B11 — `apiFetch()` logs duration inside payload, not top-level `duration_ms`

Severity: **minor / schema hygiene**

`apiFetch()` logs `duration_ms` inside payload for `ui.fetch_succeeded/failed`, but the canonical envelope already has a top-level `duration_ms` field.

Evidence:

- `apiFetch()` success/failure payload: `lib/api-fetch.ts:83-97`, `lib/api-fetch.ts:100-109`.
- `logEvent()` supports top-level duration meta: `lib/log/index.ts:121-128`, `lib/log/index.ts:151-153`.

Impact:

- Querying duration across backend/frontend becomes inconsistent.

Required fix:

Pass `duration_ms` via `meta.duration_ms`, keep payload for stable event-specific fields only.

---

## Suggested follow-up slices

### W-LOG-FIX-1 — Canon/registry/codegen drift

- Update `observability.xml` to include every event currently in generated Python/TS.
- Add missing `chat.quota_increased` to Python or remove from TS until canon declares it.
- Replace `payment.initiated` vs `payment.intent_created` mismatch.
- Add generator script or regenerate from the existing script if already present.
- Add drift gate to `scripts/guardrails.sh strict`.

### W-LOG-FIX-2 — Backend event validation

- Import and enforce `LogEventName` / generated event set.
- Validate payload fields.
- Reject unknown event names in tests.
- Make `slice/module/block/correlation_id` non-empty required at emit time.

### W-LOG-FIX-3 — `/api/_log` envelope preservation

- Strict Pydantic model with no defaults for required fields.
- Preserve incoming frontend envelope after redaction.
- Do not clear middleware context from service code.
- Add tests that input frontend `slice/module/block/duration/http/session_id` survives to emitted log.

### W-LOG-FIX-4 — Frontend redactor and console policy

- Add frontend redactor parity with canon.
- Redact before console and before ship.
- Disable console logs in prod by default.
- Add frontend redaction canary tests.

### W-LOG-FIX-5 — Guardrails

- `no-console-production` gate.
- `no-legacy-backend-logger` gate.
- `no-generated-registry-drift` gate.
- `log-envelope-required-fields` gate.
- `unknown-event-negative-test` gate.

---

## Acceptance for closing P0+P1

P0+P1 can be considered complete only when:

- [ ] Canon, Python generated registry, and TS generated registry have identical event sets.
- [ ] Unknown backend event names are rejected or fail type/static checks.
- [ ] Unknown frontend event names fail TS checks.
- [ ] Backend `system.request` always has non-empty `slice/module/block/correlation_id`.
- [ ] `/api/_log` rejects missing/empty required canon fields.
- [ ] `/api/_log` preserves frontend envelope fields after redaction.
- [ ] Frontend redacts before console and before ship.
- [ ] Backend redacts/checks `msg` and `http`, not only payload/error.
- [ ] Production console logging is off by default.
- [ ] Guardrails catch legacy logger usage and registry drift.
- [ ] Tests include negative cases, not only happy path envelope creation.

## Final note

The implementation is close enough to keep as a foundation, but not safe enough to close. The highest leverage fix is not feature retrofit yet; it is to lock the spine itself: canon ⇄ generated registries ⇄ emitters ⇄ intake ⇄ guardrails must become one mechanically enforced loop.
