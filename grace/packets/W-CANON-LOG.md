---
id: packet-w-canon-log
status: active
wave: W-CANON-LOG
last_review: 2026-05-25
---
# Controller Packet — W-CANON-LOG: Observability canon §8 (spec-only)

status: merged
phase: PHASE-1-MOCKED-PIPELINE
wave: W-CANON-LOG (inserted between W-1.1B and W-1.2 in development-plan.xml)
modules: M-CANON
canon: GRACE_CANON.md §8 (Observability) — this packet defines it
related-docs: grace/canon/observability.xml (the artifact under review)

---

## Why this wave exists

The original plan placed all logging concerns inside W-1.2 alongside Telegram
auth. Three forces push the spec out of any feature wave and into a prior
spec-only wave:

1. **Cross-stack invariant.** The log envelope must be byte-identical on
   backend and frontend. Defining it inside a feature wave means the first
   feature ships an envelope, and every later feature either conforms or
   diverges silently. By the time anyone notices, three packets have shipped
   incompatible payload shapes.
2. **Privacy is policy, not code.** The redaction list (`note`, `email`,
   `tg_user_id`, payment ids, birth data, …) is a closed contract between the
   product and its users. Encoding it inline in a logger module hides it from
   review. Encoding it in canon makes it greppable and patchable as a single
   surface.
3. **Business-events taxonomy.** `day.viewed`, `auth.tg_login_succeeded`, etc.
   are an open invitation to drift. `chat.message_send` vs `chat.message_sent`
   silently corrupts analytics. A closed registry compiled into TS unions and
   Python `Literal` types catches this at compile time. Owning the registry
   in canon makes additions explicit (canon patch) rather than incidental
   (someone added a string literal).

W-CANON-LOG ships only the canon artifact and the development-plan insertion.
No code under `apps/` or `lib/`. Implementation is split across two later
waves at the **end of PHASE-1**, after the feature skeletons exist:

- **W-1.6 LOGGING-SPINE** — envelope, correlation middleware, redactor,
  events codegen, gates 11/12/13, retrofit of already-merged endpoints.
- **W-1.7 LOG-SHIPPING** — `POST /api/_log`, frontend shipper, kill-switch.

Placing W-1.6 at the end of PHASE-1 (rather than splitting W-1.2) lets the
auth/day/calendar skeletons land first and then receive a single,
review-able instrumentation pass. PHASE-2 begins with the spine already in
place; gate-11 enforces the events registry from that point on.

## Scope of this packet

**In scope:**
- Author `grace/canon/observability.xml` covering: §8.1 goals, §8.2 envelope,
  §8.3 levels, §8.4 privacy (exhaustive redaction list + value patterns +
  allow-list + correlation-substitute), §8.5 closed events registry, §8.6
  sampling, §8.7 transports, §8.8 CI gates, §8.9 deferred items.
- Apply `grace/development-plan.canon-log.patch.md` to
  `grace/development-plan.xml`: insert W-CANON-LOG after W-1.1B; append W-1.6
  (LOGGING-SPINE) and W-1.7 (LOG-SHIPPING) after the existing W-1.5; add two
  drift-protection rules (canon-patch flow + per-wave events declaration).
- Optional one-line cross-link in `grace/requirements.xml` under NFR
  observability. No behavioural NFR is added in this PR.

**Out of scope (deferred to W-1.6):**
- Any code under `apps/api/app/core/logging.py`, `apps/api/app/core/redactor.py`,
  `apps/api/app/middleware/correlation.py`, or `lib/log/*`.
- The codegen scripts `scripts/codegen/events_from_canon.{py,ts}`.
- The CI workflow file `.github/workflows/observability.yml`.
- Retrofitting `print` / ad-hoc logs in already-merged endpoints to `log.event`.

**Out of scope (deferred to W-1.7):**
- `POST /api/_log` endpoint and the frontend shipper.
- Rate limiter and `GRACE_LOG_SHIPPING` kill-switch wiring.

## Decisions confirmed by controller

All five defaults from the design dialogue are accepted as canon. Recorded
here so future workers do not relitigate them inside their packets.

1. **Closed events registry.** Adding an event = canon patch
   `W-CANON-LOG-EXT-N`. Rationale: prevents typo drift
   (`message_send` vs `message_sent`); enables typed emitters; analytics
   joins stay sound. — **CONFIRMED.**
2. **Frontend shipping deferred to W-1.7.** W-1.6 emits to dev console and
   buffers in prod. No backend log loss; frontend events visible in dev only
   until W-1.7. — **CONFIRMED.**
3. **`tg_user_id` redaction + `user_id_hash` substitute.** Redact at every
   layer; substitute `user_id_hash = sha256(tg_user_id || GRACE_USER_SALT)[0:12]`
   for joins. `GRACE_USER_SALT` is a server-only secret env var introduced in
   W-1.6. — **CONFIRMED.**
4. **Sampling 1.0 in Phase 1.** Sampling change is a canon patch. —
   **CONFIRMED.**
5. **Sidecar (`apps/solarsage`) uses the same envelope.** `service="solarsage"`.
   Implementation lands when sidecar is touched (W-3.x); canon already covers
   it so no later canon patch is needed for sidecar onboarding. —
   **CONFIRMED.**

## Decision

- 1: closed events registry — **CONFIRMED**.
- 2: frontend shipping deferred to W-1.7 — **CONFIRMED**.
- 3: redact `tg_user_id` + `user_id_hash` via `GRACE_USER_SALT` — **CONFIRMED**.
- 4: sampling 1.0 in Phase 1 — **CONFIRMED**.
- 5: sidecar shares envelope — **CONFIRMED**.

## Acceptance (this PR)

- [x] `grace/canon/observability.xml` committed and well-formed XML.
- [x] Every section §8.1–§8.9 populated; no `TBD` left in the file.
- [x] §8.4 redaction list cross-checked against the data model: every PII /
      secret / payment / telegram / birth-data field appears as either a
      redact-key or a value pattern, or is explicitly on the allow-list with
      a reason.
- [x] §8.5 events registry covers every business event referenced in the
      current `grace/development-plan.xml` text (auth, profile, day,
      calendar, access, referral, payment, sidecar, scoring, llm, ui).
- [x] `grace/development-plan.xml` patched: W-CANON-LOG inserted after
      W-1.1B; W-1.6 and W-1.7 appended after W-1.5; two new
      drift-protection rules present (canon-patch flow, per-wave events
      declaration).
- [x] `grace/verification-matrix.md` gains the Observability row (cross-cutting section).
- [x] `GRACE_USER_SALT` (server-only secret per §8.4) declared in root `.env.example`
      with rotation note; `GRACE_LOG_DEBUG` / `GRACE_LOG_SHIPPING` toggles also stubbed.
- [x] CI runs lint-only on this PR. No code change under `apps/` or `lib/`.

## Drift protection (locked by this packet)

- This PR is the **only** place §8 of the canon may be authored without a
  canon patch. All future modifications to envelope, redaction list, or
  events registry are `W-CANON-LOG-EXT-N` micro-patches (one logical change
  per patch), landing **before** the consuming feature wave.
- W-1.6 / W-1.7 worker PRs may not modify `grace/canon/observability.xml`.
  If implementation reveals a missing field or event, the worker raises a
  question and the controller authors a `W-CANON-LOG-EXT-1` PR.
- From W-1.6 onward, every wave packet MUST list the business events it
  emits under "Business events emitted" and reference the §8.5 ids.
  Gate-11 fails PRs that emit unregistered events.
