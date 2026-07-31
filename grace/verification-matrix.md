# Verification Matrix

GRACE §13.E. Current-state verification matrix for Solar Sage after legacy removal and GRACE slice coverage audit.

Every row binds a use case or adoption slice to:

- **Modules traversed** — runtime or GRACE modules on the happy path.
- **Gates** — measurable acceptance criteria.
- **Scenarios** — concrete proofs/tests/evidence expected before acceptance.

---

## GRACE slice adoption gates

These gates apply before broad autonomous business-feature work.

| Slice | Modules | Gates | Scenarios |
|---|---|---|---|
| `SLICE-SHELL-NAVIGATION` | `M-WEB-SHELL` | App shell and TabBar are mapped to Shell/Navigation; title/aria-current/accessibility behavior remains stable. | S1: `python3 scripts/grace/coverage_audit.py --check` sentinel keeps `components/today/tab-bar.tsx -> SLICE-SHELL-NAVIGATION`. S2: TabBar tests remain green after nav edits. |
| `SLICE-TODAY-CALENDAR` | `M-WEB-TODAY-CALENDAR` | Today/Calendar files touched by a packet have AI_HEADER, MODULE_CONTRACT, MODULE_MAP, blocks where useful, and nearby tests. | S1: coverage audit JSON shows changed files in this slice. S2: Today/Calendar unit/component tests pass. S3: frontend does not calculate astrology/status logic. |
| `SLICE-FRONTEND-API-FACADES` | `M-WEB-API` | API facades use generated contracts/barrel where applicable and keep frontend error handling thin. | S1: API facade changes have local tests or caller evidence. S2: no hand-authored server payload drift. |
| `SLICE-CONTRACTS` | `M-CONTRACTS` | Pydantic remains source of truth; generated TS contracts are deterministic. | S1: schema changes regenerate contracts. S2: generated files are not manually edited. S3: frontend imports through `packages/contracts` for new payload types. |
| `SLICE-BACKEND-API-ROUTERS` | `M-BACKEND-API` | Routers stay thin and delegate product decisions to services. | S1: endpoint tests cover changed routes. S2: no long business branch added to router. |
| `SLICE-BACKEND-SERVICES` | `M-BACKEND-SERVICES` | Service logic has contracts, visible side effects, declared emitted logs where logging exists, and tests. | S1: touched service has module/function contracts. S2: service tests or endpoint integration tests pass. S3: side effects are named. |
| `SLICE-DB-MODELS-MIGRATIONS` | `M-DB` | DB changes are explicit and isolated; migrations are not touched by unrelated UI/API packets. | S1: model/migration changes require DB slice in packet scope. S2: migration tests/manual evidence included when schema changes. |
| `SLICE-HORARY-READINGS` | `M-WEB-HORARY-READINGS` | Readings/horary UI changes preserve block rendering and graceful unknown-block behavior. | S1: block renderer tests pass. S2: answer/progress/history UI has component or manual evidence. |
| `SLICE-PROFILE-ONBOARDING` | `M-WEB-PROFILE-ONBOARDING` | Profile/location/onboarding flows preserve city/timezone/location contract behavior. | S1: profile/onboarding tests pass. S2: changed city/location behavior has explicit evidence. |
| `SLICE-LOGGING-SPINE` | `M-LOGGING-SPINE` | Logging claims are reconciled with actual code and audit detection. | S1: coverage audit detects intended canonical logging patterns. S2: files with logs declare emitted logs in MODULE_CONTRACT. S3: private fields are redacted or not logged. |
| `SLICE-GUARDRAILS-TOOLING` | `M-GUARDRAILS` | Coverage audit, GRACE linters, docs checks, and orchestrator checks remain deterministic. | S1: `coverage_audit.py --check` passes. S2: sentinel mappings pass. S3: report and JSON are generated from one data object. |
| `SLICE-ORCHESTRATOR-ADAPTER` | `M-GRACE-PROJECT-ADAPTER` | Project adapter, roles, schema, verification profiles remain machine-readable. | S1: `pnpm guardrails:orchestrator` or equivalent check passes. S2: packet schema and role docs parse. |

---

## UC-TG-AUTH · Telegram WebApp authentication

| Modules | Gates | Scenarios |
|---|---|---|
| M-BACKEND-API → M-BACKEND-SERVICES → users/session | WebApp init data validates; invalid payloads rejected; user upsert is idempotent. | S1: valid init data → 200/session. S2: tampered payload → rejected/no DB write. S3: stale auth_date → rejected. |

