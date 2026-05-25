# Patch to grace/development-plan.xml — W-CANON-LOG + W-1.6 + W-1.7

This is a controller-authored amendment, applied as a **separate prior PR**
before any worker PR for the logging spine. Per drift-protection rule "If
implementation requires changing requirements.xml or technology.xml, the
change is a separate prior PR" — the plan is a sibling of those files; same
rule applies. Canon is a sibling of the plan; same rule applies again —
hence the spec-only wave W-CANON-LOG runs before the implementation waves
W-1.6 / W-1.7.

## What changes

1. Insert a new spec-only wave **W-CANON-LOG "Observability canon §8"**
   between `W-1.1B` and the existing `W-1.2`. Spec-only. No code under
   `apps/` or `lib/` changes.
2. Append two new waves at the **end of PHASE-1**, after the existing W-1.5:
   - **W-1.6 LOGGING-SPINE** — backend logger, frontend logger, correlation
     middleware, redactor, events codegen, gates 11/12/13, retrofit of
     already-merged endpoints (auth, profile, day, calendar) to use
     `log.event(...)` in place of `print` / ad-hoc strings. No new endpoints,
     no DB changes.
   - **W-1.7 LOG-SHIPPING** — `POST /api/_log` endpoint, frontend shipper
     with batching + backoff + kill-switch (`GRACE_LOG_SHIPPING`), per-user
     rate limit by `user_id_hash`.
3. Add two `<rule>` entries to `<drift-protection>`:
   - canon-patch flow for any change to §8;
   - from W-1.6 onward, every wave packet must declare its emitted business
     events.

## Why end-of-PHASE-1 instead of splitting W-1.2

Splitting W-1.2 (auth) was rejected because:
- It would re-open already-scoped W-1.2 and force a packet re-issue;
- It would land an envelope before there are any business endpoints to
  emit events from, leading to a second instrumentation pass anyway when
  day/calendar arrive;
- Per drift-protection rule "Never edit two waves in the same PR", merging
  the spine into auth scope blurs the PR boundary.

Placing W-1.6 after W-1.5 means the auth/day/calendar/FE skeletons exist by
the time the spine lands; one review-able instrumentation pass touches
every call-site once. PHASE-2 begins with gates 11/12/13 already enforcing
the canon, which is the original goal (logging spine before W-2.x).

## XML inserted (between `</wave>` of W-1.1B and `<wave id="W-1.2">`)

```xml
<wave id="W-CANON-LOG" kind="spec-only">
  <title>Observability canon §8: envelope, redaction list, events registry</title>
  <modules>M-CANON</modules>
  <write-scope>grace/canon/observability.xml · grace/development-plan.xml (insertion of this wave + W-1.6 + W-1.7 only) · grace/packets/W-CANON-LOG.md</write-scope>
  <freeze-scope>everything under apps/ · everything under lib/ · packages/contracts/* · all UI components · all feature routes · grace/requirements.xml · grace/technology.xml · grace/knowledge-graph.xml</freeze-scope>
  <entry-criteria>W-1.1B closed.</entry-criteria>
  <exit-criteria>
    <criterion>grace/canon/observability.xml exists and is internally consistent (envelope §8.2, levels §8.3, privacy §8.4, events registry §8.5, sampling §8.6, gates §8.8 all populated).</criterion>
    <criterion>Redaction list in §8.4 is exhaustive: every PII / secret / payment / telegram / birth-data key from the data model is enumerated with redact-mode and rationale.</criterion>
    <criterion>Events registry in §8.5 covers every business event referenced anywhere in development-plan.xml at the time of merge. Each event has owner-wave and payload schema.</criterion>
    <criterion>Reviewer (controller) signs off in grace/packets/W-CANON-LOG.md under "## Decision".</criterion>
    <criterion>No code changes under apps/ or lib/. CI runs lint-only on this PR.</criterion>
  </exit-criteria>
  <deliverables>grace/canon/observability.xml · grace/packets/W-CANON-LOG.md · this insertion in development-plan.xml</deliverables>
</wave>
```

## XML appended (after the existing `</wave>` of W-1.5, still inside `<phase id="PHASE-1-MOCKED-PIPELINE">`)

