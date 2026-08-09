# S20 TZ — восстановление CosmicLoader на экране дня

## packet title
S20-today-screen-cosmic-loader-restore

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- M-TODAY-SCREEN (`components/today-convergence/today-screen.tsx`)
- M-SHARED-COSMIC-LOADER (`components/shared/cosmic-loader.tsx`)

## Контекст

Фирменный лоадер дня (луна, орбиты, звёздное поле, фразы «Связываюсь со
звёздами…», прогресс 4→92%) отвалился при переписывании дня
(`e29abaa6 feat(today): wire /day/[date] to convergence screen`): страница
делегировала loading/error внутрь TodayScreen, где сделали серый скелетон
`TransportLoading` (`today-screen.tsx:147-155`). Сейчас CosmicLoader не
импортирует ни один файл — компонент, логика, CSS и тесты логики целы, но
осиротели.

Инвентарь (проверено 2026-08-09, всё существует и зелёное):
- `components/shared/cosmic-loader.tsx` — компонент (`data-testid="cosmic-loader"`,
  `role="status"`, дефолт `durationHint=12000`);
- `lib/loader-progress.ts` — чистая логика и все фразы + DONE_MESSAGE;
- `app/globals.css:236-260` — keyframes lumen-*;
- `__tests__/lib/loader-progress.test.ts` — юнит-тесты логики.

## goal

Загрузочное состояние экрана дня (`screenState === "loading"`) снова показывает
CosmicLoader вместо серого скелетона. Поведение прогресса и фраз — как было
спроектировано; доступность (role/aria) и публичный test contract не ломаются.

## exact write scope

- `components/today-convergence/today-screen.tsx` (только замена ветки loading)
- `components/shared/cosmic-loader.tsx` (только MODULE_MAP `owned_tests` — сейчас
  ссылается на несуществующий `__tests__/components/TodayScreen.v2-downstream.test.tsx`)
- `__tests__/components/today-convergence/today-screen.test.tsx` (позитивный тест
  loading → cosmic-loader)
- `__tests__/components/TodayScreen.test.tsx` (только если упадёт на замене)

## frozen / out-of-scope

- `lib/loader-progress.ts`, `app/globals.css` — без изменений (логика и
  анимации уже целы);
- narrative pending-зона (`components/today-convergence/today-narrative.tsx`,
  «Готовим персональный разбор») — НЕ трогаем в этом срезе; отдельный вопрос
  владельцу, возможный follow-up;
- `TransportError`, `ReadyContent`, страница `app/(grace)/day/[date]/page.tsx`,
  sandbox, e2e — без изменений;
- API/backend — без изменений.

## Требования к реализации

1. В `today-screen.tsx` удалить `TransportLoading` (строки 146-155, блок
   TRANSPORT оставить ради TransportError) и в ветке loading (сейчас строка 315)
   рендерить `<CosmicLoader />` с дефолтным `durationHint` (12000 мс).
   Импорт: `@/components/shared/cosmic-loader`.
2. Корневой контракт экрана сохранить: `data-testid="today-screen"`,
   `data-screen-state="loading"`, `aria-busy` — на своих местах; loader живёт
   внутри корня.
3. `components/shared/cosmic-loader.tsx`: в MODULE_MAP заменить `owned_tests`
   на реальные: `__tests__/lib/loader-progress.test.ts` и
   `__tests__/components/today-convergence/today-screen.test.tsx`.
4. Тест: `screenState="loading"` → присутствует `data-testid="cosmic-loader"`,
   `role="status"`, `aria-label="Загружаем разбор дня"`; ready → loader
   отсутствует (существующие негативные проверки скелетона сохранить/обновить:
   скелетона больше нет вообще — негативный assert на `today-loading-skeleton`
   остаётся валидным как отсутствие).
5. GRACE-разметка: обновить semantic_blocks/комментарии в today-screen.tsx,
   если они упоминают skeleton.

## must-preserve invariants

- ready/error ветки рендерятся бит-в-бит как раньше (loader только в loading);
- `data-screen-state` и root testid не меняются — e2e
  (`e2e/mock-visual/today-convergence.spec.ts:535`) зелёный;
- SSR/hydration: звёздное поле детерминировано — новых hydration-расхождений
  быть не должно (компонент уже так спроектирован);
- unit-тесты проекта зелёные (`npx vitest run`).

## verification commands

```bash
npx vitest run __tests__/components/today-convergence/today-screen.test.tsx __tests__/components/TodayScreen.test.tsx __tests__/lib/loader-progress.test.ts
npx vitest run
```

Плюс визуальная проверка ревьюером через sandbox (dev-server :3000,
`/sandbox/today?fixture=…` с задержкой не нужна — состояние loading проверяется
unit-тестом; при желании ревьюер поднимет sandbox и CF-туннель владельцу).

## expected evidence

- diff scope-файлов; вывод vitest (зелёный); подтверждение, что
  `TransportLoading` удалён, а `today-loading-skeleton` нигде не остался
  (grep по репозиторию).

## escalation rule

Потребовалось менять loader-progress, globals.css, страницу дня или
narrative pending-зону — СТОП, доложить ревьюеру.

## no-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
