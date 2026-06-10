# Review: W-NATAL-FULL-REPORT-CACHE — Waves 1–2

Date: 2026-06-10
Status: CHANGES REQUESTED
Reviewed compare: `main...feat/natal-full-report`
Head commit: `0a3215cb4318f9e7bb74cda14acc666df7338972`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`

## 1. Scope reviewed

Compare contains 1 commit ahead of `main`, 11 changed files:

- `apps/api/alembic/versions/0016_add_natal_cache_and_reports.py`
- `apps/api/app/api/natal.py`
- `apps/api/app/clients/solarsage_client.py`
- `apps/api/app/db/models.py`
- `apps/api/app/schemas/natal.py`
- `apps/api/app/services/natal_context_service.py`
- `apps/api/app/services/natal_report_service.py`
- `apps/api/app/services/natal_service.py`
- `apps/api/app/services/normalization_service.py`
- `apps/api/app/services/scoring_service.py`
- `apps/api/app/services/today_service.py`

Declared scope matches the requested Wave 1–2 direction:

- DB tables for natal context cache and reports;
- `NatalContextService` cache-first path;
- `normalize_natal_only()` / `normalize_day()` split;
- `score_natal()` / `score_day()` split;
- TodayService switched away from direct natal sidecar calls;
- sidecar validation hooks added;
- context debug/refresh endpoints added.

Overall direction is correct. Do not accept yet: there are blockers around cache invalidation semantics, scope creep, and required proof/tests.

## 2. Verdict

CHANGES REQUESTED.

The implementation is moving in the right architectural direction, but Wave 1–2 should not be merged/accepted until the blockers below are fixed or explicitly proven false with code/tests.

## 3. Blockers

### BLOCKER 1 — `natal_chart_cache` unique index is not active-only

Migration creates a unique index on:

```text
user_id, profile_hash, engine_version, calculation_version, house_system
```

But it does not include an `invalidated_at IS NULL` partial condition and does not include `invalidated_at` in the key.

Impact:

- `POST /api/natal/context/refresh` can invalidate an old context but then fail to insert a new context with the same profile hash/version.
- Old invalidated rows still block new active rows.
- This violates the TZ requirement: unique active cache, not unique forever cache.

Required fix:

For PostgreSQL:

```python
op.create_index(
    "ix_natal_chart_cache_active_unique",
    "natal_chart_cache",
    ["user_id", "profile_hash", "engine_version", "calculation_version", "house_system"],
    unique=True,
    postgresql_where=sa.text("invalidated_at IS NULL"),
)
```

If DB portability is required, use a non-unique index and enforce active uniqueness inside `NatalContextService` with transaction/locking semantics.

Acceptance test required:

1. Build context.
2. Refresh/invalidate context.
3. Build context again for same profile/version.
4. Assert new active row exists and no unique-constraint failure occurs.

### BLOCKER 2 — Today cache key must include natal context identity

The summary says `TodayService` now uses `NatalContextService`, which is correct. But Wave 1–2 is only safe if the existing daily payload cache key now depends on natal context identity/hash/version.

Impact if missing:

- User changes birth data.
- Natal context rebuilds correctly.
- Existing day payload cache may still return old day result calculated from old natal context.

Required fix/proof:

Daily cache key must include at least one of:

- `natal_context_id`; or
- `natal_context_hash`; or
- `profile_hash + calculation_version`.

Acceptance test required:

1. Build today payload for user/date.
2. Change birth time or birth coordinates.
3. Build today payload for same user/date.
4. Assert cached old TodayPayload is not reused.

### BLOCKER 3 — Wave 1–2 appears to include Wave 4 report endpoints/service

Compare includes `natal_report_service.py` and API routes for:

- `POST /api/natal/generate`
- `GET /api/natal/report`
- `GET /api/natal/report/{report_id}`
- report section retrieval

This is beyond pure Wave 1–2 if the service is actually callable in production.

Impact:

- Full report generation may become externally reachable before LLM validation, idempotency, access gating, and frontend flow are complete.
- If service contains placeholder/skeleton generation, it can violate the no-fake-success canon.

Required fix:

Choose one:

1. Move report endpoints/service wiring to Wave 4; keep only schemas/models in Wave 1.
2. Keep code but feature-flag endpoints off by default.
3. Make endpoints return explicit `501 NOT_IMPLEMENTED` until Wave 4 acceptance tests exist.

Acceptance test required:

- In production config, unfinished full-report endpoints must not return fake READY report content.

### BLOCKER 4 — Sidecar validation result must not be discarded silently

`SolarSageClient` now validates with Pydantic before returning, which is good. But the implementation pattern shown in diff validates and then returns the original raw dict.

Risk:

- Downstream code still receives untyped raw dicts.
- Normalization may rely on unnormalized aliases/defaults/coercions that exist only in the validated model.
- If schemas are permissive, invalid extra/missing semantics can still leak into business logic.

Required fix/proof:

Prefer one of:

```python
validated = SolarSageNatalResponse.model_validate(data)
return validated
```

or:

```python
validated = SolarSageNatalResponse.model_validate(data)
return validated.model_dump(mode="json")
```

Same for transits.

Acceptance tests required:

- invalid natal sidecar response fails before normalization;
- invalid transit sidecar response fails before day scoring;
- normalization tests consume validated shape, not arbitrary raw dicts.

## 4. Major risks

### RISK 1 — `NatalReport` uniqueness may block force regeneration after failure

The report table has a uniqueness constraint by:

```text
user_id, natal_context_id, prompt_version, report_schema_version
```

This is good for idempotency, but it can block regeneration unless the service updates the existing row instead of inserting a new one.

Required check:

- `force_regenerate=True` must either update the existing report row safely or use a new `prompt_version/report_schema_version`.
- Failed retryable report must not permanently block the user from generating a valid report.

### RISK 2 — `updated_at` in migration may not update at DB level

Alembic `onupdate=sa.func.now()` does not necessarily create a database-side update trigger. If the app relies on `updated_at`, SQLAlchemy model-level `onupdate` or explicit service updates must handle it.

Required check:

- Updates to cache/report rows actually change `updated_at` in tests.

### RISK 3 — `raw_chart_json` / `normalized_context_json` are stored as text

Text storage is acceptable if project portability requires it, but it needs disciplined serialization helpers.

Required check:

- Model/service should never expose raw JSON strings to schemas.
- Corrupt JSON in DB should fail explicitly.

### RISK 4 — `get_houses()` can create double-source-of-truth risk

If `/v1/natal` already returns houses/cusps, adding separate `get_houses()` may create divergence unless used carefully.

Required rule:

- NatalContext should have exactly one canonical house source.
- If houses are fetched separately, the service must validate that they match the natal calculation inputs and house system.

## 5. Suggestions

### SUGGESTION 1 — Add explicit `NatalContextRead` schema

For `GET /api/natal/context`, return a small safe debug/read schema rather than full raw chart by default.

Suggested shape:

```json
{
  "id": "...",
  "profile_hash": "...",
  "engine_version": "...",
  "calculation_version": "...",
  "house_system": "placidus",
  "summary": {},
  "created_at": "...",
  "last_used_at": "..."
}
```

Raw chart/context JSON should be hidden unless there is an internal debug flag.

### SUGGESTION 2 — Rename cache index

Current name `ix_natal_chart_cache_active` sounds like an active-only index. If it remains non-partial/non-conditional, rename it to avoid semantic confusion.

Better:

- `uq_natal_chart_cache_active_context` for partial unique active index;
- `ix_natal_chart_cache_lookup` for non-unique lookup index.

### SUGGESTION 3 — Add service-level observability

Add structured logs/metrics for:

- natal_context_cache_hit;
- natal_context_cache_miss;
- natal_context_refresh;
- sidecar_schema_invalid;
- day_reused_natal_context.

This will make future production debugging much easier.

## 6. Required tests before acceptance

Minimum test set for accepting Waves 1–2:

1. Migration creates both tables.
2. Active unique cache allows rebuild after invalidation.
3. `get_or_build_natal_context()` cache hit does not call SolarSage natal endpoint.
4. `get_or_build_natal_context()` cache miss calls SolarSage once and persists context.
5. `POST /api/natal/context/refresh` invalidates old context and creates/returns new active context.
6. `normalize_natal_only()` does not include transit signals.
7. `normalize_day()` uses cached natal context + validated transits.
8. `TodayService` does not call natal sidecar if natal context cache hit exists.
9. Today cache misses after birth profile change.
10. Invalid natal sidecar response fails before normalization.
11. Invalid transit sidecar response fails before scoring.
12. Production full-report endpoints do not return placeholder/fixture READY content.

## 7. Acceptance decision

Do not accept yet.

Accept after:

- active-only uniqueness is fixed;
- Today cache key dependency on natal context is proven;
- unfinished report endpoints are either disabled/flagged or fully tested;
- sidecar validation returns/uses validated data;
- tests above are present and passing.
