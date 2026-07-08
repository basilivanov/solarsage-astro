# Wave 12 Rework 01 TZ — Remove Template Fallbacks and Fix Contract Rendering

Date: 2026-07-08
Status: ready for coder
Owner: architect
Coder model: Flash 3.5
Branch: `main`
Reviewed commit: `35ac579`
Review: `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/02_arch_review.md`
Report path: append to `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/01_agent_report.md`

## Goal

Fix Wave 12 so it actually satisfies the architecture: active source must not contain old forecast-copy templates, product services must not branch on pytest, fallback output must be unavailable/non-forecast, and frontend must render semantic icon names as icons instead of text.

Do not push.

## Read First

- `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/00_TZ.md`
- `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/02_arch_review.md`

## Required Fixes

### 1. Remove old advice templates from backend active source

Modify:

```text
apps/api/app/services/today_interpretation_service.py
```

Required:

- Delete `SPHERE_ADVICE_TEXTS`.
- Delete all old copied product forecast strings:
  - `Дела идут со скрипом...`
  - `Сократи траты...`
  - and every other row text copied from Wave 11 frontend templates.
- If LLM is unavailable, do not synthesize forecast advice. Keep:

```text
Рекомендация временно недоступна.
```

or another explicitly unavailable, non-forecast string.

Required behavior:

- If no LLM keys are configured, `ConcreteAdviceRow.text` remains unavailable/non-forecast.
- If LLM keys are configured and fewer than 9 valid rows are returned, raise generation failure as the original TZ allowed.
- Do not cache old template text.

### 2. Remove pytest detection from product code

Modify:

```text
apps/api/app/services/today_interpretation_service.py
```

Required:

- Remove `import sys` for test detection.
- Remove checks like:

```python
"pytest" in sys.modules
any("pytest" in arg for arg in sys.argv)
```

Tests must patch `LLMService.generate_concrete_advice` / `generate_planet_interpretations` explicitly when they need deterministic LLM output.

Production behavior must not depend on the test runner.

### 3. Strengthen LLM validation

Modify:

```text
apps/api/app/services/today_interpretation_service.py
apps/api/app/services/llm_service.py
apps/api/tests/test_today_concrete_advice.py
```

Required concrete advice validation:

- expected key set is exactly the 12 canonical product keys;
- missing keys are invalid;
- extra keys are invalid;
- value must be non-empty string;
- value must not contain Latin alphabet;
- value must not contain `Transit_` or `Natal_`;
- value must not mention unsupported planet/aspect/house facts.

Pragmatic implementation for unsupported facts:

- Build an allowed-token set per row from row evidence:
  - Russian planet labels for evidence planets/targets;
  - Russian aspect labels for evidence aspect types;
  - house numbers from evidence if present.
- If the LLM text mentions a known planet/aspect/house that is not in that row's allowed set, reject that row.
- Keep the validator small and test the common cases. Do not build a full NLP parser.

Required tests:

- valid all-12-key JSON passes;
- missing key fails;
- extra key fails;
- Latin text fails;
- `Transit_` / `Natal_` fails;
- hallucinated planet/aspect fails.

### 4. Remove hardcoded forecast wording from day summary builder

Modify:

```text
apps/api/app/services/today_interpretation_service.py
```

Remove or replace hardcoded forecast summaries:

- `тема дня — ...: фокус на активности`
- `подводи итоги`
- `не подписывай и не начинай`
- `особое влияние дня`

Allowed:

- deterministic factual titles:
  - `Влияние Юпитера`
  - `Убывающая Луна 56%`
  - `Луна без курса`
  - existing backend `top_flags[0].title` if passed in or rebuilt safely.
- unavailable/non-forecast summary:
  - `Сводка временно недоступна.`
- LLM-generated summary text after validation.

Do not invent action guidance in summary facts without LLM text.

Also strip prefixes before visible text:

- `Transit_Moon` -> `Луна`
- `Natal_Mars` -> `Марс`

No visible `Transit_` or `Natal_` may be produced.

### 5. Fix chart interpretation fallback

Modify:

```text
apps/api/app/services/today_interpretation_service.py
components/today/day-chart.tsx
```

Required:

- Backend must not generate local astrology fallback like:

```text
Интерпретация для Юпитер в доме 2.
```

