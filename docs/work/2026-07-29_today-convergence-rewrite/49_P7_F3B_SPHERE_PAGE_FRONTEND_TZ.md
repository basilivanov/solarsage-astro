# 49 — P7-F3B SPHERE PAGE FRONTEND TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ. Выполняется
ПОСЛЕ merge backend P4-D3C (TodaySpherePagePayload уже в generated
contracts — проверь наличие в `packages/contracts/_generated.zod.ts`
`TodaySpherePagePayloadWireSchema`; если его нет — СТОП, доложить).

## 1. Packet title

P7-F3b — static sphere page frontend: `/spheres/{key}` с натальным слоем
«В твоей карте» и period слоем «Сейчас действует».

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 (W7 frontend), срез F3b.

## 3. Modules

- Новый: `M-APP-SPHERE-PAGE` — `app/(grace)/day/spheres/[key]/page.tsx`
- Новый: `M-SPHERE-PAGE` — `components/today-convergence/sphere-page.tsx`
- Изменяемый: `lib/api/today-convergence.ts` (или новый
  `lib/api/spheres.ts` — выбрать по размеру) + тайлы навигатора
  (немаркированный тайл → `/spheres/{key}`)

## 4. Goal

Тап по немаркированному тайлу навигатора открывает `/day/spheres/{key}`:
слой 1 «В твоей карте» (natal paragraphs при state=ready, честный статус
при unavailable), слой 2 «Сейчас действует» (period items с датами
окончания). Без слов «сегодня»/«завтра», без дневных вердиктов, дома при
bucket/unknown скрыты (по `housesAvailable`).

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  §7 (:186-190) и master §16 (запреты: «сегодня»/«завтра», дневные чипы,
  tone-заливка тайлов).
- Backend payload (фактическая форма — сверь с generated zod):
  `TodaySpherePagePayload { sphere, birthTimeMode, housesAvailable,
  natal { state: ready|unavailable, paragraphs: [{text, sourceFactIds}] | null },
  period: [{id, technique, title, activeFrom, activeUntil}], periodIdentity }`.
- `components/today-convergence/sphere-navigator.tsx` — текущие href.

## 6. Exact write scope

- `app/(grace)/day/spheres/[key]/page.tsx` (новый)
- `components/today-convergence/sphere-page.tsx` (новый)
- `lib/api/spheres.ts` (новый) или расширение lib/api/today-convergence.ts
- `components/today-convergence/sphere-navigator.tsx` — только href
  немаркированных тайлов (если требуется)
- `__tests__/components/today-convergence/sphere-page.test.tsx` (новый)
- `grace/frontend.paths` — если требуется

## 7. Frozen / Out of scope

- Backend, contracts, drilldown (F3), visual/e2e (F4), legacy components.

## 8. Функциональные требования

- Fetch `GET /api/spheres/{key}` (zod): loading (role=status), error
  (role=alert + retry), 403 → paywall CTA, 422 → «Страница недоступна».
- Root `data-testid="sphere-page"` `data-sphere={key}`
  `data-birth-time-mode={mode}`.
- Слой 1 «В твоей карте»: при `natal.state=ready` — paragraphs (перенос
  по абзацам, text-wrap pretty); при `unavailable` — честная строка
  «Разбор сферы готовится» (без retry-кнопки в v1? — retry через общий
  refetch страницы допустим; зафиксируй выбор).
- `housesAvailable=false` (bucket/unknown) — честная пометка: «Дома и
  точные часы скрыты: время рождения не указано».
- Слой 2 «Сейчас действует»: список period items — `title` + дата
  окончания («до {date}» RU формат, date only); без polarity-заливки.
- Запрещено: «сегодня»/«завтра», дневные вердикты, тестом это покрыть
  (render → отсутствие строк).
- Тесты: fixtures/inline payloads (ready, unavailable, period пустой,
  bucket без домов) — DOM contract + запретные слова + даты формата.

## 9. Must-preserve invariants

- `npx vitest run` зелёный; `npx tsc --noEmit` чист;
  `python3 scripts/grace_front_lint.py` PASS; production build PASS.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b
npx vitest run __tests__/components/today-convergence/sphere-page.test.tsx 2>&1 | tail -2
npx vitest run 2>&1 | grep -E "Test Files|Tests "
npx tsc --noEmit 2>&1 | tail -2
python3 scripts/grace_front_lint.py 2>&1 | tail -1
NODE_ENV=production npx next build 2>&1 | tail -3
```

## 11. Expected evidence

Файлы, вывод §10, пример render-структуры (дерево блоков).

## 12. Escalation rule

Payload форма не совпадает с §5 → СТОП, доложить (не адаптировать под
факт молча). Нужно менять backend → эскалация.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
