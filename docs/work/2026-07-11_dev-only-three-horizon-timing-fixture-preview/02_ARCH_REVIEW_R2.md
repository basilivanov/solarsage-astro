# Архитектурное ревью R2 — production build blocker

Дата: 2026-07-11
Статус: `REWORK_REQUIRED_R3`
Режим: без commit/push/merge.

## Что уже принято

- fixture URL показывает все три timing-блока;
- fixture browser context вызывает только
  `GET /api/dev-fixtures/three-horizon-timing`;
- переход на другой день удаляет fixture query и возвращает normal flow;
- endpoint: local `200`, public Host `404`, unsafe proxy `404`;
- targeted Vitest: 15 passed;
- focused Playwright: passed;
- `tsc --noEmit` и `git diff --check`: passed.

Эти части не переделывать заново.

## BLOCKER — production build падает из-за общего layout

Независимо выполнена команда:

```bash
NEXT_DIST_DIR=.next-arch-review pnpm build
```

Компиляция прошла, но prerender завершился ошибкой:

```text
useSearchParams() should be wrapped in a suspense boundary at page "/calendar"
Error occurred prerendering page "/calendar"
Export encountered an error on /(grace)/calendar/page
```

Причина: `app/(grace)/layout.tsx` теперь напрямую вызывает `useSearchParams()`.
Этот layout общий для `/calendar` и остальных Grace routes, поэтому dev fixture
не имеет права ломать production prerender.

Архитектор уже удалил временный `.next-arch-review` и вернул автоматически
изменённые build-командой `next-env.d.ts`/`tsconfig.json`. Не менять их в рамках
исправления.

## Обязательная переделка

Предпочтительный минимальный вариант:

1. `GraceLayout` сам не вызывает `useSearchParams()`.
2. Вынести `usePathname()` + `useSearchParams()` и выбор shell в отдельный
   внутренний client component, например `GraceShellRouter`.
3. Обернуть этот component в React `Suspense` внутри `GraceLayout`.
4. Suspense fallback обязан быть полностью side-effect-free:
   - не монтировать `AuthenticatedShell`;
   - не вызывать `useTelegramAuth`;
   - не монтировать `AppShell`, `useOnboarded`, `ProfileReset`;
   - не выполнять `/api/**` requests.
5. Fallback может быть нейтральным статическим loading shell/`role="status"`
   либо `null`. Если показывается loader, дать ему стабильный DOM contract и
   `aria-busy="true"`; он не должен называться auth-loading, пока выбор ветки
   ещё не сделан.
6. После разрешения Suspense:
   - exact dev fixture path/query монтирует только `FixtureShell`;
   - все остальные routes монтируют прежний `AuthenticatedShell`.
7. Сохранить exact fixture eligibility:

   ```text
   NODE_ENV === development
   pathname === /day/2026-07-08
   fixture === three-horizon-timing
   ```

8. Вернуть существующий normal-flow log, потерянный при рефакторинге:

   ```text
   [GraceLayout] Showing loading spinner
   ```

   Он должен эмититься внутри `AuthenticatedShell` при `isLoading`, как в
   baseline. Fixture/fallback этот log не эмитят.
9. Обновить GRACE module map/contracts для нового Suspense/router block и
   side-effect-free fallback.

Допустим другой минимальный вариант без `useSearchParams` в общем prerender path,
но он обязан одновременно доказать production build и нулевые auth/profile API
в fixture. Не использовать initial `AuthenticatedShell` с последующим
`useEffect`-переключением: auth успеет стартовать до fixture selection.

## Обязательные проверки R3

1. Повторить targeted tests:

```bash
npx vitest run \
  __tests__/api/dev-timing-fixture-route.test.ts \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/guardrails/no-runtime-mocks.test.ts
```

2. Type/diff:

```bash
npx tsc --noEmit
git diff --check
```

3. Browser fixture:

```bash
E2E_BASE_URL=http://127.0.0.1:3003 \
  npx playwright test e2e/dev-timing-fixture.spec.ts --project=mobile
```

4. Production build обязательно должен завершиться exit code `0`:

```bash
NEXT_DIST_DIR=.next-arch-review-r3 pnpm build
```

После build:

- удалить только созданный `.next-arch-review-r3`;
- вернуть любые автоматические изменения `next-env.d.ts`/`tsconfig.json` к их
  точному pre-build содержимому;
- убедиться, что этих файлов нет в `git diff`;
- не трогать `.next-v2-preview`, потому что на нём работает preview `3003`.

5. После production build снова проверить, что `3003` жив и fixture URL всё ещё
   показывает три timing card с единственным fixture API request.

## Callback R3

```text
READY_FOR_BROWSER_FIXTURE_TIMING_PREVIEW_R3
fixture_url: http://127.0.0.1:3003/day/2026-07-08?fixture=three-horizon-timing&why=1
fixture_api_requests: <unique /api paths>
production_build: PASS <точная команда>
targeted_tests: <result>
playwright: <result>
typecheck_diffcheck: <result>
build_artifacts_cleaned: YES
next_env_tsconfig_unchanged: YES
preview_3003_alive: YES
commit: NOT_YET
push: NOT_YET
```