- If LLM interpretation is absent/invalid, set:

```text
Интерпретация временно недоступна.
```

- Frontend fallback may keep the same unavailable string.

### 6. Fix concrete advice icons

Modify:

```text
components/today/concrete-day-advice.tsx
__tests__/components/TodayScreen.test.tsx
e2e/mock-visual/fixtures/day-2026-07-05.ts
```

Required:

- Real contract sends semantic `iconName` values like `briefcase`, `building`, `list-checks`.
- Do not render `row.iconName` directly as visible text.
- Map semantic icon names to visible icons.

Acceptable implementation:

- use `getIcon()` / lucide for semantic icons; or
- use a small UI-only icon/emoji map:

```ts
briefcase -> 💼
building -> 💰
list-checks -> 📝
sparkle -> 💖
leaf -> 🏃
telescope -> 💬
compass -> 🌿
target -> 🎯
hourglass -> ✈️
grid -> 🎨
layers -> 📚
zap -> 🛍️
```

This icon map is UI chrome, not forecast text, so it is allowed.

Tests must use semantic icon names and assert raw strings like `briefcase` / `building` are not visible.

### 7. Remove frontend forecast fallback copy

Modify:

```text
components/today/day-summary-card.tsx
```

Required:

- Remove fallback:

```text
без взлётов — занимайся рутиной
```

- If `daySummary.statusLine` is absent, render:

```text
Сводка временно недоступна.
```

or render nothing.

Do not add any local forecast fallback.

### 8. Clean LLM prompt examples

Modify:

```text
apps/api/app/services/llm_service.py
```

Required:

- Remove full old product-template example response from `generate_concrete_advice()`.
- Do not include `Сократи траты`, `Дела идут со скрипом`, or other old template strings in the prompt.
- Prefer a schema-only instruction:

```text
Верни JSON вида {"work":"...", "money":"...", ...}
```

or use neutral placeholders that cannot be visible forecast copy.

### 9. Update tests and fixtures so they cannot hide these bugs

Modify tests/fixtures as needed:

- `apps/api/tests/test_today_concrete_advice.py`
- `__tests__/components/TodayScreen.test.tsx`
- `e2e/mock-visual/fixtures/day-2026-07-05.ts`
- `e2e/mock-visual/day.spec.ts`

Required:

- Mock LLM explicitly for happy-path generated advice.
- Add a test for no-key/no-LLM fallback: all row texts are unavailable/non-forecast, not old advice.
- Add a test that active backend source contains no old product templates. This can be a Python test or report-only static gate, but it must be run.
- Use semantic `iconName` values in frontend fixtures, not emoji-only values.
- Update mock fixture `meta.contractVersion`, `promptVersion`, and `contentVersion` to match Wave 12 (`3`, `2`, `3`).
- Use sentinel backend-owned row text in tests to prove frontend renders payload verbatim.

## Required Gates

Run and report exact results:

```bash
rg -n "SPHERE_ADVICE_TEXTS|buildConcreteAdviceRows|planetDescription\\(|PLANET_THEME|Дела идут со скрипом|Сократи траты|Сегодня акцент через|день на твоей стороне|подводи итоги|без взлётов|Интерпретация для" components lib app apps/api/app -S
```

Expected: no output.

```bash
rg -n "pytest.*sys\\.modules|sys\\.argv|is_test_env" apps/api/app -S
```

Expected: no output.

```bash
cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py -q
cd apps/api && .venv/bin/pytest tests/test_day_endpoints.py tests/integration/test_cache.py tests/integration/test_locked_day.py tests/integration/test_user_flow.py -q
npx vitest run __tests__/components/TodayScreen.test.tsx
pnpm contracts:check
pnpm build
git diff --check 50f6150..HEAD
```

If Playwright server on 7777 is still running and current, also run:

```bash
E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
```

If not running, do not spend time on server management unless needed; report whether skipped.

## Commit Requirements

Create a new rework commit on `main`.

Do not commit unrelated untracked paths:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- `test-results/`
- `playwright-report/`

## Required Callback

At the very end, run this callback from the repo root:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 12 Rework 01 ready for architect review. Report: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/01_agent_report.md. Review: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/02_arch_review.md. Rework TZ: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```

Replace `<commit_sha>` with the actual final commit SHA.
