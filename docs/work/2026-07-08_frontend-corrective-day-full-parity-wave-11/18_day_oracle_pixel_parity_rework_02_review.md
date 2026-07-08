# Wave 11 Day Oracle Pixel Parity Rework 02 Review

Status: **REWORK REQUIRED**

Reviewed commits:

- Implementation: `cc2af5a0391fad7c203a0fc57ca559c2b8ff9879`
- Report: `7615705`

## Summary

Rework 02 improved the visible shell:

- concrete advice now uses oracle emoji icons and row layout;
- chart visual shell is much closer to the 3001 oracle;
- chart tap no longer shows the obvious blue focus rectangle in the captured candidate screenshot.

However, the result is **not accepted**. The concrete advice data/view-model still violates the product oracle contract, and the generated evidence summary is invalid.

## Findings

### P0 — Concrete advice still renders placeholder rows instead of the 3001 product contract

Files:

- `components/today/concrete-day-advice.tsx`

Problem:

- `Verdict` still includes `unavailable`.
- Missing canonical product buckets render `Нет отдельного сигнала на эту сферу.`
- Those rows get gray placeholder dots/backgrounds instead of oracle neutral/product rows.
- Header counts only count `realRows`, so a supportive day can still show `0 благоприятно`.

This reproduces the user's complaint in the candidate evidence:

- candidate screenshot shows `0 благоприятно / 4 осторожно`;
- several rows show `Нет отдельного сигнала на эту сферу.`;
- 3001 oracle shows complete product copy/verdict rows for all 12 spheres.

Required direction:

- Remove `unavailable` from concrete advice rows.
- Every one of the 12 canonical product spheres must render an oracle product text and one of `good | caution | avoid | neutral`.
- Missing/sparse real sphere score data must fall back to oracle neutral/product logic, not placeholder logic.
- Counts must be derived from the displayed row verdicts, not from `isReal` rows only.
- The adapter may use real `dayStatus`, `sphereScores`, `planetInfluences`, `topFlags`, and `notes`; it must not import runtime mocks/static API fixtures.

### P0 — Concrete advice ignores real day context that would prevent incoherent counts

Files:

- `components/today/today-screen.tsx`
- `components/today/concrete-day-advice.tsx`

Problem:

- `today-screen.tsx` passes `topFlags`, `notes`, and `sphereScores`.
- `ConcreteDayAdvice` currently uses only `sphereScores`.
- It does not receive/use `dayStatus` or `planetInfluences`, even though the real payload already has them.

This is why a day marked `supportive` can still display `0 благоприятно` in the concrete advice header.

Required direction:

- Pass `dayStatus` and `planetInfluences` into `ConcreteDayAdvice`.
- Use them in the view-model as real signal context.
- A `supportive` day with sparse sphere scores must not collapse into `0 благоприятно` unless all real signals are explicitly caution/avoid.

### P1 — Evidence summary is invalid

Files:

- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-02/summary.json`
- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/capture-rework-02.cjs`

Problems visible in `summary.json`:

- `sphereIcons` has 11 icons, not 12.
- `candidate.headerCounts` is `5 ИЮЛ · ВОСКРЕСЕНЬЕ`, which is the day summary date, not concrete advice counts.
- `oracle.popoverTitle` and `candidate.popoverTitle` are different because the script clicked different/data-dependent planets, yet the report described the evidence as parity.

Required direction:

- Make capture selectors scoped and deterministic.
- Add test ids/data attrs if useful for the semantic/test contract.
- Summary must include:
  - exactly 12 row objects for oracle and candidate: `{ icon, label, text, status }`;
  - concrete header counts parsed from the concrete advice section only;
  - collapsed/expanded row counts;
  - toggle text before/after;
  - chart legend labels;
  - selected candidate planet popover details and focus/tap-highlight styles.
- Do not call data-dependent oracle/candidate planet titles a mismatch unless the same data is being used.

### P1 — Tests still allow placeholder advice rows

Files:

- `e2e/mock-visual/day.spec.ts`
- component/unit tests if added

Problem:

The strengthened e2e test verifies emoji order and row count, but it does not reject:

- `data-status="unavailable"`;
- `Нет отдельного сигнала...`;
- `Данные появятся...`;
- `0 благоприятно` on a supportive fixture.

Required direction:

- Add assertions that no concrete advice row has `data-status="unavailable"`.
- Add assertions that placeholder texts are absent.
- For the existing supportive mock fixture, assert the concrete advice good count is greater than zero.
- Add a small unit test for the view-model if the function can be exported without exposing production internals.

### P2 — Hygiene gate fails

Command:

```bash
git diff --check HEAD~2..HEAD
```

Current result includes trailing whitespace in:

- `components/today/concrete-day-advice.tsx`
- `e2e/mock-visual/day.spec.ts`
- new docs files

Fix before the next report.

## Decision

Rework 02 is not accepted. Continue with a narrow Rework 03 focused on:

1. concrete advice view-model/data contract;
2. evidence capture correctness;
3. tests that reject placeholders and incoherent supportive-day counts;
4. whitespace hygiene.

Do not rework unrelated day sections.

