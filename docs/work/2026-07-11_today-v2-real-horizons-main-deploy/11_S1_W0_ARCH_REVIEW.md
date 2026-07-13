# S1.W0 Architect Review R1 — REWORK_REQUIRED

Дата: 2026-07-11

Вердикт: `REWORK_REQUIRED_S1_W0_R2`

Не выполнять S1.W1. Не commit и не push.

## 1. Подтверждённые положительные результаты

- staged paths находятся внутри S1.W0 allowlist;
- forbidden paths не staged;
- заявлены PASS: 16 Vitest, TypeScript, два mobile Playwright и production
  proof build;
- dev fixture остаётся ограничен development mode, exact path/date/query и
  local guarded API route;
- обычный day branch не получает fixture payload;
- UI status labels соответствуют принятому контракту.

## 2. Blocking finding: false-positive diff gate

Изменения были staged. Команда `git diff --check` проверила только unstaged
diff и поэтому дала ложный PASS.

Независимая команда:

```bash
git diff --cached --check
```

нашла trailing whitespace в staged Markdown files, включая:

```text
docs/work/2026-07-11_dev-only-three-horizon-timing-fixture-preview/01_ARCH_REVIEW.md
docs/work/2026-07-11_dev-only-three-horizon-timing-fixture-preview/02_ARCH_REVIEW_R2.md
docs/work/2026-07-11_dev-only-three-horizon-timing-fixture-preview/03_ARCH_ACCEPTANCE.md
docs/work/2026-07-11_preview-visible-sphere-status-labels/00_TZ.md
docs/work/2026-07-11_preview-visible-sphere-status-labels/01_ARCH_ACCEPTANCE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/00_MASTER_TZ.md
```

Это не исчерпывающий ручной список: исправить весь вывод
`git diff HEAD --check`, не только перечисленные строки.

Master/stage ТЗ уже уточнены: pre-commit gate теперь
`git diff HEAD --check`, чтобы видеть staged и unstaged changes вместе.

## 3. Blocking finding: неполный GRACE contract

S1.W0 требовал полноценную GRACE-разметку для новых code files и существенных
изменений. Сейчас module maps в test files неполные, а несколько изменённых
public functions не имеют function contract.

### 3.1 Дополнить module maps

В следующих новых test files `START_MODULE_MAP` не должен состоять только из
`public_entrypoints`:

```text
__tests__/api/dev-timing-fixture-route.test.ts
e2e/dev-timing-fixture.spec.ts
e2e/dev-visible-sphere-status.spec.ts
```

Добавить реальные:

- `semantic_blocks`;
- `owned_tests`;
- для E2E в semantic block/contract явно связать screenshot artifact path;
- invariants, которые реально проверяет suite, а не `none`;
- failure policy в терминах test failure.

Не придумывать runtime logs: `emitted_logs: none` корректно.

### 3.2 Добавить function contracts

Добавить `START_FUNCTION_CONTRACT` / `END_FUNCTION_CONTRACT` для изменённых
нетривиальных public entrypoints:

```text
app/(grace)/day/[date]/page.tsx
  DayPage

app/(grace)/layout.tsx
  GraceLayout

app/api/dev-fixtures/three-horizon-timing/route.ts
  GET

lib/dev-fixtures/use-three-horizon-timing-fixture.ts
  useThreeHorizonTimingFixture

components/today/concrete-day-advice.tsx
  normalizeConcreteAdviceVerdict

components/today/today-screen.tsx
  TodayScreen

components/today/week-strip.tsx
  WeekStrip
```

Существующие function contracts для `ConcreteDayAdvice` и
`WhyTimeHorizonCard` сохранить.

Для каждого contract указать:

- purpose;
- inputs;
- returns;
- side effects;
- emitted logs;
- error behavior.

Не утверждать, что функция логирует, если она только делегирует logging.

### 3.3 Нормализовать WeekStrip module contract

Сейчас header смешивает старый anonymous contract и новый named map.
Привести markers к одному ID:

```text
START_MODULE_CONTRACT: M-TODAY-WEEK-STRIP
END_MODULE_CONTRACT: M-TODAY-WEEK-STRIP
START_MODULE_MAP: M-TODAY-WEEK-STRIP
END_MODULE_MAP: M-TODAY-WEEK-STRIP
```

Не переписывать остальной файл ради форматирования.

## 4. Обязательная работа R2

1. Исправить только findings выше; не менять принятую copy/layout/fixture data.
2. Убедиться, что последние изменения architect ТЗ staged вместе с программой.
3. Не stage forbidden/unrelated paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

4. Проверить полный diff относительно HEAD:

```bash
git diff HEAD --check
git diff HEAD --stat
git status --short --branch
```

5. Повторить S1.W0 gates:

```bash
npx vitest run \
  __tests__/api/dev-timing-fixture-route.test.ts \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/guardrails/no-runtime-mocks.test.ts
npx tsc --noEmit
E2E_BASE_URL=http://127.0.0.1:3003 \
  npx playwright test \
    e2e/dev-timing-fixture.spec.ts \
    e2e/dev-visible-sphere-status.spec.ts \
    --project=mobile
NEXT_DIST_DIR=.next-s1w0-proof pnpm build
git diff HEAD --check
```

После build восстановить только generated Next type noise безопасным способом
и удалить только `.next-s1w0-proof`. Итоговый worktree не должен содержать
build noise.

## 5. Callback R2

```text
READY_S1_W0_BASELINE_R2
head: <sha>
grace_public_contracts: <list>
module_maps_completed: <list>
git_diff_head_check: PASS
allowlist_diff: <files>
forbidden_paths_staged: NO
tests: <results>
build: <result>
preview_3003: <result>
commit: NOT_YET
push: NOT_YET
```
