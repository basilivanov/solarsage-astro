# Review: Natal no-English + Horary submit tests follow-up

Date: 2026-06-09
Reviewed commit: bb65453
Previous review: `docs/work/2026-06-09_natal_redesign_horary_submit_08e5e1a_review.md`
Verdict: ACCEPTED WITH NOTES

## Scope reviewed

Commit: `bb65453`

Changed files:

- `apps/api/app/services/natal_service.py`
- `__tests__/natal/natal-no-english.test.tsx`
- `__tests__/horary/horary-form-submit.test.tsx`

This follow-up targets the two blockers from the previous review:

1. English zodiac signs still visible in natal planet cards.
2. New test coverage for natal no-English UI and horary submit states was missing from the implementation commit.

## Findings

### B1 — English signs in planet cards fixed

Status: ACCEPTED

Backend now defines `_SIGN_NOM` for nominative Russian sign names:

- `Scorpio` → `Скорпион`
- `Leo` → `Лев`
- `Libra` → `Весы`
- etc.

`_build_planets()` now uses:

```python
sign_nom = _SIGN_NOM.get(sign_en or "", sign_en or "")
sign_prep = _SIGN_RU.get(sign_en or "", sign_en or "знаке")
...
sign=sign_nom
```

So `planet.sign` is now Russian for card display, while the description still correctly uses prepositional Russian form, for example `в Скорпионе`.

This closes the visible-English-sign blocker.

### B2 — Natal no-English UI test added

Status: ACCEPTED

`__tests__/natal/natal-no-english.test.tsx` renders the natal page with Russian sign data and checks that none of the 12 English zodiac signs appear in `document.body.textContent`.

It also asserts that Russian signs such as `Скорпион`, `Лев`, and `Весы` are visible.

This is enough regression coverage for the blocker.

### B3 — Horary invalid-submit tests added

Status: ACCEPTED

`__tests__/horary/horary-form-submit.test.tsx` covers blocked reasons for invalid submit:

- missing location → `Укажи место вопроса`;
- short text → `Напиши вопрос`;
- no spendable credit → text containing `хорарный вопрос`.

This verifies that the click is no longer a silent no-op for invalid submit states.

### B4 — Horary submit API error display test added

Status: ACCEPTED

The same test file covers inline submit error display:

- `submitError` present → `horary-submit-error` is rendered;
- `submitError` null → error block is absent.

This closes the missing API-error UI coverage requested in the previous review.

## Verification evidence

User-provided local evidence:

- Frontend tests: `502 passed`.
- Backend tests: `277 passed`.

Connector-visible CI evidence:

- No GitHub Actions workflow runs were visible for `bb65453`.
- No combined GitHub status checks were visible for the commit.

## Final follow-up packet — добить перед закрытием волны

These items are not blockers for accepting `bb65453`, but should be done immediately as the final cleanup packet so the flow is fully protected.

### F1 — Successful horary create flow test

Status: REQUIRED FOLLOW-UP

Add an integration/component test proving the happy path works:

1. user enters valid text;
2. question location has lat/lon;
3. user has spendable credit;
4. click submit;
5. `createHoraryQuestion()` is called with expected payload:
   - text;
   - category if selected;
   - client local time;
   - timezone;
   - questionLat/questionLon;
   - questionLocationName;
   - idempotencyKey;
6. created question is inserted into UI/history;
7. processing card appears.

Acceptance:

- valid click is not just “not blocked”; it actually starts visible processing.
- test fails if future refactor breaks submit → create → processing.

### F2 — Successful polling start test after create

Status: REQUIRED FOLLOW-UP IF TEST HARNESS ALLOWS

Add a test that proves polling starts after successful create.

Suggested strategy:

- mock `createHoraryQuestion()` to return a `processing` question;
- mock `getHoraryQuestion()` / list refresh behavior;
- assert that polling path is invoked or that processing state remains visible and updates.

Acceptance:

- after successful create, frontend does not wait silently;
- new processing question is actively watched.

### F3 — Invalid reason priority polish

Status: REQUIRED FOLLOW-UP / PRODUCT POLISH

Current invalid reason priority in `HoraryForm` checks:

1. no credit;
2. missing place;
3. short text.

For an empty form, this may show `Укажи место вопроса` before `Напиши вопрос`.

Required behavior:

- if text is empty/too short, first show `Напиши вопрос`;
- then show missing place;
- then no credit;

or show all missing reasons at once.

Preferred simple rule:

```ts
if (text.trim().length < 5) {
  reason = "Напиши вопрос (минимум 5 символов)"
} else if (!hasQuestionPlace) {
  reason = "Укажи место вопроса"
} else if (!hasSpendableCredit) {
  reason = "Нужен доступный хорарный вопрос"
}
```

Acceptance:

- first empty-form submit tells user to write the question first;
- missing place is shown when text is valid but place is missing;
- no-credit is shown when text/place are valid but balance is missing.

### F4 — Natal technical score visual cleanup

Status: REQUIRED VISUAL REVIEW FOLLOW-UP

Current redesign is accepted, but the page may still feel technical if planet/sphere score pills are visually prominent.

Required check:

- review actual mobile screenshots after the redesign;
- if `+4.96` / numeric score pills still make the landing feel like debug output, hide or soften them;
- prefer human labels over raw scores.

Acceptance:

- natal landing should feel like a premium teaser, not a scoring dashboard.

## Final decision

ACCEPTED WITH NOTES.

The previous blockers are fixed: planet cards no longer expose English signs, natal no-English regression coverage exists, and horary invalid/API-error submit states have frontend tests.

Before fully closing this wave, complete the `Final follow-up packet`: happy-path horary create test, polling-start test if feasible, invalid-reason priority polish, and visual check for technical score pills in natal.
