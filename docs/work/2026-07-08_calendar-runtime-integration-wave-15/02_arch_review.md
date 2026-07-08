# Wave 15 Calendar Runtime Integration Review

Date: 2026-07-08
Reviewed commit: `786c967`
Decision: ACCEPTED FOR RUNTIME INTEGRATION

## Summary

Wave 15 successfully deployed the accepted calendar contract/frontend work into the canonical runtime.

Accepted outcomes:

- `main` is pushed to `origin/main`.
- `solarsage-api.service`, `solarsage-frontend.service`, and `nginx.service` are active.
- `http://127.0.0.1:8000/api/calendar?month=2026-07` now returns `meta.contractVersion = 2`.
- Lunar fields for `2026-07-08` are non-null.
- `http://127.0.0.1:3002/calendar` returns `200 OK`.
- Runtime real-auth calendar e2e passes.
- Runtime mock-visual calendar e2e passes.

## Architect Verification

```bash
systemctl is-active solarsage-api.service solarsage-frontend.service nginx.service
```

Result: exit 0, all active.

```bash
curl -s http://127.0.0.1:8000/api/health
```

Result: exit 0. Note: response still reports `git_sha=unknown`; this is a health metadata gap, not a calendar runtime blocker.

Authenticated API check for `tg_user_id=833478509`, username `basil_ivanov`:

```json
{
  "meta": {
    "schemaVersion": "calendar/v1",
    "contractVersion": 2
  },
  "selected": {
    "2026-07-08": {
      "dayStatus": "supportive",
      "access": {
        "state": "full",
        "reason": "active_referral_days",
        "referralDaysLeft": 4,
        "accessUntil": "2026-07-11"
      },
      "lunar": {
        "phase": "waning_crescent",
        "phaseIndex": 7,
        "phaseLabel": "убыв. серп",
        "illumination": 39,
        "moonSignLabel": "Овен",
        "lunarDay": 24,
        "voidOfCourse": false
      }
    },
    "2026-07-12": {
      "dayStatus": "steady",
      "access": {
        "state": "locked",
        "reason": "outside_access_window",
        "accessUntil": "2026-07-11"
      },
      "lunar": {
        "phase": "waning_crescent",
        "phaseIndex": 7,
        "illumination": 6,
        "lunarDay": 28
      }
    }
  }
}
```

This confirms Sunday is calculated and present in the cache/API; it is locked for Basil because referral access ends on `2026-07-11`.

```bash
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/calendar.spec.ts
```

Result: exit 0, `2 passed`.

```bash
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0, `12 passed`.

## Review Notes

- The e2e changes in `786c967` are harness-only and appropriate:
  - stable test IDs replace ambiguous role selectors;
  - production-runtime readiness timeout is widened;
  - mock fixtures cover Next prefetches for July day routes.
- The nginx localhost-only proxy fix is acceptable under the TZ because the required loopback smoke initially hit the wrong default site while the canonical services were healthy.
- The runtime screenshots show the deployed 3002 calendar now has the backend-owned lunar contract and presentation.

## Residual Visual Work

Runtime integration is accepted, but the broader "1:1 with 3001" calendar goal still has visible style gaps:

- day-mode cell secondary markers on 3002 still differ from the oracle;
- moon-mode phase glyph colors/contrast are close but not yet visually identical to 3001;
- synthetic-user screenshots include expected access-state differences, so final visual review must use a controlled user/access scenario and classify data differences separately from styling differences.

Those gaps should be handled in the next visual-parity wave, not by changing Wave 15 deploy/integration work.
