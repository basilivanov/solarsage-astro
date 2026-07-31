# 50 — P7-F4 VISUAL BASELINE + E2E WIRING TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ. Выполняется
после F2b/F3/F3b (страницы day/drilldown/sphere живы в worktree).

## 1. Packet title

P7-F4 — новый mock visual suite с утверждаемым baseline, удаление старых
Day V2 specs по W9, wiring workflows (visual-regression, e2e, WebKit
smoke) и real e2e specs нового Today.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 (W7 frontend), срез F4.

## 3. Modules

- Новый: `M-E2E-MOCK-TODAY-CONVERGENCE` — `e2e/mock-visual/today-convergence.spec.ts`
- Новый: `M-E2E-TODAY-CONVERGENCE` — real e2e specs (без route interception)
- Изменяемые: `.github/workflows/visual-regression.yml`,
  `.github/workflows/e2e.yml`, playwright.config.ts (WebKit project),
  e2e/README или docs (команда)

## 4. Goal

1. Mock visual suite покрывает 16 fixtures + calendar three-state +
   drilldown структурно, с PNG baseline для ключевых состояний на Desktop
   Chromium и iPhone 13.
2. Старые Day V2 mock specs и их baselines удалены тем же changeset.
3. `visual-regression.yml` запускает новый suite (не удалённый day-v2),
   `e2e.yml` содержит новые Today/Calendar/check-in specs, добавлен один
   WebKit smoke; локальная и CI команда используют один список specs.
4. Real e2e specs (без page.route) фиксируют публичный DOM-контракт
   нового Today/Calendar/check-in против dev runtime.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/06_DEV_RELEASE_EXECUTION_PLAN_TZ.md`
  P7 (строки 261-294) и §4 (test pyramid).
- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  §13 (fixtures, visual подход: маскировать LLM-зоны), §11 (selectors).
- `docs/work/2026-07-29_today-convergence-rewrite/W9_LEGACY_REMOVAL_MANIFEST.md`
  W7-списки (удалить/переписать).
- Существующее: `e2e/mock-visual/route-interception.ts`, `screenshot.ts`,
  `start-v2-preview.mjs`, `playwright.config.ts`, workflows, генератор
  initData `scripts/generate-telegram-test-initdata.py`, e2e/fixtures.ts,
  `__tests__/fixtures/today_convergence_v2/` (16 payloads + 3 yesterday).

## 6. Exact write scope

- `e2e/mock-visual/today-convergence.spec.ts` (новый) + его snapshots
- `e2e/today-convergence.spec.ts` (новый real e2e; может быть 2 файла:
  today + calendar-checkin)
- `e2e/mock-visual/calendar.spec.ts` (переписать на dayState + новые
  fixtures; старый fixture calendar-2026-07.ts уже на v2)
- **Активный calendar на v2 (обязательный блокер из эскалации):**
  - `lib/api/calendar.ts` — переписать на calendar/v2:
    `CalendarPayloadWireSchema` zod-валидация, `dayState` вместо
    `dayStatus`; normalize/status helpers под
    `hero|ordinary|not-computed` (сохранить публичные имена, которые
    используют page/calendar-screen, если возможно; иначе обновить
    callsites).
  - `components/calendar/calendar-screen.tsx` — рендер по dayState:
    hero → заполненная точка нейтрального ink, not-computed → пустой
    outline circle, ordinary → без маркера (03 §8.1; `data-day-state`
    на `calendar-day-{date}`). Переиспользовать
    `components/grace/CalendarMonth.tsx` если он уже является
    месячной сеткой экрана — проверить и не дублировать.
  - `app/(grace)/calendar/page.tsx` — только если требуется по
    сигнатуре screen.
  - `__tests__/api/calendar.test.ts` и
    `__tests__/components/CalendarScreen.test.tsx` — уже переписаны в
    F3 под v2; проверить, что они соответствуют новому client/screen
    (при расхождении — поправить тесты, не семантику).
- **Consumers удаляемых fixtures (разблокировка удалений):**
  - `e2e/mock-visual/promo-campaign.spec.ts` — отвязать от
    `./fixtures/day-2026-07-05`: заменить dayPayload на inline
    минимальный валидный `TodayConvergencePayload` (quiet_day по
    схеме) прямо в spec или на fixture из
    `__tests__/fixtures/today_convergence_v2/05_quiet_steady.json`;
    referralPayload оставить (перенести inline в spec, если жил в
    day-2026-07-05).
  - `e2e/mock-visual/start-v2-preview.mjs` — переписать под новый
    suite (новая fixture) ИЛИ удалить вместе с package.json script
    `preview:v2`, если новый suite поднимается через playwright
    `webServer` (предпочтительно — проверить playwright.config.ts).
- Удалить: `e2e/mock-visual/day.spec.ts`, `e2e/mock-visual/day-v2.spec.ts`,
  `e2e/mock-visual/day-v2.spec.ts-snapshots/`,
  `e2e/mock-visual/fixtures/day-2026-07-05.ts`,
  `e2e/mock-visual/fixtures/day-v2-2026-07-08.ts`,
  `e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json`
- Удалить/переписать real: `e2e/today.spec.ts`, `e2e/calendar.spec.ts`,
  `e2e/profile-city-checkin.spec.ts` (переписать под новый контракт или
  удалить с равноценной заменой в новых real specs)
- `.github/workflows/visual-regression.yml`, `.github/workflows/e2e.yml`
- `playwright.config.ts` (WebKit project для smoke, минимальный)
- `e2e/README.md` или `Makefile` — единая команда release specs
- `e2e/mock-visual/acceptance-day.spec.ts` — НЕ трогать (заменяется в W8)

## 7. Frozen / Out of scope

- Backend, components (приняты), `__tests__/*` (unit слой закрыт),
  production deploy (P8), включение pregen timer.

## 8. Функциональные требования

### 8.1 Mock visual suite (route interception — test-only слой)

- Сервер: существующий preview harness (start-v2-preview.mjs или
  playwright webServer против `next start` собранного worktree —
  проверить текущий подход day-v2.spec и повторить).
- Intercept `/api/day/**` → 16 fixtures; `/api/calendar` → calendar
  three-state fixture; `/api/day/snapshots/*/spheres/*` → drilldown
  fixture; `/api/checkin*` → 3 yesterday fixtures; `/api/spheres/*` →
  sphere page payload fixture (inline).
- Structural assertions на DOM contract (data-testid/state attrs) для
  каждой из 16 fixtures (desktop) — это основная масса тестов.
- PNG baseline ТОЛЬКО для: hero-tense, hero-mixed, quiet-steady,
  calendar three-state, navigator+drilldown, birth-time unknown,
  unavailable (state), content-unavailable. Desktop Chromium + iPhone 13
  (device из playwright devices). LLM-текстовые зоны (`today-narrative`)
  маскировать.
- Baseline создаётся одним явным run с `UPDATE_SNAPSHOTS=true`; после
  этого suite fail-closed. В отчёт — список созданных PNG.

### 8.2 Удаления (W9, атомарно)

- Файлы из §6 «Удалить»: specs, их snapshots и unreferenced fixtures.
- После удаления: `rg -n 'day-v2|dayPayloadV2|day-2026-07-05'
  e2e/ --glob '!**/acceptance-day*'` → 0 matches (acceptance-day
  исключается осознанно до W8 — отметить в отчёте).

