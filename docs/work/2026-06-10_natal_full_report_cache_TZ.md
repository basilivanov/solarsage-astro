# TZ: W-NATAL-FULL-REPORT-CACHE

Date: 2026-06-10
Status: ready for architect/coder packetization
Supersedes/extends: `docs/work/2026-06-09_natal_preview_mvp_TZ.md`, `docs/17_Natal_landing_and_generation_TZ.md`
Related code areas: `apps/api/app/api/natal.py`, `apps/api/app/services/natal_service.py`, `apps/api/app/services/today_service.py`, `apps/api/app/clients/solarsage_client.py`, `apps/api/app/services/normalization_service.py`, `apps/api/app/services/scoring_service.py`, `apps/api/app/db/models.py`, `lib/api/natal.ts`, `lib/contracts/natal.ts`, `app/(grace)/readings/natal/*`

## 1. Goal

Implement the production-ready natal backend and frontend integration layer:

1. Persist a reusable deterministic `NatalContext` for each user/profile version.
2. Make the daily pipeline reuse cached natal context instead of recalculating natal chart every day.
3. Generate full natal report sections with an LLM from deterministic chart facts only.
4. Persist generated report sections so paid/generated content is stable and reproducible.
5. Remove production dependency on mocked/demo natal report flows.
6. Align backend and frontend contracts around one source of truth.

User-facing value:

> User enters birth data once. The system calculates the chart once, reuses it everywhere, and can generate a full personal natal report without inventing astrological facts in the LLM layer.

## 2. Current state and key decision

Current preview MVP correctly proved that backend can calculate real natal-derived preview data through the SolarSage sidecar. The daily screen also already calls natal calculation internally as part of building the daily payload.

However, current daily flow treats natal chart as an intermediate input and caches only the final daily response. That is acceptable for the demo/MVP day screen, but not enough for full natal product.

Decision:

- Keep daily payload cache.
- Add separate persistent natal context cache.
- Refactor day calculation to call `get_or_build_natal_context(user)` and combine it with fresh transits.
- Full natal report must be generated only from this deterministic cached natal context.

Do not ask the LLM to calculate planets, houses, aspects, dignities, scores, or configurations. LLM only writes human-readable text from already calculated JSON facts.

## 3. Product scope

### In scope

1. Backend persistent natal context cache.
2. Backend full natal report generation endpoints.
3. Day pipeline reuse of cached natal context.
4. Strict sidecar response validation before normalization.
5. Separate natal-only normalization/scoring from day/transit scoring.
6. Report persistence with stable sections.
7. Frontend integration for real generate/report flow.
8. Contract cleanup: one generated/shared contract path.
9. Tests, fixtures, and golden sample checks.
10. Production guardrails: no fake successful content, no silent placeholder report.

### Out of scope unless already available in current app

1. Real payment provider implementation.
2. Refunds, invoices, receipts.
3. Admin editor for generated reports.
4. Compatibility/synastry reports.
5. Weekly/monthly forecasts.
6. Rewriting the SolarSage calculation sidecar.

If payment/access gates already exist, this wave may connect to them through a minimal `can_generate_full_report` check. If not, keep generation behind an internal feature flag and document that paid unlock is a later payment wave.

## 4. Target architecture

```text
UserProfile birth data
  -> profile_hash
  -> get_or_build_natal_context(user)
       -> NatalChartCache hit? return cached context
       -> SolarSage /v1/natal
       -> validate raw response
       -> normalize_natal_only(raw_chart)
       -> score_natal(natal_signals)
       -> derive display facts
       -> persist NatalChartCache
  -> preview uses NatalContext
  -> day uses NatalContext + fresh transits
  -> full report generation uses NatalContext + LLM
```

Daily flow:

```text
build_today(user, date)
  -> natal_context = get_or_build_natal_context(user)
  -> transits = SolarSage /v1/transits(date)
  -> validate transits
  -> day_signals = normalize_day(natal_context, transits)
  -> today_payload = score_day(day_signals)
  -> cache TodayPayload by user/date/natal_context_version/transit_target
```