---

## UC-PROFILE-CREATE · Onboarding and profile creation

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-PROFILE-ONBOARDING → M-WEB-API → M-BACKEND-API/M-BACKEND-SERVICES → M-DB | Required birth/current location fields accepted; city lat/lon/tz resolved; profile can be read after create. | S1: complete onboarding → profile row. S2: missing required field → 422. S3: birthday location omitted → accepted fallback/contract behavior. S4: onboarding flow lands on Today. |

---

## UC-PROFILE-EDIT · Edit birth/current location

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-PROFILE-ONBOARDING → M-WEB-API → M-BACKEND-SERVICES → M-DB | Birth edits invalidate natal/downstream caches; current location edits invalidate period/daily/semantic/today where relevant. | S1: edit birth_time → downstream invalidation evidence. S2: edit current location → downstream rows cleared, natal retained where valid. |

---

## UC-DAY-VIEW · Today screen

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-TODAY-CALENDAR → M-WEB-API → M-BACKEND-API/M-BACKEND-SERVICES → M-CONTRACTS | TodayPayload schema valid; access honored; cache behavior correct; frontend renders without calculating astrology. | S1: valid auth/profile/date → TodayPayload. S2: not onboarded → contract error. S3: no access → preview/locked payload. S4: invalid date → error. S5: cache hit where cache layer enabled. |

## UC-TODAY-CONVERGENCE-W1 · W1 deterministic convergence canon

| Modules | Gates | Scenarios |
|---|---|---|
| M-SIDECAR-CALCULATION → M-TODAY-CONVERGENCE-CANON → M-TODAY-REPLAY → M-CONTRACTS | New `state × dayTone × contentState` envelope is orthogonal; C1 hero requires a rare anchor plus an independent direct witness; background and transitive bridges cannot inflate it; sphere projection is primary + at most one secondary per physical group; unknown mapping fails closed; formula/calculation versions participate in lineage. | S1: `test_convergence_canon.py`, `test_convergence_mutation_fixtures.py`, `test_sphere_mapping_delta.py`. S2: direct replay parity on owner fixture. S3: 120-chart population aggregate is monitoring evidence, not a quota. S4: `CALCULATION_VERSION=ss-calc-1.3.0` parity/sect/health tests pass. S5: freeze delta-attestation records old/new source fingerprints. |

## UC-TODAY-CONVERGENCE-W2-UNITS · canonical physical units

| Modules | Gates | Scenarios |
|---|---|---|
| M-TODAY-CONVERGENCE-UNITS → M-TODAY-CONVERGENCE-CANON | Frozen canon and the versioned theme registry are loaded strictly; physical identity is producer-independent and window-aware; aspect/event-class/orb/target/data-quality failures are typed and fail closed; eligibility nesting and background exclusion hold; structural lunar events remain excluded until a canonical significance rule exists; canonical theme mappings project into immutable `theme_keys` without grouping, tone, or adapter behavior. | S1: `cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/test_today_convergence_canon.py tests/test_today_convergence_units.py -q`, including registry parity and malformed-copy rejection. S2: producer parity and prefix stripping preserve one `evt_v1_` ID; changing technical annotations changes only the mapped theme tuple; unknown mappings return `()`. S3: `python -m ruff check` on the four packet Python files, `python3 scripts/grace_lint.py apps/api/app --quiet`, `bash scripts/grace/check-markers.sh`, and `git diff --check` pass. |

## UC-TODAY-CONVERGENCE-W2-LEDGER · canonical ledger, deduplication, and DayDelta

| Modules | Gates | Scenarios |
|---|---|---|
| M-TODAY-CONVERGENCE-LEDGER → M-TODAY-CONVERGENCE-UNITS → M-TODAY-CONVERGENCE-CANON | Pure immutable ledger deduplicates only by `canonical_event_id`; frozen producer precedence selects enrichment without changing identity; provenance is a sorted union; malformed rows and unknown producers fail closed into audit; audit-only units stay non-public; DayDelta matches exact semantic keys only. Grouping, hero, tone, projection, and adapters remain out of scope. | S1: `cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/test_today_convergence_canon.py tests/test_today_convergence_units.py tests/test_today_convergence_ledger.py -q`. S2: activation/day_signal dedup, permutation parity, deterministic same-producer conflict, immutable audit, malformed-row aggregation, and background/time-sensitive preservation. S3: exact semantic-key upgrade passes; duplicate and unmatched trigger counts are deterministic; planet-name trigger does not upgrade. S4: packet Ruff, `grace_lint`, marker, and `git diff --check` gates pass. |

