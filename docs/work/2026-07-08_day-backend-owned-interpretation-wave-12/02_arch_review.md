# Wave 12 Architect Review — Rework Required

Reviewed commit: `35ac579`
Branch: `main`
Status: **REWORK REQUIRED**

## Findings

### 1. Critical — backend still hardcodes old forecast templates and caches them

`apps/api/app/services/today_interpretation_service.py` defines `SPHERE_ADVICE_TEXTS` with the old frontend product-copy strings and writes those strings into `row.text` when LLM is unavailable.

Evidence:

- `apps/api/app/services/today_interpretation_service.py:118`
- `apps/api/app/services/today_interpretation_service.py:121`
- `apps/api/app/services/today_interpretation_service.py:127`
- `apps/api/app/services/today_interpretation_service.py:371`
- `apps/api/app/services/today_interpretation_service.py:373`

This directly violates the TZ:

- "Do not insert old frontend product templates."
- fallback must be non-forecast unavailable text;
- frontend/backend forecast text must be backend payload + LLM interpretation from real evidence, not copied templates.

The report confirms this path was used in tests: "fallback path ... safely populated rows with the high-quality Russian template advice".

### 2. Critical — production service branches on `pytest` and changes product behavior

`TodayInterpretationService.build()` checks `sys.modules` / `sys.argv` for pytest and changes LLM behavior.

Evidence:

- `apps/api/app/services/today_interpretation_service.py:343`
- `apps/api/app/services/today_interpretation_service.py:346`
- `apps/api/app/services/today_interpretation_service.py:348`

Production code must not contain test-runner detection. Tests should patch/mask dependencies explicitly. This branch also hides the real no-key path and allowed the old forecast template fallback to pass integration tests.

### 3. Important — LLM output validation is far weaker than required

The TZ required:

- all 12 keys present;
- values non-empty Russian;
- reject Latin alphabet;
- reject `Transit_` / `Natal_`;
- reject unsupported planet/aspect/house facts.

Current merge validates only "string + non-empty + no Latin" for whatever keys happen to be present.

Evidence:

- `apps/api/app/services/today_interpretation_service.py:355`
- `apps/api/app/services/today_interpretation_service.py:358`
- `apps/api/app/services/today_interpretation_service.py:362`
- `apps/api/app/services/today_interpretation_service.py:363`

Missing keys and hallucinated astrology are not rejected at the validation boundary.

### 4. Important — day summary still contains hardcoded forecast copy

The new backend service still creates visible interpretive summary text locally:

- `тема дня — ...: фокус на активности`
- `подводи итоги`
- `не подписывай и не начинай`
- `особое влияние дня`

Evidence:

- `apps/api/app/services/today_interpretation_service.py:411`
- `apps/api/app/services/today_interpretation_service.py:436`
- `apps/api/app/services/today_interpretation_service.py:456`
- `apps/api/app/services/today_interpretation_service.py:468`

The TZ says LLM owns wording and backend owns deterministic evidence/verdict. If summary facts are not LLM-generated, they must be factual titles or non-forecast unavailable summaries, not old-style recommendation text.

### 5. Important — day summary can leak raw `Transit_` / `Natal_` names

The top-flag summary fact uses `top_sig.planet` and `top_sig.target_planet` directly with `PLANET_LABELS_RU.get(...)`. If signals contain `Transit_Moon` / `Natal_Mars`, the raw prefixed names are shown.

Evidence:

- `apps/api/app/services/today_interpretation_service.py:461`
- `apps/api/app/services/today_interpretation_service.py:467`

This reintroduces the known `Transit_`/`Natal_` UI risk.

### 6. Important — chart fallback still generates local astrology text

When chart LLM is unavailable and no chart keys are present, the backend writes:

```text
Интерпретация для {planet} в доме {house}.
```

Evidence:

- `apps/api/app/services/today_interpretation_service.py:512`
- `apps/api/app/services/today_interpretation_service.py:517`

The TZ explicitly said missing chart interpretation should be unavailable text, not a local generated astrology phrase.

### 7. Important — frontend renders semantic `iconName` as visible text

The backend contract/TZ uses semantic names like `briefcase`, `building`, `list-checks`. `ConcreteDayAdvice` renders `row.iconName` directly:

- `components/today/concrete-day-advice.tsx:115`

With real backend output, users will see `briefcase`, `building`, etc. instead of icons. Current tests hide this because fixtures use emoji strings instead of contract-like semantic icon names.

### 8. Important — frontend still has forecast fallback copy

`DaySummaryCard` keeps a forecast fallback:

- `components/today/day-summary-card.tsx:37`

```text
без взлётов — занимайся рутиной
```

If backend data is missing, the UI still fabricates forecast text. Fallback must be absent or non-forecast unavailable copy.

### 9. Important — LLM prompt examples hardcode old forecast templates

`generate_concrete_advice()` includes a full example response copied from the old product templates, including `Сократи траты...`.

Evidence:

- `apps/api/app/services/llm_service.py:1024`
- `apps/api/app/services/llm_service.py:1027`

This anchors the model on the exact hardcoded strings we are trying to remove. Use schema-only instructions or generic non-product examples that cannot leak old copy.

## Verification Run By Architect

```bash
git diff --check 50f6150..HEAD
```

Result: passed.

```bash
rg -n "SPHERE_ADVICE_TEXTS|buildConcreteAdviceRows|planetDescription\\(|PLANET_THEME|Дела идут со скрипом|Сократи траты|Сегодня акцент через|день на твоей стороне|подводи итоги|без взлётов" components lib app apps/api/app -S
```

Result: failed; matches in backend service, LLM prompt, and frontend summary fallback.

```bash
cd apps/api && .venv/bin/pytest tests/test_today_concrete_advice.py -q
```

Result: `2 passed`.

```bash
npx vitest run __tests__/components/TodayScreen.test.tsx
```

Result: `14 passed`.

The tests pass but do not catch the architectural violations above.

## Required Direction

Keep the contract shape and visual shell. Rework must remove hardcoded forecast templates from active source and make tests prove the actual contract behavior:

- no product forecast templates in `components`, `lib`, `app`, or `apps/api/app`;
- no pytest detection in product service;
- no raw semantic icon names visible in rows;
- no `Transit_` / `Natal_` in visible payload text;
- invalid/missing LLM output is rejected or unavailable, not replaced with advice templates.
