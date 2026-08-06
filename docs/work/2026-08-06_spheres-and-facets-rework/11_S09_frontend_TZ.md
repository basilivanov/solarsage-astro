# S9 TZ — frontend productization: unified как единственная ветка, выпил legacy

## packet title
S9-frontend-productization

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- today-convergence components (`components/today-convergence/*`)
- sphere pages (`app/(grace)/day/spheres/`)
- labels/icons (`lib/display/*`)

## goal
Unified-подача становится единственной веткой convergence_today; hero и
страницы сфер удалены; labels/иконки/типы финализированы под 12 новых ключей;
компонентные тесты обновлены и зелёные. UX-решения: `01_UX_DECISIONS_FROM_PROTOTYPE.md`.

## exact write scope
- `components/today-convergence/*` (включая УДАЛЕНИЕ convergence-hero.tsx,
  heroVariant-шва; ConvergenceUnifiedList — основной)
- `app/(grace)/day/spheres/` — удаление маршрута и компонентов sphere-page
- `lib/display/sphere-labels.ts`, `facet-labels.ts`, `lib/contracts/today.ts`
- `components/today-convergence/sphere-icons.tsx`, `today-formatters.tsx`
- `__tests__/components/today-convergence/*`, `__tests__/lib/display/*`
- `app/sandbox/` — today page/client (шов heroVariant убрать, unified по умолчанию)

## frozen / out-of-scope
- backend, contracts regen (S5), e2e specs (S10), calendar
- DOM-контракт data-testid/data-state (AGENTS.md UI contract) — сохранить/обновить
  осмысленно, не удалять

## must-preserve invariants
- quiet_day путь не меняется визуально (MainEvent + ImpulsesList + Narrative).
- Sandbox today продолжает работать с фикстурами 17/18 без hero-параметра.
- Все интерактивы: тайлы→шторка (включая пустые), сигнал→шторка,
  «Как это рассчитано» (stats + колесо client-only).

## Требования
1. Удалить `ConvergenceHero` и `heroVariant` prop из TodayScreen/sandbox;
   convergence_today → всегда `ConvergenceUnifiedList`. TodayNarrative
   blocks-режим: оставить для pending/unavailable; плоский flat-list для
   ready в hero больше не нужен — per-signal тексты в карточках.
2. Удалить `app/(grace)/day/spheres/[key]` route, `sphere-page.tsx` и всё, что
   только туда вело (grep: `/day/spheres/` ссылки не должны остаться).
3. `lib/display/sphere-labels.ts`: финализировать (убрать legacy
   BACKEND_TO_PRODUCT_KEY_MAP для удалённых старых API, если они больше не
   используются другими экранами — проверить grep'ом; если используются
   day-history/старым day payload — оставить только то, что реально нужно,
   с комментарием).
4. Иконки home_family (домик) и friends_goals (мишень) из прототипа — финализировать.
5. Обновить компонентные тесты: 12 тайлов новых ключей; unified-лист
   (2 finance-сигнала на одной карточке); модалки incl. empty-state;
   drilldown facet-строка/note/synthesis; how-calculated stats; старые
   assert'ы decisions/shopping — переписать под новую модель, не удалять
   проверки поведения.
6. `npx vitest run` — зелёный (0 падений); `npx tsc --noEmit` — 0 ошибок.

## verification commands
```bash
cd /opt/solarsage-astro && npx tsc --noEmit && npx vitest run
python3 scripts/grace_front_lint.py && bash scripts/grace/check-markers.sh
```

## expected evidence
- diff (включая удалённые файлы); vitest summary; grep, что `/day/spheres/`
  и `ConvergenceHero` не осталось в продовом коде (sandbox — ок).

## escalation rule
Если удаление sphere-page ломает другие экраны (profile/readings ссылки) —
стоп, доложить, новый packet.

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