Full report flow:

```text
POST /api/natal/generate
  -> auth user
  -> validate profile completeness
  -> natal_context = get_or_build_natal_context(user)
  -> access check / feature flag
  -> find existing READY report for same context + prompt_version
  -> else create NatalReport(status=GENERATING)
  -> generate sections from deterministic context
  -> validate LLM JSON blocks
  -> persist sections_json + status=READY
```

## 5. Data model

Add migrations and SQLAlchemy models. Use the project's existing JSON-compatible type/style; do not introduce database-specific JSONB if the project currently uses a portable JSON abstraction.

### 5.1 `natal_chart_cache`

Purpose: deterministic reusable natal calculation result.

Fields:

- `id`: primary key.
- `user_id`: FK to user.
- `profile_hash`: string, deterministic hash of all birth inputs that affect natal chart.
- `engine_version`: string, version of SolarSage sidecar/calculation engine.
- `calculation_version`: string, version of normalization/scoring code.
- `house_system`: string, default `placidus` unless project explicitly supports more.
- `raw_chart_json`: JSON, validated raw SolarSage natal output.
- `normalized_context_json`: JSON, production context used by preview/day/report.
- `summary_json`: JSON, optional small denormalized facts for list/preview/debug.
- `created_at`, `updated_at`.
- `invalidated_at`: nullable timestamp.
- `last_used_at`: nullable timestamp.

Uniqueness:

- Unique active cache by `(user_id, profile_hash, engine_version, calculation_version, house_system, invalidated_at is null)`.
- If partial unique indexes are not portable in current DB setup, enforce active uniqueness at service level and add a normal composite index.

`profile_hash` must include at least:

- `birthday`
- `birth_time`
- `birth_lat`
- `birth_lon`
- `birth_tz`
- `birth_city` only if it affects displayed metadata, not chart math
- `gender` only if gendered phrasing is stored in context/report
- `house_system`

Important: if user edits any birth field, old context must not be reused.

### 5.2 `natal_reports`

Purpose: persisted generated full report.

Fields:

- `id`: primary key, report id exposed to frontend.
- `user_id`: FK to user.
- `natal_context_id`: FK to `natal_chart_cache`.
- `status`: enum/string: `PENDING`, `GENERATING`, `READY`, `FAILED_RETRYABLE`, `FAILED_PERMANENT`.
- `access_state`: enum/string: `FREE_PREVIEW`, `UNLOCKED`, `INTERNAL_TEST`, `BLOCKED`.
- `prompt_version`: string.
- `report_schema_version`: string.
- `model_provider`: nullable string.
- `model_name`: nullable string.
- `model_params_json`: JSON.
- `sections_json`: JSON, full generated report sections.
- `sections_status_json`: JSON, per-section generation status if section-by-section generation is used.
- `input_context_hash`: string, hash of exact context passed to LLM.
- `output_hash`: nullable string, hash of validated report output.
- `error_code`: nullable string.
- `error_message_sanitized`: nullable string.
- `created_at`, `updated_at`, `completed_at`.

Uniqueness:

- Prefer reusing READY report by `(user_id, natal_context_id, prompt_version, report_schema_version)`.
- Do not generate duplicate reports on repeated button clicks.

## 6. Backend services

### 6.1 `NatalContextService`

Create a dedicated service, for example:

`apps/api/app/services/natal_context_service.py`

Public methods:

```python
get_or_build_natal_context(user: User) -> NatalContext
build_natal_context(profile: UserProfile) -> NatalContext
invalidate_for_user(user_id: int, reason: str) -> None
compute_profile_hash(profile: UserProfile) -> str
```

Responsibilities:

1. Validate profile completeness.
2. Compute stable `profile_hash`.
3. Check active cache.
4. Call SolarSage `/v1/natal` on miss.
5. Validate sidecar response with Pydantic models.
6. Call natal-only normalization.
7. Call natal-only scoring.
8. Build final `NatalContext` JSON.
9. Persist and return context.

