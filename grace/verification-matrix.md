# Verification Matrix

GRACE §13.E. Current-state verification matrix for SolarSage Astro after profile/access/day/calendar/natal/horary and test-stack updates.

Every row binds a use case to:

- **Modules traversed** — runtime modules on happy path.
- **Gates** — measurable acceptance criteria.
- **Scenarios** — concrete proofs/tests/evidence expected before acceptance.

---

## UC-TG-AUTH · Telegram WebApp authentication

| Modules | Gates | Scenarios |
|---|---|---|
| M-AUTH-TG → users → session cookie | Telegram initData HMAC validates; tampered/expired payloads rejected; user upsert is idempotent. | S1: valid initData → 200/session. S2: tampered hash → 401/no DB write. S3: stale auth_date → rejected. |

---

## UC-PROFILE-CREATE · Onboarding and profile creation

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-ONBOARDING → M-WEB-API → M-PROFILE → user_profiles | Required birth/current location fields accepted; city lat/lon/tz resolved; profile can be read after create. | S1: complete onboarding → profile row. S2: missing required field → 422. S3: birthday location omitted → accepted fallback/contract behavior. S4 E2E: onboarding flow completes and lands on `/day/today`. |

---

## UC-PROFILE-EDIT · Edit birth/current location

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-PROFILE → M-PROFILE → cache invalidation | Birth edits invalidate natal and downstream caches; current location edits invalidate period/daily/semantic/today, but keep natal where valid. | S1: edit birth_time → natal/period/daily/semantic/today cache rows cleared. S2: edit current location → downstream rows cleared, natal retained. |

---

## UC-ACCESS-CHECK · Access state

| Modules | Gates | Scenarios |
|---|---|---|
| M-ACCESS → access_ledger | Consumption order honored; access windows and preview states correct. | S1: referral_bonus 14d → days 0..13 full, day 14 preview. S2: referral + subscription → bonus consumed before subscription. S3: no entries → preview/expired reason. |

---

## UC-REFERRAL · Referral reward

| Modules | Gates | Scenarios |
|---|---|---|
| M-AUTH-TG → M-REFERRAL → referrals + access_ledger | Referral creates reward rows once; repeated invitee does not double grant. | S1: invitee signs up by referral link → inviter and invitee access reward. S2: same invitee repeats → no duplicate rows. |

---

## UC-DAY-VIEW · Today screen

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-DAY → M-WEB-API → M-DAY-SERVICE → M-PROFILE/M-ACCESS/M-CALC-PIPELINE/M-SEMANTIC/M-LLM as enabled | TodayPayload schema valid; access honored; cache behavior correct; frontend renders without calculating astrology. | S1: valid auth/profile/date → TodayPayload. S2: not onboarded → 422. S3: no access → preview/locked payload. S4: invalid date → error. S5: second call shows cache hit when cache layer enabled. |

---

## UC-DAY-NAV · Navigate days

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-DAY → router → M-WEB-API | URL/date state changes; week strip active marker and payload update; scroll behavior sane. | E2E: tap/swipe next day → URL and rendered day update. |

---

## UC-CAL-NAV · Calendar

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-CALENDAR → M-CALENDAR | Allowed range enforced; day click navigates; calendar payload validates. | S1: valid month → 3-month grid. S2: out-of-range month → error. S3 E2E: tap date → `/day/:date`. |

---

## UC-WEEK-STRIP · 7-day strip

| Modules | Gates | Scenarios |
|---|---|---|
| M-DAY-SERVICE → C-TODAY-PAYLOAD.weekStrip → M-WEB-DAY | Status values come from backend; frontend only renders. | S1: weekStrip statuses are from allowed set. S2: frontend does not compute dayStatus. |

---

## UC-NATAL-VIEW · Natal reading blocks

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-READINGS → M-NATAL-READING → C-NATAL-PAYLOAD | Versioned blocks render; unknown block types gracefully skipped. | S1: overview route renders. S2: section route renders. S3: unknown block.type does not crash. |

---

