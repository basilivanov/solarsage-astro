# Wave 12 Rework 02 TZ — Remove Test-Aware Runtime Logic and Stale Fixtures

Date: 2026-07-08
Status: ready for coder
Owner: architect
Coder model: Flash 3.5
Branch: `main`
Reviewed commit: `e0e1832`
Review: `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/04_rework_01_review.md`
Report path: append to `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/01_agent_report.md`

## Goal

Finish Wave 12 cleanly: product code must not inspect mocks, validation must only allow facts supported by row evidence, prompts/tests/fixtures must not keep old product-copy templates, and the commit must not include unrelated Wave 11 artifacts.

Do not push.

## Read First

- `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/00_TZ.md`
- `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/02_arch_review.md`
- `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/03_rework_01_TZ.md`
- `docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/04_rework_01_review.md`

## Required Fixes

### 1. Remove mock introspection from product code

Modify:

```text
apps/api/app/services/today_interpretation_service.py
```

Required:

- Delete all `is_mocked`, `is_chart_mocked`, `hasattr(..., "mock")`, `hasattr(..., "assert_called")` checks.
- Product behavior must be based on explicit runtime configuration and data only.
- A good default:
  - `has_llm_keys = bool(settings.openrouter_api_key or settings.anthropic_api_key or getattr(settings, "deepseek_api_key", ""))`
  - call LLM only when `has_llm_keys` is true;
  - if false, keep unavailable fallback text.

Tests that need LLM output must patch keys explicitly and patch/fake LLM output explicitly. Product code must not detect that.

### 2. Remove global autouse LLM mock

Modify:

```text
apps/api/tests/conftest.py
apps/api/tests/test_today_concrete_advice.py
```

Required:

- Delete `_mock_llm_interpretations` autouse fixture.
- In shared test settings, force all LLM keys to empty so normal endpoint/cache tests cannot hit the network:
  - `openrouter_api_key = ""`
  - `anthropic_api_key = ""`
  - `deepseek_api_key = ""` if this setting exists.
- In tests that need generated wording, patch:
  - a fake key, e.g. `settings.openrouter_api_key = "test-key"`;
  - `LLMService.generate_concrete_advice` / `generate_planet_interpretations` to deterministic fake output.
- Add a direct no-key test proving all concrete advice rows stay `Рекомендация временно недоступна.` and no old template appears.

### 3. Tighten evidence validation

Modify:

```text
apps/api/app/services/today_interpretation_service.py
apps/api/tests/test_today_concrete_advice.py
```

Required:

- Remove static `PLANET_TO_SPHERES_MAP` planet defaults from `validate_row_text()`.
- Allowed planets/aspects/houses for validation must come from `row.evidence` only.
- If row evidence has no planets/aspects/houses, LLM text must not mention any known planet/aspect/house.
- Add tests:
  - text mentioning a planet from evidence passes;
  - text mentioning a planet not in evidence fails;
  - text mentioning a default sphere planet without evidence fails.

### 4. Remove remaining hardcoded summary copy

Modify:

```text
apps/api/app/services/today_interpretation_service.py
```

Required:

- Remove `summary="особое влияние дня"`.
- For top flag facts, either:
  - omit summary / use `None` if schema allows it; or
  - use a factual, non-forecast string derived from the signal type, e.g. `транзитный аспект`.
- Keep prefix stripping for visible planet names.

### 5. Make concrete advice icon fallback safe

Modify:

```text
components/today/concrete-day-advice.tsx
__tests__/components/TodayScreen.test.tsx
```

Required:

- Do not render unknown `row.iconName` raw.
- Use a neutral fallback icon such as `•`, `◦`, or a safe lucide icon.
- Add/update a test proving `briefcase` / `building` / an unknown semantic key is not visible as raw text.

### 6. Remove recommendation examples from LLM prompt

Modify:

```text
apps/api/app/services/llm_service.py
```

Required:

- Replace the full JSON recommendation example with schema-only shape or neutral placeholders.
- Do not include complete advice sentences.

Allowed example:

```text
Верни JSON-объект ровно такого вида:
{"work":"<русский текст>", "money":"<русский текст>", ...}
```

### 7. Update mock visual fixtures and frontend tests

Modify:

```text
e2e/mock-visual/fixtures/day-2026-07-05.ts
__tests__/components/TodayScreen.test.tsx
```

Required for `day-2026-07-05.ts`:

- `contractVersion: 3`
- `promptVersion: 2`
- `contentVersion: 3`
- `concreteAdvice.rows[].iconName` uses semantic names, not emojis.
- Advice row texts are sentinel backend-owned fixture strings, not old product templates.
- `daySummary.statusLine` and facts contain sentinel/factual strings, not:
  - `день на твоей стороне`
  - `подводи итоги`
  - `особое влияние дня`

Required for component tests:

- Use semantic icon names in fixtures.
- Use sentinel backend-owned text, e.g. `СЕНТИНЕЛ БЭКЕНДА ДЛЯ ОТНОШЕНИЙ`.
- Assert sentinel text is rendered verbatim.
- Assert raw semantic icon names are not rendered.

### 8. Remove unrelated Wave 11 artifact churn from this commit

Required:

- Restore files under:

```text
docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03/
```

to their state before `e0e1832`, unless there is a specific Wave 12 reason. There should not be one.

Use non-destructive git commands carefully; do not touch unrelated user files.

## Required Gates

Run and report exact results:

```bash
rg -n "hasattr\(llm_service\.generate_.*mock|assert_called|is_mocked" apps/api/app -S
```

Expected: no output.

```bash
rg -n "Сократи траты|Дела идут со скрипом|Сегодня акцент через|день на твоей стороне|подводи итоги|без взлётов|особое влияние дня|Фокусируйся на текущих|Приобретай только|Взвешивай все последствия" apps/api/app apps/api/tests __tests__ e2e components lib -S
```

Expected: no output, except if a string appears only inside this work-doc directory; avoid scanning `docs/work`.

```bash
rg -n "contractVersion: 1|promptVersion: 1|contentVersion: 1|iconName: \"💼\"|iconName: \"💰\"|iconName: \"📝\"|iconName: \"💖\"|iconName: '💖'" e2e/mock-visual __tests__/components/TodayScreen.test.tsx -S
```

Expected: no output for the Wave 12 touched fixtures/tests.

```bash
cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py -q
cd apps/api && .venv/bin/pytest tests/test_day_endpoints.py tests/integration/test_cache.py tests/integration/test_locked_day.py tests/integration/test_user_flow.py -q
npx vitest run __tests__/components/TodayScreen.test.tsx
pnpm contracts:check
pnpm build
git diff --check 50f6150..HEAD
```

If Playwright server on 7777 is still running and current:

```bash
E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
```

If not running, report skipped.

Also report:

```bash
git diff --name-only HEAD~1..HEAD -- docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03
```

Expected: no output in the final rework commit.

## Commit Requirements

Create a new rework commit on `main`.

Do not push.

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
  -d '{"prompt":"Wave 12 Rework 02 ready for architect review. Report: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/01_agent_report.md. Review: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/04_rework_01_review.md. Rework TZ: docs/work/2026-07-08_day-backend-owned-interpretation-wave-12/05_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```

Replace `<commit_sha>` with the actual final commit SHA.
