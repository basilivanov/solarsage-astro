# 48 — P7-F3 DRILLDOWN + CHECKIN + CALENDAR TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельный кодер пишет
backend sphere page — его файлы не трогать (см. §7).

## 1. Packet title

P7-F3 — sphere drilldown page, Yesterday/check-in на snapshot recap и
calendar test rewrite на `dayState` контракт.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 (W7 frontend), срез F3.

## 3. Modules

- Новый: `M-APP-SPHERE-DRILLDOWN-PAGE` —
  `app/(grace)/day/snapshots/[id]/spheres/[key]/page.tsx`
- Новый: `M-SPHERE-DRILLDOWN` — `components/today-convergence/sphere-drilldown.tsx`
- Новый: `M-API-CLIENT-TODAY-SPHERE-DRILLDOWN` — добавить в
  `lib/api/today-convergence.ts` (уже создан в F2b — расширить)
- Изменяемый: check-in page + компоненты (recap + observed spheres)
- Tests: переписать W9-список (§6).

## 4. Goal

1. Тап по маркированному тайлу навигатора ведёт на drilldown page с
   deterministic evidence chain из `GET /api/day/snapshots/{id}/spheres/{key}`.
2. Check-in экран использует новый `YesterdayCheckinResponse`:
   pre-submit — только `forecastAvailable` отметка; post-submit —
   `forecastRecap` (state/dayTone/sphereKeys); опциональный мультиселект
   `observed_spheres`.
3. Calendar-тесты переписаны на `dayState` (hero/ordinary/not-computed).

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  §7 (drilldown :186-190), §8 (calendar + yesterday :192-231), §11
  (selectors), §12 (a11y).
