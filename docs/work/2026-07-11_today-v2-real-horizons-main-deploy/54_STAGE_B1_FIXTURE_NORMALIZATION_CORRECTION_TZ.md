# Stage B1 — canonical fixture normalization correction

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`

## Finding

После accepted semantic corrections независимый architect gate:

```bash
pnpm contracts:fixture:check
```
завершился:

```text
Drift detected in e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json.
```

## Задача

Не менять смысл payload. Выполнить только canonical normalization существующего
единственного JSON fixture:

```bash
pnpm contracts:fixture:normalize
pnpm contracts:fixture:check
```

После normalizer проверить, что изменилось только механическое canonical
ordering/formatting и не изменились значения:

- fast `whyItMattersNow` начинается `С 8 по 10 июля по Москве`;
- firdar explanation `timing` остаётся `null`;
- horizons order `long, medium, fast`;
- IDs/actions/provenance не исчезли;
- screenshot и UI semantics не меняются.

Затем повторить:

```bash
apps/api/.venv/bin/python -m pytest \
  packages/py-contracts/tests \
  apps/api/tests/test_contract_registry.py \
  apps/api/tests/test_today_horizons_contract.py \
  scripts/contracts/test_check_compat.py \
  -q

npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/lib/presentation/today-v2.test.ts

pnpm contracts:fixture:check
git diff --check
git diff --cached --name-only
```

Scope: только уже изменённый
`e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json`; этот doc уже создан
архитектором. Не менять generated contracts, source, tests или screenshot.

Не делать `git add`, commit, push. Не начинать B2. Не запускать субагентов.

Callback:

```text
READY_STAGE_B1_FIXTURE_NORMALIZED
fixture_normalize: PASS
fixture_check: PASS
semantic_values: PRESERVED
backend_focused: <counts>
frontend_focused: <counts>
diff_check: PASS
index: EMPTY
commit: NOT_YET
push: NOT_YET
```
