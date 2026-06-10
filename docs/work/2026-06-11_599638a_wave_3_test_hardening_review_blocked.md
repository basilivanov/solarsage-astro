# Review Blocked: 599638a — Wave 3 Test Hardening

Date: 2026-06-11
Status: REVIEW BLOCKED — COMMIT NOT VISIBLE TO CONNECTOR
Target branch: `feat/natal-full-report`
Requested commit: `599638a`
Previous Wave 3 review: `docs/work/2026-06-11_dbfb322_wave_3_day_pipeline_reuse_review.md`

## 1. Request

The requested follow-up review was for commit `599638a`, described as implementing both Wave 3 test-hardening follow-ups:

1. Different-date scenario:
   - same-date TodayPayload + NatalContext cache hit;
   - different-date TodayPayload miss + NatalContext hit;
   - natal sidecar not called;
   - transit sidecar called;
   - `meta.cached=False`.

2. End-to-end rebuild after birth profile change:
   - build payload with original birth data;
   - verify old `TodayPayloadCache` with original hash;
   - change birth lat/lon/tz;
   - verify new hash;
   - call `get_today_payload()` again;
   - verify natal sidecar called again;
   - verify `meta.cached=False`;
   - verify new cache row exists and old row is not served.

User reported: `74 natal-теста все зелёные`.

## 2. What I could verify

I attempted to fetch the commit directly:

```text
fetch_commit(599638a)
```

Result:

```text
No commit found for SHA: 599638a
```

I also attempted to fetch the target test file from `feat/natal-full-report`:

```text
apps/api/tests/test_wave3_day_pipeline_reuse.py
```

The connector returned the older version from the previous Wave 3 commit. It still contained the previous weaker tests:

- `test_second_day_call_skips_natal_sidecar`
- `test_profile_change_causes_today_cache_miss`

It did not show the newly claimed tests:

- `test_same_date_both_caches_hit`
- `test_different_date_today_miss_natal_hit`
- `test_rebuild_after_profile_change_end_to_end`

Search for the new test names also returned no results through the connector at review time.

## 3. Verdict

REVIEW BLOCKED.

I cannot accept or reject commit `599638a` because it is not visible through the GitHub connector yet, and the branch content visible to the connector still appears to be the older test file.

This is not a code rejection. It is an evidence/access issue.

## 4. Expected acceptance criteria once commit is visible

When `599638a` becomes visible, the review should verify:

### Acceptance 1 — Same-date cache hit

Required proof:

- Build payload for date A.
- Call payload for date A again.
- Assert:
  - TodayPayload cache hit;
  - NatalContext cache hit;
  - no natal sidecar call;
  - no transit sidecar call if TodayPayload is returned before transit fetch;
  - `payload.meta.cached is True`.

### Acceptance 2 — Different-date TodayPayload miss + NatalContext hit

Required proof:

- Build payload for date A.
- Call payload for date B.
- Assert:
  - TodayPayload cache misses because date differs;
  - NatalContext cache hits because profile hash is the same;
  - natal sidecar is not called;
  - transit sidecar is called;
  - `payload.meta.cached is False`.

### Acceptance 3 — Profile-change rebuild end-to-end

Required proof:

- Build payload for original birth profile.
- Assert cache row exists with `original_hash`.
- Change birth lat/lon/tz.
- Assert `new_hash != original_hash`.
- Call same date again.
- Assert:
  - old TodayPayload cache is not served;
  - natal context rebuild occurs or new active context is created;
  - natal sidecar is called again;
  - new TodayPayload cache row exists with `new_hash`;
  - old row may remain in DB but is not returned;
  - `payload.meta.cached is False`.

## 5. Required next step

Re-run this review when one of these is available:

1. full commit SHA for `599638a`;
2. visible branch head containing the new tests;
3. PR/diff URL for the follow-up commit;
4. pasted diff for `apps/api/tests/test_wave3_day_pipeline_reuse.py`.

Until then, the previous Wave 3 status remains:

```text
ACCEPTED WITH TEST-HARDENING FOLLOW-UP
```

not fully upgraded to unconditional acceptance.