## UC-TODAY-CONVERGENCE-W2-GROUPS · direct stars, C1 hero, and group spheres

| Modules | Gates | Scenarios |
|---|---|---|
| M-TODAY-CONVERGENCE-GROUPS → M-TODAY-CONVERGENCE-LEDGER → M-TODAY-CONVERGENCE-UNITS → M-TODAY-CONVERGENCE-CANON | Pure immutable direct-star groups use only shared target/theme links; public members are evidence-eligible and non-background; distinct drivers determine group validity; C1 requires a rare target-eligible anchor plus a direct independent confirmer; spheres project once per physical group with majority/anchor/canonical tie-break and at most one secondary. Tone, presentation, and adapters remain out of scope. | S1: `cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/test_today_convergence_canon.py tests/test_today_convergence_units.py tests/test_today_convergence_ledger.py tests/test_today_convergence_groups.py -q`. S2: direct-star bridge-negative, background/ineligible exclusion, producer dedup, distinct-driver, hero fast/lot/direct-confirmation negatives, and immutable deterministic records. S3: per-group sphere majority, tie-break, secondary threshold/cap, input permutation, stable group IDs, duplicate-ledger-ID typed error. S4: packet Ruff, `grace_lint`, markers, and `git diff --check` pass. |

## UC-TODAY-CONVERGENCE-W2-TONE · frozen unit/group/day tone policy

| Modules | Gates | Scenarios |
|---|---|---|
| M-TODAY-CONVERGENCE-TONE → M-TODAY-CONVERGENCE-GROUPS → M-TODAY-CONVERGENCE-LEDGER → M-TODAY-CONVERGENCE-CANON | Strict canon exposes the exact `tone-candidate-0.1` block; unit/group coefficients are canon-driven; day tone uses aware IANA local-date freshness, distinct drivers, and selected-only legacy audit; no selector, wire, or adapter behavior. | S1: `cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/test_today_convergence_canon.py tests/test_today_convergence_units.py tests/test_today_convergence_ledger.py tests/test_today_convergence_groups.py tests/test_today_convergence_tone.py -q`. S2: timezone boundary, supporting context, fast/mixed sparse regressions, hero/two-driver thresholds, weighted supportive+tense mixed balance, and selection-independent day tone. S3: malformed tone canon and foreign/duplicate references fail closed; output and trigger order are permutation-deterministic; internal `steady` group polarity is not wire behavior. S4: packet Ruff, `grace_lint`, markers, and `git diff --check` pass. |

---

## UC-DAY-NAV · Navigate days

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-SHELL → M-WEB-TODAY-CALENDAR → router → M-WEB-API | URL/date state changes; active marker and payload update; scroll behavior sane. | S1: tab/day navigation preserves title/aria-current. S2: next day changes URL and rendered payload. |

---

## UC-CAL-NAV · Calendar

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-TODAY-CALENDAR → M-WEB-API → M-BACKEND-API/M-BACKEND-SERVICES | Allowed range enforced; day click navigates; calendar payload validates. | S1: valid month → grid. S2: out-of-range month → error. S3: tap date → Today/date route. |

---

## UC-NATAL-VIEW · Natal reading blocks

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-HORARY-READINGS → M-CONTRACTS | Versioned blocks render; unknown block types gracefully skipped. | S1: overview route renders. S2: section route renders. S3: unknown block type does not crash. |

---

## UC-HORARY-QUOTA · Horary balance and ledger

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-HORARY-READINGS → M-WEB-API → M-BACKEND-API/M-BACKEND-SERVICES → M-DB | Ledger model only; legacy quota counters are not revived; spend order deterministic. | S1: active access creates current week free unit lazily. S2: paid units persist. S3: spend order deterministic. S4: no spendable units → product error. |

---

## UC-HORARY-SUBMIT · Create horary question

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-HORARY-READINGS → M-WEB-API → M-BACKEND-SERVICES → M-SCORING-SEMANTIC-LLM | Requires usable question place; idempotency prevents double spend/generation; generation starts after commit. | S1: valid question/place → one question and one spend. S2: same key and same payload → existing question. S3: same key and changed time/place → conflict. S4: no place coordinates → submit disabled. |

---

## UC-HORARY-ANSWER · Horary processing and answer view

