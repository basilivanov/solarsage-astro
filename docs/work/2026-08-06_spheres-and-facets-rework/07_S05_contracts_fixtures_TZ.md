# S5 TZ — contracts regen + fixtures + frontend type fallout

## packet title
S5-contracts-fixtures

## Phase / Wave
W-SPHERES-FACETS-REWORK (docs/work/2026-08-06_spheres-and-facets-rework/)

## Modules
- generated contracts (`packages/contracts/_generated.ts`, `_generated.zod.ts`, `openapi.json`)
- fixtures (`__tests__/fixtures/today_convergence_v2/*`)

## goal
Generated OpenAPI/TS/Zod пересобраны после S2–S4/S7 (sphere/facet, новый union,
schema_version 2, periodSynthesis/note, без drilldown-схемы); все фикстуры Today
на новых ключах; frontend компилируется.

## exact write scope
- `packages/contracts/*` (результат `pnpm contracts:generate`)
- `__tests__/fixtures/today_convergence_v2/*.json` + `index.ts` (barrel)
- `lib/contracts/today.ts` (zod union ключей)
- точечные правки frontend-типов, без которых не проходит `npx tsc --noEmit`

## frozen / out-of-scope
- frontend-логика/компоненты поведения (S9), narrative (S6), backend-сервисы
- тестовые assert'ы не ослаблять — падения фиксить обновлением данных, не удалением проверок

## must-preserve invariants
- `pnpm contracts:generate` — единственный способ правки `_generated*`;
  ручные правки generated-файлов запрещены.
- Barrel `index.ts` после обновления включает `17_spheres_facets_finance` и
  `18_quiet_facets_new_spheres` (их `__sandbox*` ключи при валидации
  вырезать, если zod strict падает — задокументировать как).
- Фикстуры 01–16: `money→finance`, удалить `decisions`/`shopping` ключи
  (remap по мастер-ТЗ §4: decisions→предметная сфера по смыслу текста,
  shopping→finance), `primarySphere/secondarySphere` → `sphere`/`facet`
  (facet — по дому/контексту сигнала, при сомнении null).

## Требования
1. `pnpm contracts:generate` после S2–S4/S7; drift-gate чистый.
2. Миграция всех fixtures 01–16 на новые ключи и shape (скриптом, с отчётом mapping).
3. Barrel update; contract fixture test зелёный.
4. `lib/contracts/today.ts` zod union — новые 12 ключей.
5. `npx tsc --noEmit` — 0 ошибок (разрешены точечные правки типов в components).

## verification commands
```bash
cd /opt/solarsage-astro && pnpm contracts:generate && npx tsc --noEmit
npx vitest run __tests__/contracts
```

## expected evidence
- отчёт mapping по каждой фикстуре (что куда remapped);
- вывод contracts:generate, tsc, vitest contracts.

## escalation rule
Если tsc-фоллаут требует поведенческих правок компонентов — стоп, доложить (это S9).

## no-commit rule
Ничего не коммитить и не пушить — коммит делает ревьюер.
