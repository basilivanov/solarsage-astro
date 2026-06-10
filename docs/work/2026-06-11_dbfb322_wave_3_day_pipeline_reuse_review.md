# Review: dbfb322 — Wave 3 Day Pipeline Reuse

Date: 2026-06-11
Status: ACCEPTED WITH TEST-HARDENING FOLLOW-UP
Reviewed commit: `dbfb322562e657d33b4154e952ff29056d23b6ad`
Branch: `feat/natal-full-report`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`
Previous accepted cleanup: `docs/work/2026-06-11_50cd54f_legacy_natal_cleanup_review.md`

## 1. Scope reviewed

Wave 3 target from TZ:

- `TodayService` should reuse cached `NatalContext` instead of directly calling natal sidecar.
- Day calculation should only fetch fresh transits.
- Day cache key should depend on `profile_hash` / natal context identity.
- Day payload shape should remain compatible.
- Tests should prove cache hit/miss and no direct natal sidecar call.

Commit `dbfb322` changes:

- `apps/api/app/api/day.py`
- `apps/api/app/services/today_service.py`
- `apps/api/tests/test_day_no_birthday_fallback.py`
- `apps/api/tests/test_wave3_day_pipeline_reuse.py`

Commit message reports: `93 tests passed, 0 failed`.

## 2. Verdict

ACCEPTED WITH TEST-HARDENING FOLLOW-UP.

No code blocker found for Wave 3 production path. `TodayService` now routes natal facts through `NatalContextService`, calls the day sidecar only for transits, uses `normalize_day()`, uses `score_day()`, and caches TodayPayload by `(user_id, target_date, profile_hash)`.

However, two tests are weaker than their names/acceptance labels claim. This is not a code blocker because the implementation itself is aligned, but the test suite should be hardened before final merge or in the next small cleanup commit.

## 3. Code review

### CHECK 1 — TodayService no longer calls natal sidecar directly

Status: OK.

`TodayService.get_today_payload()` now:

```python
context_service = NatalContextService(self.db)
natal_context = await context_service.get_or_build_natal_context(user_id)
```

Then it obtains a SolarSage client only for:

```python
transits = await client.get_transits(...)
```

No `client.get_natal()` call is present in the day path.

### CHECK 2 — Day path uses `normalize_day()` and `score_day()`

Status: OK.

The production path now does:

```python
natal_context_dict = natal_context.model_dump(by_alias=False)
signals = normalization_service.normalize_day(natal_context_dict, transits)
scoring_result = scoring_service.score_day(signals)
```

This satisfies the Wave 3 split between natal context and daily transits.

### CHECK 3 — Yesterday delta path also uses `normalize_day()`

Status: OK.

`_get_yesterday_signals()` receives `natal_context_dict` and uses:

```python
y_signals = normalization_service.normalize_day(
    natal_context=natal_context_dict,
    transits=y_transits,
)
```

So DayDelta no longer re-enters the legacy raw natal+transits normalize path.

### CHECK 4 — Today cache is keyed by `profile_hash`

Status: OK.

`TodayService` computes:

```python
profile_hash = NatalContextService.compute_profile_hash(profile)
```

and cache lookup/upsert use:

```python
_get_cached_payload(user_id, target_date, profile_hash)
_cache_payload(user_id, target_date, payload, profile_hash)
```

This preserves the intended behavior: if birth data changes, profile hash changes, and the previous day cache entry is no longer returned.

### CHECK 5 — Debug prints removed from `day.py`

Status: OK.

The noisy `print(...)` calls around onboarding/birth coordinate checks were removed.

### CHECK 6 — Payload shape preserved

Status: OK by code and test intent.

The builder still returns `TodayPayload` with existing fields:

- `meta`
- `date`
- `title`
- `headline`
- `access`
- `day_status`
- `top_flags`
- `notes`
- `reading`
- `why_this_happens`
- `week_strip`
- `important_today`

## 4. Tests reviewed

### `test_wave3_day_pipeline_reuse.py`

New test module contains four acceptance-style checks:

1. second day call skips natal sidecar;
2. profile hash changes after birth profile edit;
3. payload has expected fields;
4. day client does not call `get_natal()` directly.

This is useful coverage and should stay.

## 5. Test-hardening follow-up

### FOLLOW-UP 1 — Cache-hit test should isolate natal-context cache from TodayPayload cache

Current `test_second_day_call_skips_natal_sidecar()` does:

1. first call for date `D`;
2. second call for the same date `D`;
3. asserts natal sidecar was not called on the second call.

But the second call can return from `TodayPayloadCache` before reaching `NatalContextService`. This proves “day payload cache hit skips everything”, not specifically “natal context cache hit skips natal sidecar”.

Recommended stronger test:

1. Call day for `2026-06-11` to build `NatalChartCache` and `TodayPayloadCache`.
2. Call day for `2026-06-12` so TodayPayload cache misses, but NatalChartCache hits.
3. Assert:
   - `natal_context_service.get_solarsage_client().get_natal` is not called;
   - `today_service.get_solarsage_client().get_transits` is called.

This directly proves Wave 3 acceptance.

### FOLLOW-UP 2 — Profile-change test should build old TodayPayload first

Current `test_profile_change_causes_today_cache_miss()` changes profile fields and checks that old/new hash differ, but it does not build an old TodayPayload before the profile change.

Recommended stronger test:

1. Build day payload for original profile.
2. Assert a `TodayPayloadCache` row exists with `original_hash`.
3. Change birth data.
4. Build same date again.
5. Assert old cache row was not used, and either:
   - new payload has `meta.cached is False`; or
   - new `TodayPayloadCache` row exists with `new_hash`.

This directly proves “day rebuilds if birth profile changes”.

## 6. Non-blocking notes

### NOTE 1 — `day.py` profile check still assumes `user.profile` exists before null check

Current code computes:

```python
has_birth_coords = (
    user.profile.birth_lat is not None and user.profile.birth_lon is not None
)
```

before checking `not user.profile`.

If `require_session` can ever return a user without profile, this can raise `AttributeError` instead of `422 NOT_ONBOARDED`.

This is not caused by Wave 3 and may be covered by existing assumptions, but safer code would be:

```python
if not user.profile:
    raise 422
has_birth_coords = user.profile.birth_lat is not None and user.profile.birth_lon is not None
```

### NOTE 2 — Commit message test evidence not independently verified through CI

Commit message reports `93 tests passed, 0 failed`. I did not verify CI status through GitHub checks in this review. Treat the commit-local evidence as accepted unless the project requires CI artifact proof.

## 7. Acceptance decision

Accepted for Wave 3 code path.

No production-path blocker found. Add the two test-hardening improvements before final merge if this branch is going through a strict evidence gate; otherwise they can be tracked as a small follow-up cleanup.