Service must not call transits.

### 6.2 `NatalReportService`

Create or extend a service, for example:

`apps/api/app/services/natal_report_service.py`

Public methods:

```python
get_preview(user: User) -> NatalPreviewRead
generate_report(user: User) -> NatalReportRead
get_report(user: User, report_id: str | None = None) -> NatalReportRead
get_report_section(user: User, section_id: str, report_id: str | None = None) -> NatalReportSectionRead
```

Responsibilities:

1. Use `NatalContextService` for all natal facts.
2. Build preview from `NatalContext`, not from ad hoc SolarSage calls.
3. Generate report from cached deterministic context.
4. Persist report result.
5. Never return fake successful generated content after LLM failure.
6. Return explicit failure states to frontend.

### 6.3 `TodayService` refactor

Current day service should stop calling `client.get_natal(...)` directly.

Target:

```python
natal_context = natal_context_service.get_or_build_natal_context(user)
transits = solarsage_client.get_transits(...)
day_signals = normalization_service.normalize_day(natal_context, transits)
today_payload = scoring_service.score_day(day_signals)
```

Daily cache key must include:

- `user_id`
- `target_date`
- `target_tz`
- `natal_context_id` or `natal_context_hash`
- `calculation_version`
- `transit_engine_version` if available

If user changes birth data, daily cache should naturally miss because natal context id/hash changes.

## 7. Normalization and scoring split

Current `NormalizationService.normalize(natal, transits)` mixes natal and transit signals. Split it.

Required methods:

```python
normalize_natal_only(raw_natal: ValidatedNatalChart) -> NatalSignals
normalize_day(natal_context: NatalContext, transits: ValidatedTransits) -> DaySignals
```

Required scoring methods:

```python
score_natal(natal_signals: NatalSignals) -> NatalScores
score_day(day_signals: DaySignals) -> TodayScores
```

Rules:

1. Natal report/preview cannot include transit aspects.
2. Day forecast must include transits and use cached natal context as radix/base chart.
3. Do not label natal signals as `transit` family.
4. If advanced factors are not available from sidecar, do not invent them.
5. If advanced factors are implemented later, add them as deterministic fields in `NatalContext`, not in LLM prompt prose only.

Natal context should include, when available:

- planets with sign, degree, house, retrograde flag;
- house cusps and angles: ASC, MC, IC, DSC;
- natal aspects with orb and applying/separating if available;
- nodes, Lilith, Chiron, Pars Fortunae, Selena, Vertex, East Point if available;
- elements/modalities balance;
- house emphasis;
- chart ruler and important dispositor facts if deterministic code supports them;
- dignity/debility facts only if deterministic code supports them;
- fixed stars/midpoints/configurations only if deterministic code supports them.

## 8. Sidecar validation

`SolarSageClient` must not return unvalidated raw dicts into business logic.

Add Pydantic schemas for at least:

- `SolarSageNatalResponse`
- `SolarSagePlanetPosition`
- `SolarSageHouseCusp`
- `SolarSageAspect`
- `SolarSageTransitsResponse`

Validation rules:

1. Required fields must be explicit.
2. Unknown extra fields may be allowed at sidecar boundary, but normalized output must be strict.
3. Degrees must be numeric and normalized to `[0, 360)` where applicable.
4. House numbers must be `1..12`.
5. Missing required natal chart fields should produce a clear backend error, not partial fake content.

Error behavior:

- Profile incomplete: return 409 with actionable profile fields.
- Sidecar unavailable: return 503/502 style app error.
- Sidecar schema invalid: return 502 style app error with sanitized details.
- Do not show demo data in production because sidecar failed.

## 9. API endpoints

Keep/adjust existing:

### `GET /api/natal/preview`

Returns real preview based on cached/buildable `NatalContext`.

Behavior:

- On cache hit: no sidecar natal call.
- On cache miss: build and persist context.
- Response must match generated/shared `NatalPreviewRead` contract.

### `POST /api/natal/generate`

Starts or performs full report generation.

MVP acceptable behavior:

