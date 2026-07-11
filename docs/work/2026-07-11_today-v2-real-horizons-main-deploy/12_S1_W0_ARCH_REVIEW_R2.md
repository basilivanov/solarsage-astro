# S1.W0 Architect Review R2 — GRACE accuracy rework

Дата: 2026-07-11

Вердикт: `REWORK_REQUIRED_S1_W0_R3`

Не выполнять S1.W1. Не менять runtime/UI behavior. Не commit и не push.

## Принято в R2

- `git diff HEAD --check` теперь PASS;
- function contracts добавлены ко всем перечисленным public entrypoints;
- WeekStrip module marker получил canonical ID;
- module maps дополнены.

## Blocking findings

### 1. Непарные START_BLOCK

R2 добавил `START_BLOCK`, но не добавил соответствующие `END_BLOCK` для:

```text
app/(grace)/day/[date]/page.tsx                 ROUTE_SELECTION
app/(grace)/layout.tsx                          SUSPENSE_ROUTER
app/api/dev-fixtures/three-horizon-timing/route.ts  FIXTURE_RESPONSE
lib/dev-fixtures/use-three-horizon-timing-fixture.ts FIXTURE_FETCH
components/today/today-screen.tsx               SCREEN_COMPOSITION
components/today/week-strip.tsx                 WEEK_RENDER
```

Каждый block marker должен быть парным и охватывать ровно заявленный semantic
block. Существующие парные markers не трогать.

### 2. Function contracts не должны обещать несуществующее поведение

Исправить только комментарии:

```text
DayPage.error_behavior
```

Сейчас ошибочно сказано, что функция возвращает fallback при render failure.
Фактически локального catch/fallback нет: render errors передаются React/Next
error boundary.

```text
TodayScreen.error_behavior
```

Сейчас ошибочно сказано, что компонент возвращает fallback, когда children
throw. Фактически optional missing sections могут быть скрыты, а render
exceptions bubble to the parent boundary.

```text
GET.error_behavior
```

Уточнить оба пути: guard rejection возвращает 404; dynamic fixture
import/serialization failure не swallowing и превращается в route error/500.

```text
WeekStrip.error_behavior
```

Компонент не `raise`: per-day fetch failure становится `unknown`; неожиданный
outer batch failure пишет `system.error` и оставляет fallback statuses.

### 3. WeekStrip module contract неточен

Исправить:

```text
emitted_logs: system.error
failure_policy: per-day failure -> unknown; unexpected batch failure logs and
                keeps the week UI usable; no exception is intentionally raised
```

Не оставлять generic фразу про `logEvent/logStart/...` — contract должен
называть реально emitted event.

### 4. Test invariants не могут оставаться `none`

В module contracts:

```text
__tests__/api/dev-timing-fixture-route.test.ts
e2e/dev-timing-fixture.spec.ts
e2e/dev-visible-sphere-status.spec.ts
```

заменить `invariants: none` на краткие реальные invariants suite:

- route: только development + local direct request получает 200;
- timing E2E: fixture делает только guarded fixture API request, обычный route
  не активирует fixture, три timing blocks соответствуют payload;
- status E2E: четыре verdict enum имеют стабильные visible labels/data-status,
  раскрытый Work сохраняет aria/data-status contract.

## Завершение

1. Не менять TS/TSX executable statements, fixture payload, CSS или copy.
2. Stage только S1.W0 allowlist, включая этот review file.
3. Forbidden paths оставить untracked/unstaged.
4. Выполнить:

```bash
git diff HEAD --check
npx vitest run \
  __tests__/api/dev-timing-fixture-route.test.ts \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/guardrails/no-runtime-mocks.test.ts
npx tsc --noEmit
git status --short --branch
```

Так как R3 меняет только comments/Markdown, повторный Playwright/build не нужен,
если их R2 результаты действительно PASS и executable diff byte-for-byte не
изменён. Я независимо повторю acceptance gates после callback.

## Callback

```text
READY_S1_W0_BASELINE_R3
paired_blocks: <list>
corrected_contracts: <list>
test_invariants: <list>
executable_diff_changed_in_r3: NO
git_diff_head_check: PASS
vitest: <result>
tsc: <result>
forbidden_paths_staged: NO
commit: NOT_YET
push: NOT_YET
```