- `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
  §6 (:315-357): drilldown endpoint, YesterdayCheckinResponse форма.
- Существующее:
  - `components/today-convergence/sphere-navigator.tsx` (F2a) — href тайлов.
  - `packages/contracts/today-sphere-drilldown.ts` (generated types из
    backend D3B) и `packages/contracts/_generated.zod.ts` —
    `TodaySphereDrilldownPayloadWireSchema`, `YesterdayCheckinResponseWireSchema`.
  - `app/(grace)/checkin/page.tsx`, `components/checkin/*` — текущая
    check-in реализация (observed spheres UI может частично существовать).
  - `components/grace/CalendarMonth.tsx` — уже на dayState (hero dot /
    not-computed outline).
  - Checkin create API: `POST /api/checkin` — принимает observed_spheres
    (проверить существующий CheckinCreate wire).

## 6. Exact write scope

- `app/(grace)/day/snapshots/[id]/spheres/[key]/page.tsx` (новый)
- `components/today-convergence/sphere-drilldown.tsx` (новый)
- `lib/api/today-convergence.ts` — добавить `fetchSphereDrilldown` и
  `fetchYesterdayCheckin` (если yesterday client отдельный — в
  существующий checkin client файл, выбрать по месту и отметить)
- `app/(grace)/checkin/page.tsx` + `components/checkin/*` — только
  необходимые изменения для новой формы (минимально инвазивно)
- `__tests__/components/CalendarScreen.test.tsx` (переписать)
- `__tests__/api/calendar.test.ts` (переписать)
- `__tests__/contracts/calendar.test.ts` (переписать: validators dayState)
- `__tests__/app/checkin-page.test.tsx` (переписать)
- `__tests__/api/checkin.test.ts` (переписать)
- `__tests__/components/today-convergence/sphere-drilldown.test.tsx` (новый)
- `grace/frontend.paths` — если новые пути требуют регистрации

## 7. Frozen / Out of scope

- НЕ менять: backend (`apps/`), `packages/contracts/*` (generated уже в
  HEAD), `components/today-convergence/*` кроме НОВОГО sphere-drilldown.tsx,
  `components/today-convergence/sphere-navigator.tsx` (только если href
  тайла не совпадает с новым route — тогда поправить href там и отметить),
  e2e specs (F4), static sphere page (ТЗ 49 после backend D3C).
- НЕ трогать legacy `components/today/*`.

## 8. Функциональные требования

### 8.1 Drilldown (03 §7)

- Route: `/day/snapshots/{id}/spheres/{key}` (совместить с href тайлов
  навигатора из F2a — проверить фактический href; если в F2a стоял
  `/day/spheres/{key}` — выбрать ОДИН канонический вид: для drilldown с
  snapshot контекстом нужен snapshotId → используй
  `/day/snapshots/{id}/spheres/{key}` и поправь href навигатора в
  F2a-компоненте, отметив это в отчёте).
- Fetch `GET /api/day/snapshots/{id}/spheres/{key}` через zod
  (`TodaySphereDrilldownPayloadWireSchema`): loading (role=status),
  error (role=alert + retry), 403/404 → честные состояния (403 —
  «Нужен полный доступ» + paywall CTA; 404 — «Разбор недоступен»).
- Контент: заголовок «{Сфера RU} — сегодня»; нумерованная доказательная
  цепочка событий (время по EventTime правилам F2a, polarity метка +
  текст, НЕ только цвет); блок convergence если присутствует (основание
  связи); disclosure «Как это рассчитано» (aria-expanded/controls).
- DOM: root `data-testid="sphere-drilldown"` `data-sphere={key}`;
  события `data-testid="drilldown-event-{eventId}"` с `data-polarity`.
- Слова «сошлось» допустимо (это hero-контекст), LLM-полей нет.

### 8.2 Check-in (03 §8.2)

- Источник — `GET /api/checkin/yesterday` (новая форма).
- Pre-submit: форма как раньше + нейтральная отметка
  `data-testid="yesterday-forecast-available"` «Прогноз за этот день
  сохранён» ТОЛЬКО при `forecastAvailable=true`; dayTone/sphereKeys НЕ
  показывать до submit.
- Post-submit: `data-testid="yesterday-forecast-recap"` блок «Что было в
  прогнозе»: sphereKeys (RU названия сфер) + тон (RU метка tone) — только
  при `forecastRecap != null`; без tone-заливки, без оценки «угадали».
- Мультиселект `observed_spheres` `data-testid="observed-spheres"`:
  12 сфер canonical порядка, опционально, значения уходят в POST
  /api/checkin (проверить wire поле `observedSpheres` в CheckinCreate).
- Streak/существующая форма не меняются.

### 8.3 Calendar tests

- `CalendarScreen.test.tsx`: рендер hero dot / not-computed outline /
  ordinary без маркера; `data-day-state` на `calendar-day-{date}`; lock
  marker сохранён.
- `api/calendar.test.ts`: client парсит calendar/v2 payload (zod);
  ошибка сети typed.
- `contracts/calendar.test.ts`: validators на dayState (заменить
  validateDayStatus suite на dayState-эквивалент; если validateDayStatus
  экспортируется из contracts runtime и стал unreferenced — отметить,
  НЕ удалять сам validator (W9)).

### 8.4 GRACE / lint

- Новые файлы с полной разметкой; `grace_front_lint` PASS; ESLint чист;
  tsc чист.

## 9. Must-preserve invariants

- `npx vitest run` зелёный; `npx tsc --noEmit` чист;
  `python3 scripts/grace_front_lint.py` PASS.
- rg-gate по изменённым тестам: `rg -n 'DayStatus|TodayFocus|
  relativeStatus' __tests__/components/CalendarScreen.test.tsx
  __tests__/api __tests__/app/checkin-page.test.tsx` → 0 matches.
- Legacy rg в `__tests__/contracts/calendar.test.ts` — 0 dayStatus
  active matches после переписывания.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b
npx vitest run __tests__/components/today-convergence/sphere-drilldown.test.tsx \
  __tests__/components/CalendarScreen.test.tsx __tests__/app/checkin-page.test.tsx \
  __tests__/api __tests__/contracts/calendar.test.ts 2>&1 | tail -3
npx vitest run 2>&1 | grep -E "Test Files|Tests "
npx tsc --noEmit 2>&1 | tail -3
python3 scripts/grace_front_lint.py 2>&1 | tail -1
NODE_ENV=production npx next build 2>&1 | tail -4
```

## 11. Expected evidence

- Список файлов; вывод §10; rg-gate вывод; скрин DOM (не обязателен).

## 12. Escalation rule

Нужно менять backend/contracts/F2a компоненты сверх §6/§8.1; wire
CheckinCreate не принимает observedSpheres → СТОП, доложить.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