- synchronous generation if expected duration is acceptable;
- or async/job-like status if current project already has job infrastructure.

Request body:

```json
{
  "force_regenerate": false
}
```

Response:

```json
{
  "report_id": "...",
  "status": "READY|GENERATING|FAILED_RETRYABLE|FAILED_PERMANENT",
  "sections_available": true
}
```

Rules:

1. Repeated click must be idempotent.
2. If READY report exists for same context/prompt/schema version, return it.
3. If GENERATING exists, return current status.
4. If previous FAILED_RETRYABLE exists, allow retry unless retry limit exceeded.
5. Do not create multiple reports for the same user/context/prompt version.

### `GET /api/natal/report`

Returns latest READY report for current active natal context, or current generation status.

### `GET /api/natal/report/{report_id}`

Returns specific report if it belongs to user.

### `GET /api/natal/report/{report_id}/section/{section_id}`

Returns one section if frontend needs section loading.

If frontend currently renders whole report at once, section endpoint may be implemented after full report endpoint, but schema should be designed now.

## 10. Report schema and blocks

Current frontend and backend block contracts are inconsistent. Fix this before wiring production report.

Choose one strict shared schema generated from backend or a single shared contract package. Backend Pydantic should be the source of truth if current contract-generation flow supports it.

Recommended block union:

```text
lead
paragraph
heading
list
callout
pros_cons
quote
divider
```

Each block must have a stable `type` discriminator.

Required report shape:

```json
{
  "id": "...",
  "meta": {
    "user_name": "...",
    "birth_date": "...",
    "birth_time": "...",
    "birth_place": "...",
    "house_system": "Placidus",
    "context_hash": "...",
    "prompt_version": "..."
  },
  "sections": [
    {
      "id": "portrait",
      "title": "Психологический портрет",
      "summary": "...",
      "blocks": []
    }
  ]
}
```

Required section ids for this wave:

1. `portrait`
2. `ascendant`
3. `rulers`
4. `aspects`
5. `spheres`
6. `planets`
7. `shadow`
8. `synthesis`

These must align with preview locked chapters and frontend navigation.

## 11. LLM generation contract

LLM input must be a compact, deterministic JSON context, not raw unstructured text.

Input shape:

```json
{
  "user": {
    "name": "...",
    "gender": "female",
    "locale": "ru"
  },
  "birth": {
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "place": "...",
    "timezone": "..."
  },
  "chart": {
    "angles": {},
    "planets": [],
    "houses": [],
    "aspects": [],
    "special_points": [],
    "balances": {},
    "scores": {},
    "dominants": []
  },
  "report_plan": {
    "sections": ["portrait", "ascendant", "rulers", "aspects", "spheres", "planets", "shadow", "synthesis"],
    "tone": "friendly, concrete, practical, non-fatalistic",
    "block_schema_version": "..."
  }
}
```

Output must be strict JSON matching `NatalReportRead` or per-section `NatalReportSectionRead`.

Prompt requirements:

1. Write in Russian.
2. Use correct masculine/feminine wording from profile gender.
3. Be concrete and life-applicable.
4. Avoid fatalism and medical/legal/financial certainty.
5. Do not introduce chart facts absent from input JSON.
6. Do not claim exact predictive events from natal chart.
7. Prefer practical interpretation: strengths, risks, relationship/work/energy patterns, self-observation prompts.
8. Do not mention internal scores unless they are intentionally user-facing.

Validation:

1. Parse JSON.
2. Validate Pydantic schema.
3. Validate every referenced planet/sign/house/aspect exists in context.
4. Reject hallucinated chart facts.
5. Reject empty/generic sections.
6. Persist only after full validation.

Failure behavior:

- If validation fails, status becomes `FAILED_RETRYABLE` with sanitized reason.
- Frontend shows explicit generation error/retry, not fake report.
- No placeholder generated sections.

## 12. Frontend integration

Current frontend demo routes must remain available only under demo mode.

Required behavior:

### `/readings/natal`