| Modules | Gates | Scenarios |
|---|---|---|
| M-BACKEND-SERVICES → M-SCORING-SEMANTIC-LLM → M-WEB-HORARY-READINGS | Backend owns verdict/context; narration is strict and validated; late/stale generator cannot overwrite final state. | S1: processing → answered. S2: generation failure handles spend restoration/refund policy. S3: late generator skip. S4: answer UI displays place when available. |

---

## UC-SOLARSAGE-PARITY · Sidecar/reference parity

| Modules | Gates | Scenarios |
|---|---|---|
| M-SIDECAR-CALCULATION → M-BACKEND-SERVICES | Sidecar outputs match golden fixtures within declared tolerance; fallback behavior documented. | S1: golden fixture parity. S2: normal-latitude fixture parity. S3: high-latitude fallback stable. |

---

## UC-SCORING-SEMANTIC-LLM · Interpretation pipeline

| Modules | Gates | Scenarios |
|---|---|---|
| M-SCORING-SEMANTIC-LLM → M-CONTRACTS | Canon validates; prompt receives curated context only; frontend receives payload, not internals. | S1: canon change invalidates downstream. S2: prompt payload has semantic evidence only. S3: LLM output validates strict schema. |

---

## UC-GRACE-ORCHESTRATOR · Agent packet execution

| Modules | Gates | Scenarios |
|---|---|---|
| M-GRACE-PROJECT-ADAPTER → M-GUARDRAILS → M-TESTS | Project adapter and packet schema are machine-readable; roles parse; coverage audit remains stable. | S1: `python3 scripts/grace/coverage_audit.py --check`. S2: orchestrator guardrails pass or known pre-existing failures are isolated. S3: packet missing scope/frozen-scope rejected where required. |

---

## UC-PROMO-REDEEM · Named promo campaign preview and redemption

| Modules | Gates | Scenarios |
|---|---|---|
| M-WEB-SHELL (promo gate) → M-WEB-API (promo client) → M-BACKEND-API (promo router) → M-BACKEND-SERVICES (promo campaign) → M-DB | Raw token exists only at request/CLI boundary (DB stores SHA-256 hash); redemption is atomic (one commit; domain/unexpected failure rolls back grants, counter and redemption); duplicate redeem is 409 ALREADY_REDEEMED without second grants; PROFILE_INCOMPLETE spends nothing; privacy: no token/display_name in logs. | S1: `apps/api/tests/test_promo_campaign_service.py` (domain incl. failure invariants). S2: `apps/api/tests/test_promo_api.py` (status/code matrix, safe 400, no-store, sentinel privacy). S3: `PROMO_TEST_POSTGRES_URL=... python -m pytest apps/api/tests/test_promo_postgres_acceptance.py` (concurrency proofs on real PostgreSQL). S4: gate/sheet vitest (`PromoCampaignGate`, `PromoConfirmationSheet`, `promo-client`). S5: operator CLI contract (`test_promo_admin_cli.py`). |

---

# Cross-cutting gates

## Contract drift

- Any Pydantic schema change must regenerate/check TypeScript contracts.
- `packages/contracts/_generated.ts` must not be hand-edited.
- New frontend payload imports should use `packages/contracts` unless a local runtime schema is explicitly justified.

## Layer isolation

- Frontend must not import backend modules.
- Backend must not import frontend mocks.
- Frontend must not calculate astrology, dayStatus, scores, verdicts, or access/spend logic.
- LLM prompt builder must not receive raw sidecar output or internal score fields unless explicitly approved by the relevant slice.

## Logging and privacy

- Logging assumptions must be validated by `SLICE-LOGGING-SPINE` before claiming full coverage.
- Files with logging should declare emitted logs in MODULE_CONTRACT.
- Sensitive profile/location/free-text fields are not logged or sent to LLM by default.

## Performance gates

| Flow | Target |
|---|---|
| `/api/day/:date` cached | p95 < 200ms when cache layer enabled |
| `/api/day/:date` cold full pipeline | p95 < 20s when real pipeline enabled |
| `/api/calendar` | p95 < 300ms |
| sidecar 31d range | p95 < 3s |
| horary quota | p95 < 300ms |
| horary create question | p95 < 1s before async generation |

---

# How to use this matrix

1. Map the feature to slices first.
2. Use the slice gate table to choose mandatory checks.
3. Use the UC rows to add product-specific evidence.
4. Run the smallest sufficient verification profile, then escalate only if risk demands it.
5. Update this matrix only when runtime behavior, slice ownership, or gates change.
