# Verification Matrix

GRACE §13.E. Each row binds a use case to the modules it traverses, the gates it must pass, and the scenarios that prove it.

Columns:
- **UC** — use case id from `requirements.xml`.
- **Modules traversed** — every module on the happy path; if any is missing, gate fails.
- **Gates** — exit criteria from the wave; pass means measurable, not "looks good".
- **Scenarios** — concrete test inputs/outputs that auditor can run.

---

## UC-TG-AUTH · Telegram WebApp authentication

| Modules | Gates | Scenarios |
|---|---|---|
| M-AUTH-TG → `users` table | `sign_check` matches Telegram HMAC; expired payloads rejected; users row upserted exactly once per `telegram_id` | S1: valid initData → 200, session set, `users.count` +=1. S2: tampered hash → 401, no DB write. S3: replay after 24h → 401 if `auth_date` too old. |

## UC-PROFILE-CREATE · Onboarding

| Modules | Gates | Scenarios |
|---|---|---|
| M-AUTH-TG → M-PROFILE → `user_profiles` | All required fields present; lat/lon/tz resolved; redirect target = `/day/today` | S1: full payload → 201, profile readable via GET. S2: missing birth_time → 422 with `PROFILE_INCOMPLETE`. S3: birthday_location omitted → defaults to current_location. |

## UC-PROFILE-EDIT · Edit birth/location

| Modules | Gates | Scenarios |
|---|---|---|
| M-PROFILE → invalidation hooks | Edit of `birth_*` clears all 5 cache layers for the user; edit of `current_location` clears period/daily/semantic/today | S1: edit birth_time → assert `natal_snapshots`, `period_snapshots`, `daily_snapshots`, `semantic_layers`, `today_payloads` rows for user are gone. S2: edit current_location only → assert `natal_snapshots` retained, others cleared. |

## UC-ACCESS-CHECK · Access state

| Modules | Gates | Scenarios |
|---|---|---|
| M-ACCESS → `access_ledger` | Consumption order honored; counters accurate; preview returned when no entry | S1: 14d referral_bonus starts today, no subscription → day 0..13 = full, day 14 = preview. S2: 14d referral + 30d subscription → days 0..13 full from referral, days 14..43 full from subscription. S3: no entries → preview with reason `expired_access`. |

## UC-DAY-VIEW · `GET /api/day/:date` (PILOT)

| Modules | Gates | Scenarios |
|---|---|---|
| M-AUTH-TG → M-PROFILE → M-ACCESS → M-DAY-SERVICE → C-TODAY-PAYLOAD | Schema validation passes; meta has all version fields; cache hit on second call; p95 < 500ms (PHASE-1) | S1 (PHASE-1): valid auth + profile + date → TodayPayload validates; meta.cached=false on first call, true on second. S2: not onboarded → 422 `NOT_ONBOARDED`. S3: tomorrow's date in PHASE-2 with no access → preview payload with soft lock. S4: invalid date → 400 `INVALID_DATE`. S5 (PHASE-5): cold call traverses M-CALC-PIPELINE → M-NORMALIZATION → M-SCORING → M-SEMANTIC → M-LLM and persists each layer. |

## UC-DAY-NAV · Navigate days

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-DAY → M-WEB-API-CLIENT | URL changes to `/day/:nextDate` on arrow/swipe; scroll resets; payload refetches | E2E: tap right arrow on `/day/today` → URL updates, headline changes, week strip's active marker moves. |

## UC-CAL-NAV · Calendar

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-CALENDAR → M-CALENDAR | Allowed range = prev/curr/next month; disabled days non-clickable; tap → `/day/:date` | S1: GET `?month=2026-05` → grid of 3 months. S2: GET `?month=2030-01` → 400 `INVALID_DATE` (out of range). S3 e2e: tap on day 15 → URL `/day/2026-05-15`. |

## UC-WEEK-STRIP · 7-day strip

| Modules | Gates | Scenarios |
|---|---|---|
| M-DAY-SERVICE → C-TODAY-PAYLOAD.weekStrip | Exactly 3 distinct status values across the strip's domain; mapping per docs/04 §11 | S1: payload weekStrip[*].status ∈ {supportive, steady, tense}. S2: internal quality `high_contrast` maps to `tense`; `quiet` maps to `steady`. |

## UC-REFERRAL · 14 days for both

| Modules | Gates | Scenarios |
|---|---|---|
| M-AUTH-TG → M-REFERRAL → `referrals` + `access_ledger` | 2 ledger rows of 14 days created on new invitee; idempotent on repeat | S1: invitee signs up via referral link → both users have ledger row of 14d. S2: same invitee tries again → no second pair of rows. |

## UC-LOCKED-DAY · Preview/locked