### 8.3 Workflows wiring

- `visual-regression.yml`: шаг(и) запускают
  `e2e/mock-visual/today-convergence.spec.ts` (+ calendar) вместо любых
  day-v2 ссылок.
- `e2e.yml`: release job содержит новые real specs
  (`e2e/today-convergence*.spec.ts`) + mock suite, НЕ удалённые файлы.
- `playwright.config.ts`: добавить project `webkit-smoke` (WebKit) с
  grep `@webkit-smoke`; пометить 3 минимальных теста
  (ready/loading/error navigation path нового Today) этим тегом.
  Полная matrix не требуется.
- Единый список release specs: вынести в одно место (например,
  `e2e/release-specs.txt` или переменная в Makefile), используемое и CI,
  и локальной командой; задокументировать команду в e2e/README.md.

### 8.4 Real e2e (без route interception)

- Против `E2E_BASE_URL` (dev) с реальным Telegram HMAC initData
  (существующий fixtures.ts + generate-telegram-test-initdata.py).
- Минимум: today ready → DOM contract присутствует (state/tone/
  contentState/access/birthTimeMode), hero или quiet блок виден;
  pending→poll или content готов; calendar month рендерится с
  `data-day-state`; check-in page форма + (если есть lineage)
  forecast-recap скрыт до submit; sphere navigator тайлы 12 шт.
- Тесты обязаны пропускаться с понятным skip, если E2E_BASE_URL не задан
  (как существующие real specs).

## 9. Must-preserve invariants

- Mock suite зелёный локально после baseline run; unit vitest/tsc не
  затронуты; `rg day-v2` gate из §8.2 чист.
- Workflows YAML валидны (actionlint если есть, иначе yaml parse).
- acceptance-day.spec.ts не тронут и не сломан импортами.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b
UPDATE_SNAPSHOTS=true npx playwright test e2e/mock-visual/today-convergence.spec.ts \
  e2e/mock-visual/calendar.spec.ts 2>&1 | tail -5
npx playwright test e2e/mock-visual/today-convergence.spec.ts \
  e2e/mock-visual/calendar.spec.ts 2>&1 | tail -3
npx playwright test --project=webkit-smoke 2>&1 | tail -3
rg -n 'day-v2|dayPayloadV2|day-2026-07-05' e2e/ --glob '!**/acceptance-day*' | head -3
```

## 11. Expected evidence

- Список новых/удалённых файлов; PNG baseline список (имя → что
  фиксирует); вывод §10; workflow diffs; команда из README.

## 12. Escalation rule

Preview harness не поднимается с новым frontend; baseline визуально
нарушен (не маскируемый динамический контент) → СТОП, доложить с
скриншотами. Нужно менять components → эскалация.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
