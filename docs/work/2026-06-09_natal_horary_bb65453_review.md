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

## Residual notes

No blockers found.

Recommended future hardening, not required for this acceptance:

1. Add an integration/component test for successful horary create flow: submit valid question → `createHoraryQuestion` called → processing item appears.
2. Add a small test for successful polling start after create if test harness allows it.
3. In `HoraryForm`, invalid reason priority currently shows no-credit before missing text/place. If product wants first-empty-form click to say `Напиши вопрос` first, adjust priority later.
4. Consider reducing/renaming technical planet score pills in the natal UI if screenshots still feel too technical.

## Final decision

ACCEPTED WITH NOTES.

The previous blockers are fixed: planet cards no longer expose English signs, natal no-English regression coverage exists, and horary invalid/API-error submit states have frontend tests. The remaining items are follow-up hardening, not acceptance blockers.