## UC-HORARY-QUOTA · Horary balance and credit ledger

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-HORARY → M-HORARY-API → M-HORARY-CREDIT-SERVICE → horary_credits/horary_credit_spends | New ledger model only; no HoraryQuota/questions_used/questions_limit/left/nextInDays as primary balance. Weekly-free does not accumulate; paid persists; spend order deterministic. | S1: active access creates current subscription_weekly_free lazily only for current access week. S2: unused weekly-free expires at access_week_end. S3: paid credits persist after weekly expiry. S4: spend order weekly-free → expiring referral/gift/adjustment → paid. S5: no spendable credits → 402 NO_HORARY_CREDITS. |

---

## UC-HORARY-SUBMIT · Create horary question

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-HORARY → M-HORARY-API → M-HORARY-SERVICE → M-HORARY-CREDIT-SERVICE → M-HORARY-ENGINE/M-LLM | Requires spendable credit and usable question place. Idempotency prevents double spend/generation. Request hash includes text/category/time/timezone/place/name. Generation starts only after commit. | S1: valid paid credit + questionLat/questionLon → 201, one spend row. S2: same idempotencyKey + same full payload → same question, no second spend, no second generator. S3: same key + changed clientLocalTime/timezone/place → 409. S4: no place coordinates → frontend submit disabled. |

---

## UC-HORARY-ANSWER · Horary processing and answer view

| Modules | Gates | Scenarios |
|---|---|---|
| M-HORARY-SERVICE → M-HORARY-ENGINE → M-LLM → horary_answers → M-WEB-HORARY | Backend owns verdict/context; LLM narrates only. Late/stale generator cannot overwrite failed/refunded/answered question. Answer shows question location name when available. | S1: processing → answered with verdict/confidence/blocks. S2: generation failure refunds paid or restores weekly-free only if access-week active. S3: late generator after failed/refunded skips answer save. S4: answer UI displays place of calculation. |

---

## UC-HORARY-UX-LOCATION · Horary time/place/category UX

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-HORARY → M-WEB-PROFILE → CityPicker/cities/geo helpers | Form shows time and place; default place may come from profile current location; user can change place; selected city timezone syncs; submit disabled without coordinates; premium progress state used. | S1: profile current city/lat/lon/tz → form shows place and can submit. S2: no coordinates → red warning and disabled CTA. S3: changing city updates timezone when city.timezone exists. S4: category chip switches love → career. S5: progress shows orbit/steps and long-running copy. |

---

## UC-EVENING-CHECKIN · Checkin and closure

| Modules | Gates | Scenarios |
|---|---|---|
| M-CHECKIN → evening_checkins → Today composer | Upsert by user/date; private note not leaked to logs/LLM by default; yesterdayEcho appears only when applicable. | S1: POST twice → one row updated. S2: GET today after yesterday checkin → echo present. S3: note absent from logs/prompt unless note-aware prompt_version. |

---

## UC-SOLARSAGE-PARITY · Sidecar/reference parity

| Modules | Gates | Scenarios |
|---|---|---|
| M-SOLARSAGE-REFERENCE-COLLECTOR → M-SIDECAR → M-SOLARSAGE-CLIENT | Sidecar outputs match golden fixtures within declared tolerances; high-latitude fallback documented. | S1: golden Vasiliy fixture parity. S2: normal-latitude fixture parity. S3: high-latitude house-system fallback behavior stable. |

---

## UC-SCORING-SEMANTIC-LLM · Real interpretation pipeline

| Modules | Gates | Scenarios |
|---|---|---|
| M-SCORING-CANON → M-ACTIVATION-LAYER → M-SCORING → M-SEMANTIC → M-LLM | Canon YAML validates; scoring refuses hidden constants; prompt receives curated context only. | S1: changing canon YAML invalidates downstream caches. S2: convergence bonus requires multiple independent evidence sources. S3: prompt payload has semantic evidence, not raw ephemeris/internal scores. |

---

## UC-GRACE-ORCHESTRATOR · Agent packet execution

| Modules | Gates | Scenarios |
|---|---|---|
| M-GRACE-PROJECT-ADAPTER → M-GRACE-PACKET-SCHEMA → M-GRACE-ROLES → M-GRACE-VERIFICATION-PROFILES | Project adapter and packet schema are machine-readable; roles have parseable final markers; verification profiles map to portable commands. | S1: `pnpm guardrails:orchestrator` validates. S2: packet missing Frozen/Out Of Scope rejected for new-packet mode. S3: reviewer output without final JSON marker fails parse. |