| Modules | Gates | Scenarios |
|---|---|---|
| M-DAY-SERVICE (preview branch) → M-WEB-DAY locked state | Preview payload contains date, headline, partial flags, teaser, soft lock; CTAs present | S1: locked /day/2026-12-01 with no access → response has `access.state=preview`, soft lock with subscribe + invite CTAs. |

## UC-NATAL-VIEW · Versioned natal blocks

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-READINGS → C-NATAL-PAYLOAD | Unknown block.type does not crash render; routes /readings/natal and /readings/natal/[section] both render | S1: payload contains a block.type=`future_block` → renderer skips it, dev log emitted. S2: section route renders only that section's blocks. |

## UC-EVENING-CHECKIN · Checkin + closure

| Modules | Gates | Scenarios |
|---|---|---|
| M-CHECKIN → `evening_checkins` → composer integration | Upsert by (user_id, date); note never sent to LLM; yesterdayEcho appears only when checkin exists | S1: POST checkin twice → one row, second updates fields. S2: GET /api/day/today after yesterday's checkin → payload.yesterdayEcho.hadCheckin=true. S3: no checkin → yesterdayEcho omitted or `hadCheckin=false`. |

## UC-PAYMENTS · Subscription

| Modules | Gates | Scenarios |
|---|---|---|
| M-PAYMENTS → `access_ledger` | Successful payment writes subscription ledger row; consumed only after bonus | S1: user has 14d bonus + paid 30d → days 0..13 from bonus, days 14..43 from subscription. |

---

## Cross-cutting verifications

### Contract drift

For each contract in `technology.xml`:
- TS shape in `packages/contracts/*` matches Pydantic schema in `apps/api/app/schemas/*`.
- JSON Schema generated from each side compares equal.
- Test: `tests/contract_parity_test.py` regenerates and diffs.
- Authoring direction is set by W-1.1B. The "regenerates and diffs" step in `tests/contract_parity_test.py` runs the generator declared by the chosen option (A/B/C); the test fails if regeneration produces a non-empty diff against committed artifacts.

### Layer isolation (canon §11)

- Static check: backend code that imports anything from `lib/mocks/*` fails CI.
- Static check: frontend code that imports anything from `apps/api/*` or references `salience|supportScore|frictionScore|shadowRisk|totalSalience` outside `node_modules` fails CI.
- Static check: LLM prompt builder must source only from `SemanticLayer`; lint rule forbids passing raw `daily_snapshot` to prompt context.
- Static check: scoring consumers must read sphere definitions, dignity modifiers, aspect thresholds, activation rules, and convergence weights from `grace/canon/*.yml`; new hardcoded tables or top-N aspect cutoffs fail the scoring canon gate.

### SolarSage reference, scoring canon, and activation layer

| Modules | Gates | Scenarios |
|---|---|---|
| M-SOLARSAGE-REFERENCE-COLLECTOR → M-SIDECAR → M-SOLARSAGE-CLIENT | Golden fixture parity. The split service must match controller-approved reference collector JSON for planets, houses, aspects, lots, special points, fixed stars, and derived raw layers within declared tolerances. | S1: Vasiliy golden chart and target date regenerate byte-stable normalized JSON except timestamp fields. S2: A high-latitude chart uses the documented house-system fallback. S3: Chiron/Nodes/Lilith/Vertex fixed-star and aspect coverage remains present after service split. |
| M-SCORING-CANON → M-ACTIVATION-LAYER → M-SCORING | Canon YAML validates; scoring refuses to run without matching `scoring_canon_version`; activation evidence is included in debug/evidence artifacts but not exposed to frontend. | S1: changing `grace/canon/aspect_rules.v1.yml` changes `scoring_canon_version` and invalidates semantic/today caches. S2: two independent techniques pointing to the same planet/house produce convergence bonus. S3: one isolated rare factor cannot create a strong sphere claim by itself. |
| M-SCORING → M-SEMANTIC → M-LLM | LLM receives curated interpretation inputs only; no raw SolarSage, no score internals, no self-calculated astrology. | S1: prompt payload contains semantic themes and evidence IDs, not raw ephemeris JSON. S2: generated text may interpret facts but regex gate rejects language implying the LLM calculated positions/aspects itself. |

### GRACE orchestrator readiness

| Modules | Gates | Scenarios |
|---|---|---|
| M-GRACE-PROJECT-ADAPTER → M-GRACE-ORCHESTRATOR | `pnpm guardrails:orchestrator` validates project.yml, packet schema, verification profiles, role contracts, packet frontmatter, and legacy packet warnings. | S1: missing `agent_command_default` in `project.yml` fails. S2: non-portable verification command outside guardrails fails. S3: legacy packets warn but do not block until migrated. |
| M-GRACE-PACKET-SCHEMA → M-GRACE-ORCHESTRATOR | New executable packets must have allowed scope, frozen scope, verification, expected evidence, and escalation triggers before coder launch. | S1: packet without `Frozen / Out Of Scope` is rejected for new-packet mode. S2: planner output references `profile.frontend`; verifier resolves it to `pnpm guardrails:frontend`. |
| M-GRACE-ROLES → M-GRACE-ORCHESTRATOR | Every role prompt has Role, Inputs, Outputs, Hard Constraints, and machine-readable FINAL marker. | S1: coder role missing allowed-scope hard constraint fails role contract review. S2: reviewer verdict without `FINAL_GRACE_REVIEWER_VERDICT_JSON` fails artifact parse. |