```xml
<wave id="W-1.6">
  <title>Logging spine: envelope, correlation, redactor, events codegen, gates 11/12/13</title>
  <modules>M-OBSERVABILITY</modules>
  <write-scope>
    apps/api/app/core/logging.py ·
    apps/api/app/core/logging_events.py (codegen output, committed) ·
    apps/api/app/core/redactor.py ·
    apps/api/app/middleware/correlation.py ·
    apps/api/app/main.py (mount middleware + logger init only) ·
    apps/api/app/api/auth.py (retrofit to log.event) ·
    apps/api/app/api/profile.py (retrofit) ·
    apps/api/app/api/day.py (retrofit) ·
    apps/api/app/api/calendar.py (retrofit) ·
    lib/log/index.ts ·
    lib/log/redactor.ts ·
    lib/log/events.gen.ts (codegen output, committed) ·
    lib/log/correlation.ts ·
    lib/api/* (inject correlation header) ·
    scripts/codegen/events_from_canon.py ·
    scripts/codegen/events_from_canon.ts ·
    .github/workflows/observability.yml
  </write-scope>
  <freeze-scope>grace/canon/observability.xml (READ-ONLY) · packages/contracts/* · all DB models · all UI components · all alembic migrations</freeze-scope>
  <entry-criteria>W-CANON-LOG merged. W-1.5 merged.</entry-criteria>
  <exit-criteria>
    <criterion>Backend logger emits canonical envelope on stdout-json (prod) and stderr-pretty (dev).</criterion>
    <criterion>Frontend logger emits the same envelope; in prod it buffers (shipping arrives in W-1.7).</criterion>
    <criterion>Correlation middleware reads/mints X-Correlation-Id and round-trips it.</criterion>
    <criterion>Codegen produces logging_events.py and events.gen.ts byte-identically. CI fails on drift (gate-11).</criterion>
    <criterion>Redactor canary covers every key/pattern in §8.4. Sentinel never appears (gate-12).</criterion>
    <criterion>Every test-suite log line validates against the §8.2 envelope (gate-13).</criterion>
    <criterion>Existing endpoints emit their declared §8.5 events with correct payloads. No new endpoints in this wave.</criterion>
    <criterion>e2e: /day/today browser → backend log line carries the same correlation_id.</criterion>
  </exit-criteria>
  <deliverables>backend logger · frontend logger · correlation middleware · shared redactor · events codegen + committed artifacts · gates 11/12/13 in CI · retrofitted call-sites · 1 e2e correlation test</deliverables>
</wave>

<wave id="W-1.7">
  <title>Frontend → backend log shipping via POST /api/_log</title>
  <modules>M-OBSERVABILITY-SHIPPING</modules>
  <write-scope>
    apps/api/app/api/_log.py ·
    apps/api/app/services/log_intake.py ·
    apps/api/app/core/rate_limit.py ·
    lib/log/shipper.ts ·
    lib/log/index.ts (wire shipper behind GRACE_LOG_SHIPPING) ·
    .env.example
  </write-scope>
  <freeze-scope>grace/canon/observability.xml · core logger from W-1.6 · auth · profile · day/calendar · all DB models</freeze-scope>
  <entry-criteria>W-1.6 merged. Gates 11/12/13 stable in CI for at least one PR cycle.</entry-criteria>
  <exit-criteria>
    <criterion>POST /api/_log accepts batched envelopes, validates against §8.2, runs the same redactor, forwards to stdout-json. No log_intake DB table unless controller decides otherwise.</criterion>
    <criterion>Frontend shipper batches by 50 envelopes or 5s, with backoff and a hard kill-switch on GRACE_LOG_SHIPPING=off (default off in dev, on in prod).</criterion>
    <criterion>Endpoint enforces auth (session cookie) and per-user rate limit by user_id_hash from §8.4.</criterion>
    <criterion>Endpoint rejects malformed envelopes with 400 and emits log.intake_rejected (warn).</criterion>
    <criterion>e2e: a click in the web app produces a backend log line with matching correlation_id within 10s.</criterion>
    <criterion>Load: 1k envelopes/min for 5 min, &lt; 0.1% drops, no backend OOM.</criterion>
  </exit-criteria>
  <deliverables>shipping endpoint · client batcher with kill-switch · rate limiter · 6 tests · 1 load-test fixture</deliverables>
</wave>
```

## Drift-protection rules added (inside `<drift-protection>`)

```xml
<rule>Any change to grace/canon/observability.xml (envelope, levels, redact-list, events registry, sampling, gates) is a separate spec-only PR titled W-CANON-LOG-EXT-N and must merge before any wave that depends on the new shape. Workers MUST NOT add a business event by editing only their own packet — the registry in §8.5 is the closed source of truth and is enforced by gate-11.</rule>
<rule>Once W-1.6 is merged, every subsequent wave that adds endpoints, workers, or UI flows MUST list the business events it emits (from §8.5) in its packet under "Business events emitted" and assert them in tests. Gate-11 will fail PRs that emit unregistered events.</rule>
```

## phase-deps

No change. Logging spine lives entirely inside PHASE-1, so the existing
`PHASE-2-ACCESS requires PHASE-1-MOCKED-PIPELINE` dependency is sufficient
to gate PHASE-2 behind W-1.7.

## verification-matrix.md

Append a new row under "Cross-cutting verifications":

> **Observability**: gate-11 (events registry), gate-12 (redactor canary),
> gate-13 (envelope shape) enforced from W-1.6 onward on every PR. Source
> of truth: `grace/canon/observability.xml`. Any change to envelope,
> redaction list, or events registry is a canon patch (W-CANON-LOG-EXT-N)
> and must land before the consuming feature wave.

## Renumber map

None. Existing W-1.2 / W-1.3 / W-1.4 / W-1.5 keep their ids and bodies.
W-CANON-LOG is the only insertion in the middle of PHASE-1; W-1.6 and W-1.7
are appended at the end. No worker packets need renaming.
