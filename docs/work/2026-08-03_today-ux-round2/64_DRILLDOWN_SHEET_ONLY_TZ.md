# 64 — Drilldown: только sheet, страницу snapshot-drilldown удалить (реализация ТЗ 60)

Ты — coder. Skill coder-loop использовать НЕЛЬЗЯ. Ничего не коммить — коммит делает ревьюер.

Норматив: `docs/work/2026-07-29_today-convergence-rewrite/00.../03_W7_FRONTEND_DESIGN_TZ.md` и решение владельца `docs/work/2026-08-03_today-ux-round2/00_MASTER_TZ.md` §60: «Страницу как deep-link вообще выпиливаем, она не нужна». Drilldown = только `ImpulseDrilldownSheet` (role=dialog bottom-sheet).

## Текущее состояние (фактура ревьюера)

- Карточка импульса — `<a href="/day/snapshots/{snapshotId}/spheres/{sphere}">` (components/today-convergence/impulses-list.tsx).
- Кнопка «Разобрать, как это может проявиться» под группой открывает `ImpulseDrilldownSheet` (state `openSphere` внутри ImpulsesList).
- Маркированный тайл сферы — `<a href="/day/snapshots/...">` (sphere-navigator.tsx), немаркированный → `/day/spheres/{key}` (остаётся).
- Страница drilldown: `app/(grace)/day/snapshots/[id]/spheres/[key]/page.tsx` + `components/today-convergence/sphere-drilldown.tsx`.

## Что сделать

1. **ImpulsesList**: карточка импульса перестаёт быть ссылкой — тап открывает sheet (тот же `ImpulseDrilldownSheet`, та же группа сферы). Карточка становится `<button type="button">` (или div role=button — лучше button) с тем же визуалом и affordance (chevron оставить). Кнопку «Разобрать, как это может проявиться» под группой УДАЛИТЬ (дублирует тап). Сохранить data-testid карточек; добавить `aria-haspopup="dialog"` на карточку-открывашку.
2. **SphereNavigator**: маркированный тайл (`data-has-today="true"`) тоже открывает sheet вместо перехода. Для этого поднять состояние sheet'а: общий host в `today-screen.tsx` (state `openSphere`), колбэк `onOpenDrilldown(sphere)` в Navigator и ImpulsesList. Немаркированные тайлы — по-прежнему ссылки на статическую страницу сферы.
3. **Удалить** `app/(grace)/day/snapshots/[id]/spheres/[key]/page.tsx` (весь каталог route) и `components/today-convergence/sphere-drilldown.tsx`. Если `fetchSphereDrilldown` в `lib/api/today-convergence.ts` после этого не используется — удалить и его (backend endpoint не трогать).
4. **Sheet**: остаётся как есть; внутри ссылка «Полный разбор сферы» должна вести на `/day/spheres/{key}` (проверить, что она не ведёт на удаляемый роут).
5. **Тесты/e2e**: обновить unit (`__tests__/components/today-convergence/*`) и e2e, ссылающиеся на удалённый роут/компонент (`sphere-drilldown`, `drilldown-*` testid'ы): e2e/mock-visual/today-convergence.spec.ts — тест drilldown теперь открывает sheet и проверяет его DOM; snapshot-бейзлайны sphere-drilldown-*.png удалить из репо (git rm), новые бейзлайны sheet ревьюер переснимет отдельно. Реальные e2e (e2e/*.spec.ts) — поправить ожидания под sheet.
6. DOM-контракт sheet'а сохранить; data-testid карточек импульсов и тайлов не менять.

## Verification (обязательно, показать вывод)

- `npx vitest run 2>&1 | tail -4`
- `npx tsc --noEmit`
- `python3 scripts/grace_front_lint.py | tail -2`
- `bash scripts/grace/check-markers.sh | tail -1`
- `git diff --check`

Визуальную проверку в песочнице сделает ревьюер (`/sandbox/today?fixture=02_hero_tense`).
