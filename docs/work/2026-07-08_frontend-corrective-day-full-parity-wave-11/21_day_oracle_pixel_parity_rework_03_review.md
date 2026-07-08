# Wave 11 Day Oracle Pixel Parity Rework 03 Review

Status: **REWORK REQUIRED**

Reviewed commits:

- Implementation: `ab145535359a16f8ef94a73748232e0c25a29879`
- Report: `b6f2275`

## Accepted Progress

- `ConcreteDayAdvice` now receives `dayStatus` and `planetInfluences`.
- Concrete advice no longer renders `data-status="unavailable"`.
- Rework 03 candidate evidence has 12 row objects, `placeholderTextCount: 0`, `unavailableStatusCount: 0`, and `goodCount: 4`.
- Chart tap highlight/focus evidence remains clean.

## Blocking Finding

### P0 — English text leaked into visible concrete advice copy

Files:

- `components/today/concrete-day-advice.tsx`
- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03/summary.json`

Evidence:

```text
Сократи траты — день для financial discipline
```

This is visible product copy in the `Деньги` row. It violates the Russian UI contract and would be visible in Telegram.

Required fix:

- Replace with the oracle Russian text: `Сократи траты — день для финансовой дисциплины`.
- Add a test that concrete advice row texts contain no Latin alphabet words.
- Regenerate Rework 03 evidence summary/screenshots after the fix.

## Non-Blocking Cleanup

The module contract comments in `components/today/concrete-day-advice.tsx` still mention unavailable rows. Update those comments so they match the new contract.

The report currently names `f1ec4a9` as HEAD in its metadata, but final report commit is `b6f2275`. Update the report metadata in the follow-up report or amend if you choose to amend.