---

# Cross-cutting verification gates

## Contract drift

- Run contracts generation/check after any Pydantic schema change.
- `packages/contracts/_generated.ts` must be byte-stable after regeneration.
- New frontend payload imports should use `packages/contracts` barrel unless a local runtime zod schema is intentionally needed.

## Layer isolation

- Frontend must not import backend modules.
- Backend must not import frontend mocks.
- Frontend must not calculate astrology, dayStatus, scores, horary verdicts, or access/credit spend logic.
- LLM prompt builder must not receive raw SolarSage or internal score fields.

## Horary anti-regression grep gate

These must not appear as live primary horary balance logic:

```bash
grep -R "HoraryQuota\|questions_used\|questions_limit\|left\|nextInDays" apps/api lib components packages/contracts \
  --exclude-dir=.venv --exclude-dir=__pycache__ --exclude-dir=node_modules
```

Allowed hits: historical docs/work review files only.

## Privacy

- Telegram IDs, auth tokens, birth data, location data, and private notes must be redacted from structured logs according to observability canon.
- Evening checkin free-text note is not sent to LLM unless prompt_version is explicitly note-aware.

## Performance gates

| Endpoint / flow | Target |
|---|---|
| `/api/day/:date` cached | p95 &lt; 200ms when cached layer enabled |
| `/api/day/:date` cold full pipeline | p95 &lt; 20s when real pipeline enabled |
| `/api/calendar` | p95 &lt; 300ms |
| Sidecar `/v1/range` 31d | p95 &lt; 3s |
| Horary quota | p95 &lt; 300ms |
| Horary create question | p95 &lt; 1s before async generation |

---

# Test coverage matrix

Current reported test status after horary follow-up:

```text
Backend: 237 tests green
Frontend: 467 tests green
```

| UC | Backend Unit | Backend Integration | Frontend Unit/Component | E2E/Visual |
|---|---|---|---|---|
| UC-TG-AUTH | test_telegram_hmac.py | test_auth_endpoints.py | - | auth/telegram auth specs if enabled |
| UC-PROFILE-CREATE | - | test_profile_endpoints.py | onboarding reducer/components | onboarding specs/visuals |
| UC-PROFILE-EDIT | - | test_profile_endpoints.py | profile components | profile visual if enabled |
| UC-ACCESS-CHECK | test_access_service.py | endpoint coverage where applicable | access hook/lib tests | locked-day specs |
| UC-DAY-VIEW | normalization/scoring tests | test_day_endpoints.py | day components where present | day-view/visual specs |
| UC-CAL-NAV | - | test_calendar_endpoints.py | calendar components | calendar specs/visuals |
| UC-NATAL-VIEW | schema/block tests | readings endpoints where present | block renderer tests | readings navigation specs |
| UC-HORARY-QUOTA | test_horary_credit_service.py | test_horary_endpoints.py | quota bar tests if present | manual/QA acceptable for MVP |
| UC-HORARY-SUBMIT | test_horary_credit_service.py | test_horary_endpoints.py | horary form/time-place tests | manual/QA acceptable for MVP |
| UC-HORARY-ANSWER | horary service/engine tests | test_horary_endpoints.py | answer/progress tests | manual/QA acceptable for MVP |
| UC-EVENING-CHECKIN | yesterday/checkin tests | checkin endpoint tests | - | - |
| UC-SOLARSAGE-PARITY | apps/solarsage/tests/test_parity.py | sidecar health/API tests | - | - |
| UC-GRACE-ORCHESTRATOR | scripts/check_orchestrator_contracts.py | guardrails scripts | - | - |

---

# How to use this matrix

1. Before merging a wave PR, find every UC its scope touches.
2. For each UC row, every gate must have passing tests, grep evidence, or explicit controller acceptance.
3. If a gate cannot be met under the wave scope, raise it as a question; do not silently expand scope.
4. After merge, update this matrix when the runtime behavior or acceptance gates change.