- Calls real `GET /api/natal/preview` when not demo mode.
- CTA calls `POST /api/natal/generate` or routes to generation page that calls it.
- Shows clear errors for incomplete profile and generation failures.

### `/readings/natal/generating`

- No hardcoded demo completion in production.
- Starts generation if no active report exists.
- Polls status if backend is async.
- Routes to `/readings/natal/{report_id}` when READY.
- If generation fails, show retry action if status is retryable.

### `/readings/natal/[id]`

- Fetches `GET /api/natal/report/{id}`.
- Uses real report sections.
- Demo report only when `IS_DEMO_MODE=true` and id is demo.

### Contracts

- Remove or deprecate duplicated local-only `lib/contracts/natal.ts` if it conflicts with generated contracts.
- `NatalPreviewRead`, `NatalReportRead`, `NatalReportSectionRead`, and block schemas must come from one shared source.
- `pnpm contracts:generate` and `pnpm contracts:check` must pass.

## 13. Caching and invalidation

### Natal context cache

Cache miss when:

1. No active cache for profile hash.
2. `engine_version` changed.
3. `calculation_version` changed.
4. House system changed.
5. User changed birth data.

Do not delete old contexts by default; mark invalidated if needed. Reports tied to old contexts remain historical artifacts but should not be shown as current active report unless explicitly requested.

### Today payload cache

Today cache must depend on natal context version/hash. If birth data changes, daily response should rebuild.

### Report cache

Reports are immutable for a given natal context and prompt/schema version.

If prompt version changes:

- existing report may stay available;
- new generation should create a new report version;
- UI should show latest current-version report by default.

## 14. Testing requirements

### Unit tests

1. `compute_profile_hash` changes when birth date/time/lat/lon/tz/house_system changes.
2. `get_or_build_natal_context` returns cache hit without sidecar call.
3. `get_or_build_natal_context` builds and persists on cache miss.
4. Incomplete profile returns 409-style domain error.
5. Sidecar invalid schema returns sanitized failure.
6. `normalize_natal_only` does not include transit signals.
7. `normalize_day` uses cached natal context + transits.
8. `score_natal` and `score_day` are separate methods and not interchangeable.
9. `generate_report` is idempotent for repeated clicks.
10. LLM output with hallucinated planet/aspect is rejected.
11. LLM output with invalid block type is rejected.
12. Failed generation does not create READY report.

### API tests

1. `GET /api/natal/preview` builds context on first call.
2. Second preview call reuses context.
3. `POST /api/natal/generate` returns report id/status.
4. Repeated `POST /api/natal/generate` returns same active/ready report.
5. `GET /api/natal/report/{id}` returns only owner report.
6. Production mode never returns demo report after backend failure.
7. `/api/today` or equivalent day endpoint does not call natal sidecar on natal cache hit.

### Frontend tests

1. `/readings/natal` renders real preview payload.
2. CTA starts generation.
3. Generating page does not auto-route to demo in production.
4. Report page fetches real report by id.
5. Block renderer supports all shared block types.
6. Incomplete profile state is actionable.
7. Generation failure state is visible and not masked as success.

### Golden sample test

Add a deterministic fixture based on the provided Zhanna sample:

Birth data:

- Date: `1993-01-07`
- Time: `10:33`
- Place: `Chirchiq / Чирчик, Tashkent region`
- House system: `Placidus`

Expected key facts from the sample:

- ASC: Pisces around `11°55`
- MC: Sagittarius around `20°28`
- Sun: Capricorn around `16°56`, 11th house
- Moon: Gemini around `29°38`, 4th house
- Mercury: Capricorn around `7°06`, 10th house
- Venus: Pisces around `3°33`, 12th house
- Mars: Cancer around `17°57`, 5th house, retrograde
- Jupiter: Libra around `13°57`, 7th house
- Saturn: Aquarius around `17°01`, 12th house
- Uranus: Capricorn around `18°02`, 11th house
- Neptune: Capricorn around `18°35`, 11th house
- Pluto: Scorpio around `24°47`, 9th house
- North Node: Sagittarius around `21°25`, 10th house
- South Node: Gemini around `21°25`, 4th house

