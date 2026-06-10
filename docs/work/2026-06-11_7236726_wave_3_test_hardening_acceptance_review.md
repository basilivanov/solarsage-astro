# Acceptance Review: 7236726 — Wave 3 Test Hardening

Date: 2026-06-11
Status: ACCEPTED
Reviewed commit: `72367264993a2d8e423736980f186087027e07f5`
Branch: `feat/natal-full-report`
Supersedes blocked review: `docs/work/2026-06-11_599638a_wave_3_test_hardening_review_blocked.md`
Previous Wave 3 review: `docs/work/2026-06-11_dbfb322_wave_3_day_pipeline_reuse_review.md`

## 1. Scope reviewed

This commit addresses the two test-hardening follow-ups from the Wave 3 day pipeline reuse review:

1. Prove the different-date scenario:
   - date A builds/caches `NatalContext` and `TodayPayload`;
   - date B misses `TodayPayloadCache` but hits `NatalContext`;
   - natal sidecar is not called;
   - transit sidecar is called;
   - payload is freshly generated with `meta.cached=False`.

2. Prove profile-change rebuild end-to-end:
   - build payload with original birth data;
   - verify cache with original `profile_hash`;
   - change birth lat/lon/tz;
   - verify `profile_hash` changes;
   - call `get_today_payload()` again;
   - verify natal sidecar is called again;
   - verify `meta.cached=False`;
   - verify new cache row exists with new hash while old row remains but is not served.

Commit message reports: `74 natal tests all passing`.

## 2. Verdict

ACCEPTED.

The two follow-up test gaps from `dbfb322` are closed. Wave 3 can now be considered accepted without the previous “test-hardening follow-up” caveat.

## 3. Checks

### CHECK 1 — Same-date both-caches-hit test

Status: OK.

The old weaker `test_second_day_call_skips_natal_sidecar` was replaced by:

```python
test_same_date_both_caches_hit
```

It now verifies:

- first call is fresh and calls natal sidecar;
- second call for the same date returns cached TodayPayload;
- natal sidecar is not called on second call;
- transit sidecar is not called on second call;
- `payload2.meta.cached is True`.

This correctly proves the full same-date cache hit path.

### CHECK 2 — Different-date TodayPayload miss + NatalContext hit

Status: OK.

New test:

```python
test_different_date_today_miss_natal_hit
```

It verifies the important Wave 3 scenario:

- date A builds natal context and TodayPayload;
- date B is a TodayPayload cache miss because date differs;
- NatalContext is reused because profile hash/user are the same;
- natal sidecar is not called on date B;
- transit sidecar is called on date B;
- `payload_b.meta.cached is False`;
- payload date equals date B.

This directly closes Follow-up 1.

### CHECK 3 — Profile hash baseline test retained

Status: OK.

`test_profile_change_causes_today_cache_miss` was narrowed to the baseline invariant:

- birth-data change changes `profile_hash`.

This is good: it keeps the simple hash invariant separate from the end-to-end rebuild test.

### CHECK 4 — End-to-end rebuild after birth profile change

Status: OK.

New test:

```python
test_rebuild_after_profile_change_end_to_end
```

It now proves the full behavior requested in the prior review:

1. build payload with original profile;
2. verify cache entry exists with `original_hash`;
3. change `birth_lat`, `birth_lon`, `birth_tz`;
4. verify `new_hash != original_hash`;
5. verify old cache remains and new cache does not exist yet;
6. call `get_today_payload()` again;
7. verify natal sidecar is called again;
8. verify fresh payload with `meta.cached=False`;
9. verify new cache exists with `new_hash`;
10. verify old cache row still exists but is not used by the new hash path.

This directly closes Follow-up 2.

## 4. Remaining notes

### NOTE 1 — Evidence is commit-message/local evidence

The commit message reports `74 natal tests all passing`. I did not independently inspect CI artifacts through GitHub Actions in this review.

This is acceptable for this review pass because the diff itself contains the required tests and the previous issue was test coverage shape, not production code correctness.

### NOTE 2 — Previous blocked review is superseded

The earlier blocked review existed only because the short commit SHA was not pushed/visible. Since `7236726` is now visible and contains the expected changes, the blocked status is superseded by this acceptance review.

## 5. Acceptance decision

Accepted.

Wave 3 day pipeline reuse is now accepted both by production-path code review and by the hardened acceptance tests.
