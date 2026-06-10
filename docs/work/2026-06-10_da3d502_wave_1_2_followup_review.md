# Follow-up Review: da3d502 — W-NATAL-FULL Waves 1–2

Date: 2026-06-10
Status: CHANGES REQUESTED
Reviewed commit: `da3d50278bed7275f5317c5d1d38a898b295d4fd`
Branch: `feat/natal-full-report`
Previous review: `docs/work/2026-06-10_wave_1_2_natal_cache_review.md`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`

## 1. Summary

Commit `da3d502` addresses the four explicit blockers from the previous review:

1. `natal_chart_cache` migration now creates a partial unique index with `WHERE invalidated_at IS NULL`.
2. `today_payloads_cache` now has `profile_hash` and unique key `(user_id, target_date, profile_hash)`.
3. Full report endpoints are gated by `settings.natal_report_enabled` and return `501 FEATURE_DISABLED` by default.
4. `SolarSageClient.get_natal()` and `get_transits()` now return `validated.model_dump(by_alias=True)` instead of the raw sidecar dict.

These fixes are directionally correct.

However, the commit should not be accepted yet. There are new/remaining blockers in the implementation.

## 2. Verdict

CHANGES REQUESTED.

This is close, but not safe to accept until the blockers below are fixed and covered by tests.

## 3. Blockers

### BLOCKER 1 — `_prefetch_week()` still calls `_get_cached_payload()` with the old signature

`_get_cached_payload()` now requires:

```python
_get_cached_payload(user_id, target_date, profile_hash)
```

The updated cache lookup correctly filters by `profile_hash`.

But `_prefetch_week()` still calls:

```python
cached = await self._get_cached_payload(user_id, day)
```

Impact:

- Background week prefetch will raise `TypeError` every time.
- The exception is swallowed by `except Exception: pass`, so this failure will be silent.
- Prefetch will stop working, and the system will hide the regression.

Required fix:

Compute the same profile hash before the prefetch loop, or simply remove the manual pre-check and let `get_today_payload(..., skip_prefetch=True)` perform its own cache check.

Recommended minimal fix:

```python
async def _prefetch_week(self, user_id, today: Date) -> None:
    async def _calc_one(day: Date):
        try:
            await self.get_today_payload(user_id, day, None, skip_prefetch=True)
        except Exception:
            logger.debug("Prefetch failed", exc_info=True)
```

Acceptance test required:

- Call `_prefetch_week()` or trigger a normal today build with `skip_prefetch=False`.
- Assert no `TypeError` is raised/logged due to `_get_cached_payload` signature mismatch.

### BLOCKER 2 — `TodayService` still does not use `normalize_day()` / `score_day()` path

The TZ required splitting:

```python
normalize_natal_only(raw_natal)
normalize_day(natal_context, transits)
score_natal(natal_signals)
score_day(day_signals)
```

`NormalizationService.normalize_day()` exists, but `TodayService` still loads `raw_chart_json` from cache and calls the legacy method:

```python
signals = normalization_service.normalize(natal, transits)
```

It also still calls:

```python
scoring_result = scoring_service.score(signals)
```

Impact:

- The day pipeline is cache-backed, but it has not actually migrated to the new day-specific normalization/scoring API.
- The new `normalize_day()` method is currently not proven by the production day path.
- The old mixed `normalize()` remains the real path for day.

Required fix:

Either:

1. Update `TodayService` to use `normalize_day(...)` and `score_day(...)`; or
2. Rename the acceptance claim: this commit only makes day reuse cached raw natal chart, not the new day pipeline.

Preferred target:

```python
natal_context = await context_service.get_or_build_natal_context(user_id)
transits = await client.get_transits(...)
signals = normalization_service.normalize_day(
    natal_context.model_dump(by_alias=False),
    transits,
)
scoring_result = scoring_service.score_day(signals)
```

Acceptance tests required:

- `TodayService` calls `normalize_day()`, not legacy `normalize()`.
- `TodayService` calls `score_day()`, not only legacy `score()`.

### BLOCKER 3 — `score_day()` appears missing despite being claimed in the commit summary

Commit message says:

```text
ScoringService → score_natal() + score_day()
```

The file reviewed at `da3d502` has `score_natal()` and legacy `score()`, but no visible `score_day()` method in the inspected scoring service range.

Impact:

- The API split is incomplete or misleading.
- Future coder/reviewer may assume `score_day()` exists and is production-ready, but the day path still uses `score()`.

Required fix:

Add:

```python
def score_day(self, signals: list[AstroSignal]) -> dict:
    return self.score(signals)