Tolerance:

- Positions: choose a realistic small degree tolerance based on sidecar precision.
- Houses: exact expected house numbers unless known sidecar/house-system differences are documented.

This fixture is not an astrology correctness proof. It is a regression guard that the backend keeps producing the same chart semantics for a known sample.

## 15. Guardrails and non-goals

1. No fake report in production.
2. No generic fallback generated content.
3. No LLM chart calculation.
4. No silent cache reuse after profile changes.
5. No duplicated frontend/backend schemas.
6. No transit contamination in natal report.
7. No user-facing stack traces or raw provider errors.
8. No live external calls in unit tests.
9. No broad rewrite of existing day product unless required for natal-context reuse.

## 16. Implementation waves

### Wave 1: Schema and migrations

Deliver:

- `NatalChartCache` model/table.
- `NatalReport` model/table.
- Pydantic schemas for natal context/report/block contracts.
- Contract generation updated.
- Basic migration tests.

Acceptance:

- App starts with migrations.
- `pnpm contracts:check` passes.
- Backend tests for schema validation pass.

### Wave 2: Natal context service

Deliver:

- `NatalContextService`.
- Sidecar natal response validation.
- `normalize_natal_only`.
- `score_natal`.
- Preview refactored to use context service.

Acceptance:

- First preview call builds cache.
- Second preview call reuses cache.
- No transits are called for preview/full natal context.

### Wave 3: Day pipeline reuse

Deliver:

- `TodayService` uses cached natal context.
- Day normalization split from natal normalization.
- Daily cache key includes natal context version/hash.

Acceptance:

- Day endpoint still returns same expected shape.
- Day endpoint does not call natal sidecar on context cache hit.
- Day rebuilds if birth profile changes.

### Wave 4: Full report backend

Deliver:

- `NatalReportService`.
- `POST /api/natal/generate`.
- `GET /api/natal/report`.
- `GET /api/natal/report/{id}`.
- LLM JSON generation and validation.
- Idempotent repeated generation.

Acceptance:

- Full report persists to DB.
- Repeated generate returns existing report/status.
- Invalid LLM output is rejected and not persisted as READY.

### Wave 5: Frontend real flow

Deliver:

- Preview CTA uses real generate route.
- Generating page starts/polls real generation.
- Report page fetches real report by id.
- Demo content gated strictly by demo mode.

Acceptance:

- Production mode cannot navigate from generating page to demo report.
- Report page renders real API response.
- Error/retry states are visible.

### Wave 6: Golden tests and evidence

Deliver:

- Zhanna golden fixture.
- Sidecar mock fixtures.
- Unit/API/frontend evidence.
- Short implementation notes in PR.

Acceptance:

- Golden sample key facts match expected tolerances.
- Tests prove cache hit/miss, invalidation, report idempotency, and no transit contamination.

## 17. Definition of done

1. `GET /api/natal/preview` is real and cache-backed.
2. `POST /api/natal/generate` creates or returns a persisted report.
3. `GET /api/natal/report/{id}` returns a real persisted report.
4. Day calculation reuses cached natal context.
5. Natal report generation uses no transits.
6. LLM is only a narrative layer over deterministic chart context.
7. Contracts are unified and generated/checkable.
8. Demo data is impossible to return in production after real API failure.
9. Golden sample regression test exists.
10. All unit/API/frontend tests for this wave pass.

## 18. Reviewer checklist

Reviewer must explicitly verify:

- There is exactly one production path for natal chart facts: `NatalContextService`.
- Today pipeline no longer directly calls natal sidecar if cache exists.
- Full report does not use mocked `MOCK_NATAL_REPORT` outside demo mode.
- LLM output is schema-validated before persistence.
- Report generation is idempotent.
- Invalid LLM/provider response is visible as failure, not successful placeholder content.
- Profile change invalidates context usage through `profile_hash`.
- Tests prove no transit aspects/signals appear in natal-only report context.
