# Packet 37 — P3-G: restore full CI green before P4

Статус: **COMPLETED — local gates green; GitHub CI pending**
Phase / gate: **P3 acceptance / mandatory CI recovery before P4**
Baseline run: `30615509451`, head `807c4d84bab16869c6ee53757ff0ff099f73b239`
Controller: `06_DEV_RELEASE_EXECUTION_PLAN_TZ.md`

## 1. Goal

Вернуть все jobs текущего GitHub CI в зелёное состояние после P1–P3, не меняя
W1 canon, runtime-семантику convergence, публичные контракты, тестовые пороги
или workflow. После этого packet 36 и этот recovery changeset можно push вместе;
P4 запрещён до зелёного GitHub run на новом head.

Исходный RED воспроизведён:

- API proof: 7 failures из-за двух stale `ss-calc-1.2.0` в legacy V2 fixture
  при canonical `CALCULATION_VERSION=ss-calc-1.3.0`;
- mypy: 34 errors в 9 новых/изменённых API service-файлах;
- sidecar Ruff: 2 genuinely unused local assignments;
- frontend ESLint: 4 unused imports/locals в трёх legacy test-файлах;
- contract tests и sidecar tests уже green.

## 2. Exact write scope

Разрешены только:

- `apps/api/app/services/today_convergence_units.py`
- `apps/api/app/services/today_birth_time.py`
- `apps/api/app/services/today_convergence_groups.py`
- `apps/api/app/services/today_convergence_tone.py`
- `apps/api/app/services/today_convergence_selection.py`
- `apps/api/app/services/checkin_service.py`
- `apps/api/app/services/today_birth_time_facts.py`
- `apps/api/app/services/today_convergence_runtime.py`
- `apps/api/app/services/today_convergence_snapshot.py`
- `apps/solarsage/solarsage/services/activation_builder.py`
- `e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json`
- `__tests__/components/FocusEventSheet.test.tsx`
- `__tests__/components/TodayScreen.v2-downstream.test.tsx`
- `__tests__/contracts/today-focus-canary-roundtrip.test.tsx`
- `__tests__/contracts/today-fixture-roundtrip.test.ts`
- этот packet-файл.

Если green требует соседний путь — stop и escalation. Не расширять scope молча.

## 3. Mandatory fixes

### 3.1 API proof fixture

В committed legacy fixture заменить **оба** значения calculation version
`ss-calc-1.2.0` на `ss-calc-1.3.0`: public meta и nested audit/meta должны
оставаться согласованными. Не подменять version внутри pytest fixture и не
ослаблять proof validator: тест обязан читать честный committed JSON.

Синхронизировать точное version-ожидание в
`__tests__/contracts/today-fixture-roundtrip.test.ts` с тем же canonical
`ss-calc-1.3.0`. Это соседний consumer того же committed JSON, выявленный
полным Vitest reviewer-gate после исходного RED; других assertions теста не
менять.

### 3.2 Mypy debt

Закрыть все 34 исходных errors и любые новые errors packet 36 так, чтобы
`mypy app/services/` завершался с `Success: no issues found`.

Разрешены: точные return annotations, локальное type narrowing, явные guards,
typed helper/alias, корректное распаковывание tuple, доказуемый `cast` к точному
типу. Запрещены:

- `# type: ignore`, `Any`/`object` как способ спрятать ошибку;
- ослабление public return type;
- удаление runtime validation или изменение ranking/tone/grouping/check-in
  поведения;
- изменение W1 canon, формул, mapping, порогов или payload shape.

Для missing-return допустим только явный fail-closed unreachable guard после
исчерпывающего enum/Literal branching; valid-input поведение не меняется.

### 3.3 Ruff and frontend lint

- удалить только два неиспользуемых local assignment в `activation_builder.py`;
- удалить только четыре неиспользуемых import/local binding в трёх test-файлах;
- не удалять legacy tests сейчас: их нормативная замена остаётся первым
  changeset W7;
- существующий `react-hooks/exhaustive-deps` warning в legacy runtime не входит
  в этот recovery packet и не должен провоцировать runtime refactor.

## 4. Frozen / forbidden

- `.github/workflows/ci.yml`, pytest/mypy/Ruff/ESLint/Vitest config;
- coverage thresholds, markers, skips, xfail, test selection;
- W1 canon/replay fingerprint/formula/calculation version;
- generated public contracts, API/DB schema, migration, frontend runtime;
- удаление тестов или переписывание assertions ради green;
- commit/push — выполняет reviewer.

## 5. Required gates

Coder:

```bash
PYTHONPATH=apps/api:packages/py-contracts \
  /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_real_today_v2_api_proof.py -q

cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/mypy app/services/

/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check --no-cache \
  apps/api/app apps/solarsage/solarsage

pnpm run lint
git diff --check
python3 scripts/grace_lint.py apps/api/app --quiet
```

Также запустить owned/focused tests изменённых service-модулей, найденные через
их `MODULE_MAP.owned_tests`. Не менять файлы тестов вне exact scope.

Reviewer перед push:

```bash
PYTHONPATH=apps/api:packages/py-contracts pnpm contracts:check
npx vitest run --coverage
cd apps/api && PYTHONPATH=.:../../packages/py-contracts \
  /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest tests/ \
  -m 'not integration and not benchmark' -q
```

Затем локальный scoped commit, push packet 36 + packet 37, ожидание GitHub CI.
Acceptance: `backend-lint`, `backend-mypy`, `backend-tests`, `sidecar-tests`,
`frontend-tests`, `contract-tests` — все green. До этого P4 не начинать.

## 6. Evidence

Финальная локальная приёмка:

- API proof: `16 passed`;
- mypy без incremental cache: `Success: no issues found in 96 source files`;
- owned backend tests: `253 passed`;
- full backend: `2525 passed, 5 skipped, 32 deselected`;
- full Vitest coverage run: `136 files, 1354 tests passed`;
- generated contracts: `111 passed`, generated diff clean;
- Ruff, ESLint (0 errors; один frozen warning), GRACE и `git diff --check`: PASS.

Test/config/workflow и runtime semantics не ослаблены. Reviewer выполняет
scoped commit/push и подтверждает отдельным GitHub CI run все шесть jobs.