```

or make `score()` the explicitly documented day method and update the TЗ/commit notes. Prefer adding `score_day()` to match the accepted architecture.

Acceptance test required:

- Direct unit test for `score_day()`.
- TodayService uses it.

### BLOCKER 4 — ORM partial index definition likely uses an invalid `postgresql_where` type

Migration uses raw SQL and looks correct:

```sql
CREATE UNIQUE INDEX ix_natal_chart_cache_active
ON natal_chart_cache (...)
WHERE invalidated_at IS NULL
```

But ORM model defines:

```python
Index(
    "ix_natal_chart_cache_active",
    "user_id", "profile_hash", "engine_version",
    "calculation_version", "house_system",
    unique=True,
    postgresql_where=("invalidated_at IS NULL"),
)
```

`postgresql_where` should be a SQLAlchemy SQL expression, not a plain string.

Impact:

- SQLAlchemy metadata creation / test DB creation can fail.
- Alembic autogenerate may produce weird diffs.
- PostgreSQL dialect may not accept the string as a where-clause expression.

Required fix:

Use a real expression. Example:

```python
Index(
    "ix_natal_chart_cache_active",
    "user_id", "profile_hash", "engine_version", "calculation_version", "house_system",
    unique=True,
    postgresql_where=text("invalidated_at IS NULL"),
)
```

Import `text` from SQLAlchemy.

If SQLite tests create metadata directly, consider also `sqlite_where=text("invalidated_at IS NULL")`.

Acceptance test required:

- Metadata can be created in the project test DB.
- Migration upgrade runs.

### BLOCKER 5 — Sidecar schemas default required arrays to empty lists, which can mask invalid sidecar responses

The sidecar validation schemas currently allow:

```python
planets: list[SolarSagePlanetPosition] = []
houses: list[SolarSageHouseCusp] = []
special_points: list[SolarSageSpecialPoint] = []
```

and transits:

```python
planets: list[SolarSageTransitPlanet] = []
```

Impact:

- A sidecar response missing `planets` or `houses` may validate as an empty chart instead of failing.
- That violates the previous blocker fix intent: invalid sidecar response must fail before normalization.
- It can produce empty/low-quality context rather than an explicit 502.

Required fix:

Make required fields required:

```python
planets: list[SolarSagePlanetPosition]
houses: list[SolarSageHouseCusp]
special_points: list[SolarSageSpecialPoint] = []  # optional if truly optional
```

For natal, at minimum require non-empty `planets` and `houses`. Add a model validator if needed.

For transits, require non-empty `planets`.

Acceptance tests required:

- `{}` as natal response fails validation.
- natal response with empty planets fails validation.
- transits response with empty/missing planets fails validation.

## 4. Previous blockers status

### Previous BLOCKER 1 — active-only natal cache uniqueness

Mostly fixed in migration. The migration now creates a partial unique index with `WHERE invalidated_at IS NULL`.

Still needs ORM model expression fix from BLOCKER 4 above.

### Previous BLOCKER 2 — Today cache key depends on natal context

Mostly fixed. `TodayPayloadCache` now includes `profile_hash`, and cache lookup/upsert uses it.

Remaining issue: `_prefetch_week()` still calls the old signature and silently breaks.

### Previous BLOCKER 3 — Wave 4 endpoints reachable too early

Fixed enough for Wave 1–2. The report endpoints return 501 when `NATAL_REPORT_ENABLED=false`, and the setting defaults to false.

### Previous BLOCKER 4 — sidecar validation returns raw dict

Partially fixed. Client now returns `validated.model_dump(by_alias=True)`.

Remaining issue: validation is too permissive because required arrays have empty-list defaults.

## 5. Major risks

### RISK 1 — `normalized_context_json` does not include `natal_signals`, while `normalize_day()` expects them optionally

`normalize_day()` first tries:

```python
natal_signals = natal_context.get("natal_signals", [])
```

But `NatalContextData` stores `top_signals`, not full `natal_signals`.

It then falls back to rebuilding from context planets/houses/aspects. This may work, but it means `normalize_day()` is not really using the persisted normalized signal layer.

Recommendation:

- Either persist full natal signal list in `NatalContextData`; or
- Remove the `natal_signals` branch and make `normalize_day()` deterministic from the stored chart context.

### RISK 2 — `NatalContextService` validates twice but normalizes the post-client dict, not the local `validated` model

`SolarSageClient.get_natal()` already returns a validated dump. `NatalContextService` validates it again, then calls:

```python
natal_signals = normalization_service.normalize_natal_only(raw_chart)
```

This is acceptable if `raw_chart` is already the sanitized dict. But the naming is now misleading and should be clarified.

Recommendation:

Rename local variable from `raw_chart` to `validated_chart_dict` after client return, or make the client return a model.

### RISK 3 — Background exceptions are swallowed too broadly

`_prefetch_week()` swallows all exceptions with no log. This is why BLOCKER 1 can hide.

Recommendation:

At least log debug-level exception with `exc_info=True`, or track a metric.

## 6. Required tests before acceptance

Minimum additional tests for this follow-up:

1. `_prefetch_week()` does not call `_get_cached_payload()` with stale signature.
2. Today cache lookup/upsert uses `profile_hash` and changes cache key after birth data changes.
3. Today path uses `normalize_day()` or the claim is corrected.
4. `score_day()` exists and is used, or the claim is corrected.
5. ORM metadata/migration succeeds with the partial unique index definition.
6. Invalid natal sidecar response `{}` fails validation.
7. Empty natal `planets` / `houses` fails validation.
8. Empty/missing transit `planets` fails validation.
9. Report endpoints return 501 when `NATAL_REPORT_ENABLED=false`.
10. Report endpoints are reachable only when flag is true.

## 7. Acceptance decision

Do not accept yet.

Accept after:

- `_prefetch_week()` is fixed;
- day path either truly uses `normalize_day()`/`score_day()` or claims are corrected;
- partial index ORM definition is fixed;
- sidecar required/empty response validation is hardened;
- tests cover the above.
