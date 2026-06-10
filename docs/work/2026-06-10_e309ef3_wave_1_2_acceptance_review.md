# Acceptance Review: e309ef3 — W-NATAL-FULL Waves 1–2

Date: 2026-06-10
Status: ACCEPTED FOR WAVE 1–2 BLOCKER CLOSURE
Reviewed commit: `e309ef3d5a5f8072ca2cbcfb18ee93883bf78744`
Branch: `feat/natal-full-report`
Previous follow-up review: `docs/work/2026-06-10_da3d502_wave_1_2_followup_review.md`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`

## 1. Scope reviewed

This review checked commit `e309ef3` against the 5 blockers from the previous follow-up review:

1. `_prefetch_week()` stale `_get_cached_payload()` call.
2. `TodayService` still using legacy `normalize()` / `score()`.
3. Missing explicit `ScoringService.score_day()`.
4. ORM partial-index `postgresql_where` using a plain string.
5. Sidecar schemas accepting missing/empty required arrays.

## 2. Verdict

ACCEPTED FOR WAVE 1–2 BLOCKER CLOSURE.

The 5 follow-up blockers are closed by code inspection.

This does not mean the whole natal full-report product is done. It means the Wave 1–2 cache/context/day-pipeline blocker set is now acceptable to proceed, assuming the test suite/evidence is green.

## 3. Blocker closure review

### BLOCKER 1 — `_prefetch_week()` stale cache call

Status: RESOLVED.

`_prefetch_week()` no longer calls `_get_cached_payload(user_id, day)` directly. It delegates each day to:

```python
await self.get_today_payload(user_id, day, None, skip_prefetch=True)
```

This lets the normal TodayService path compute `profile_hash` and perform the cache check using the correct key. Exceptions are now debug-logged instead of silently swallowed.

Acceptance result: OK.

### BLOCKER 2 — TodayService must use `normalize_day()`

Status: RESOLVED.

`TodayService` now:

1. obtains `natal_context` from `NatalContextService`;
2. dumps it to `natal_context_dict`;
3. calls `NormalizationService.normalize_day(natal_context_dict, transits)`;
4. passes `natal_context_dict` into yesterday signal calculation;
5. `_get_yesterday_signals()` also uses `normalize_day()`.

The old production day path using `normalization_service.normalize(natal, transits)` has been removed from this flow.

Acceptance result: OK.

### BLOCKER 3 — Missing `score_day()`

Status: RESOLVED.

`ScoringService.score_day()` now exists and returns:

- `day_status`
- `sphere_scores`
- `top_signals`

`TodayService` calls `scoring_service.score_day(signals)` instead of legacy `score()`.

Legacy `score()` remains for backward compatibility and is documented as such.

Acceptance result: OK.

### BLOCKER 4 — ORM partial-index expression

Status: RESOLVED.

`models.py` now imports SQLAlchemy `text`, and `NatalChartCache.__table_args__` uses:

```python
postgresql_where=text("invalidated_at IS NULL")
sqlite_where=text("invalidated_at IS NULL")
```

The migration already uses raw SQL for the partial unique index. ORM metadata now matches the intended partial-index semantics better than the previous plain-string variant.

Acceptance result: OK.

### BLOCKER 5 — Sidecar validation too permissive

Status: RESOLVED.

`SolarSageNatalResponse` now requires:

```python
planets: list[SolarSagePlanetPosition]
houses: list[SolarSageHouseCusp]
```

and validates both lists as non-empty.

`SolarSageTransitsResponse` now requires:

```python
planets: list[SolarSageTransitPlanet]
```

and validates it as non-empty.

`special_points` remains optional with an empty default, which is acceptable.

Acceptance result: OK.

## 4. Remaining non-blocking risks

### RISK 1 — Test evidence was not visible in this code-only review

The commit message says the fixes were verified, but this specific commit does not appear to add test files. If tests exist elsewhere or were run locally, attach the evidence in the implementation packet.

Required evidence before final merge/acceptance gate:

- backend unit/API tests pass;
- migration upgrade/downgrade passes on the target DB;
- explicit tests cover the 5 fixed blockers.

This is an evidence requirement, not a code blocker found in `e309ef3`.

### RISK 2 — `normalize_day()` still reconstructs natal signals from persisted context

`NatalContextData` stores chart facts and top signals, not the full `natal_signals` list. `normalize_day()` therefore falls back to rebuilding natal house/sign/aspect signals from the persisted chart context.

This is acceptable for Wave 1–2, but for future report/LLM context work consider either:

- persist full deterministic `natal_signals`; or
- make `normalize_day()` intentionally context-derived and remove the unused `natal_signals` branch.

### RISK 3 — Legacy hardcoded `/api/natal/overview` and `/api/natal/section/*` still exist

This is pre-existing and not part of the 5 blockers fixed by `e309ef3`, but it should be cleaned up before production natal rollout.

Current safer production path is `/api/natal/preview`, which uses `NatalContextService`.

Recommended next cleanup:

- deprecate/remove legacy overview/section endpoints; or
- route them through `NatalContextService`; or
- return `501` if not used by frontend.

## 5. Recommended next actions

1. Attach test evidence for the 5 blocker fixes.
2. Proceed to Wave 3 or Wave 4 only after the Wave 1–2 tests are green.
3. Add a small cleanup ticket for legacy fake natal endpoints.
4. Keep `NATAL_REPORT_ENABLED=false` until full-report LLM validation and idempotency tests are done.

## 6. Acceptance decision

Accepted for Wave 1–2 blocker closure.

No remaining code blocker was found in `e309ef3` for the 5 issues from the previous follow-up review.