### Version sanity

- On every CI run: load latest payload, ensure `meta.contract_version` matches frontend's expected; mismatch fails build.
- On every cache write: row carries the version it was computed with; reading code rejects rows whose version differs from current.

### Privacy

- Test: `evening_checkins.note` is not present in any structured log JSON.
- Test: prompt builder excludes `note` unless `prompt_version` is in note-aware allowlist.

### Observability (canon §8, enforced from W-1.6)

| Modules | Gates | Scenarios |
|---|---|---|
| M-CANON (`grace/canon/observability.xml`) → `apps/api/app/core/logging.py` (W-1.6) → `lib/log/*` (W-1.6) → `apps/api/app/api/_log.py` (W-1.7) | gate-11 events-registry parity (codegen byte-equal); gate-12 redactor canaries (every redact-key + every redact-pattern + allow-keys round-trip); gate-13 envelope shape (all CI log lines validate against §8.2 schema) | S1: emit `log.event("auth.tg_login_succeeded", {is_new_user: true})` → JSON line validates, `correlation_id` propagated end-to-end via `X-Correlation-Id`. S2: payload contains `tg_user_id=123456789` → serialized line shows `[redacted]`, sentinel grep finds zero hits. S3: payload contains `Bearer eyJabc.def.ghi` in a free-text msg → value-pattern replaces with `[redacted-jwt]`/`[redacted-bearer]`. S4: emit unregistered event name `auth.tg_login_OK` (typo) → mypy/tsc fail at compile, gate-11 backstop fails CI. S5: response carries the same `X-Correlation-Id` echo as the incoming request, or a freshly minted one if absent. |

### Performance gates

| Endpoint | Target | Phase introduced |
|---|---|---|
| `/api/day/:date` (cached) | p95 < 200ms | PHASE-1 |
| `/api/day/:date` (cold, full pipeline) | p95 < 20s | PHASE-5 |
| `/api/calendar` | p95 < 300ms | PHASE-1 |
| Sidecar `/v1/range` 31d | p95 < 3s | PHASE-3 |

---

## Testing Strategy

See `docs/ADR-001_Headless_Testing.md` for the complete testing strategy.

### Test Coverage Matrix

| UC | Backend Unit | Backend Integration | Frontend Unit | E2E | Visual |
|---|---|---|---|---|---|
| UC-TG-AUTH | test_telegram_hmac.py | test_auth_endpoints.py | - | auth.spec.ts | - |
| UC-PROFILE-CREATE | - | test_profile_endpoints.py | - | onboarding.spec.ts | onboarding-step*.png |
| UC-PROFILE-EDIT | - | test_profile_endpoints.py | - | - | - |
| UC-ACCESS-CHECK | - | test_access_service.py | useAccess.test.ts | - | - |
| UC-DAY-VIEW | test_normalization.py, test_scoring.py | test_day_endpoints.py | - | day-view.spec.ts | today-*.png |
| UC-DAY-NAV | - | - | - | day-view.spec.ts | - |
| UC-CAL-NAV | - | test_calendar_endpoints.py | - | calendar.spec.ts | calendar-3months.png |
| UC-WEEK-STRIP | - | test_day_endpoints.py | - | day-view.spec.ts | week-strip.png |
| UC-REFERRAL | - | test_referral_service.py | - | - | - |
| UC-LOCKED-DAY | - | test_day_endpoints.py | - | locked-day.spec.ts | locked-preview.png |

### Auth-First Principle

All integration and e2e tests go through Telegram auth:
- Backend: `authenticated_client` fixture (login → onboarding → request)
- Frontend: `authenticateAndOnboard` helper (inject Telegram WebApp API → auto auth)
- No backdoors, no test-mode without auth

### Visual Regression

Baseline screenshots stored in `apps/web/e2e/visual/__screenshots__/`:
- Today screen: supportive / steady / tense days
- Calendar: 3-month grid
- Locked day: preview + soft lock
- Onboarding: all 5 steps
- Profile: edit form

CI fails on visual diff > 0.1%, uploads diff artifacts.

---

## How to use this matrix

1. Before merging a wave PR, find every UC its scope touches.
2. For each UC row, every gate must have a passing test or measurement linked in PR.
3. If a gate cannot be met under the wave's freeze-scope, raise a question; do not silently expand.
4. After merge, the matrix row is updated with PR link and date passed.
