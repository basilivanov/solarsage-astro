# 45 — P7-F2A TODAY SCREEN COMPONENTS TZ — Today Convergence Rewrite

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Параллельный кодер работает
только в apps/api (backend) — его файлы не трогать.

## 1. Packet title

P7-F2a — новый Today screen component suite на `TodayConvergencePayload`:
все состояния из 16 fixtures, DOM/test contract из AGENTS.md и 03 §11,
атомарное удаление старых UI/fixture тестов из W9 W7-списка.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 (W7 frontend), срез F2a (компоненты без
page wiring — страница и hook подключаются в F2b).

## 3. Modules

- Новый: `M-TODAY-CONVERGENCE-SCREEN` — `components/today-convergence/`
- Tests: `__tests__/components/today-convergence/` (новые),
  удаления по W9 W7-списку (§8.4).

## 4. Goal

Каталог `components/today-convergence/` рендерит все 16 fixtures из
`__tests__/fixtures/today_convergence_v2/` с публичным DOM-контрактом
(`data-testid`/state attributes), accessibility semantics и без единой
строки legacy-полей. Старые W7-удаляемые тесты убраны в том же changeset.

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/03_W7_FRONTEND_DESIGN_TZ.md`
  ЦЕЛИКОМ (особенно §2 оси, §3 цвета, §4 типографика, §5 компоновки по
  состояниям, §9 loading/retry/disclosure, §10 тексты/время, §11 test
  contract, §12 accessibility).
- AGENTS.md раздел «UI Semantic/Test Contract» (корень репо).
- Fixtures: `__tests__/fixtures/today_convergence_v2/` (16 Today + index.ts
  barrel с типами).
- Типы: `packages/contracts/today-convergence.ts` (TodayConvergencePayload).
- Существующие примитивы для переиспользования (смотреть, не менять):
  `components/paywall.tsx` (preview/locked), `components/ui/*`,
  `components/shared/cosmic-loader.tsx` (loading).

## 6. Exact write scope

- `components/today-convergence/*.tsx` (новые)
- `__tests__/components/today-convergence/*.test.tsx` (новые)
- Удалить ровно эти файлы (W9 W7-список, атомарно с новым покрытием):
  - `__tests__/components/ActivationEvidenceCard.downstream.test.tsx`
  - `__tests__/components/ActivationEvidenceCard.personal.test.tsx`
  - `__tests__/components/FocusEventSheet.test.tsx`
  - `__tests__/components/TodayFocus.test.tsx`
  - `__tests__/components/TodayImportantAccordion.test.tsx`
  - `__tests__/components/TodayScreen.v2-downstream.test.tsx`
  - `__tests__/contracts/today-fixture-roundtrip.test.ts`
  - `__tests__/contracts/today-focus-canary-roundtrip.test.tsx`
  - `__tests__/contracts/today-v2-wire-identity.test.ts`
  - `__tests__/lib/presentation/today-v2.test.ts`
  - `__tests__/today/day-summary-card.test.tsx`
  - `e2e/mock-visual/fixtures/day-2026-07-05.ts`,
    `e2e/mock-visual/fixtures/day-v2-2026-07-08.ts`,
    `e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json` — ТОЛЬКО если
    после удаления тестов выше они становятся unreferenced (проверить
    grep'ом; если ещё используются — оставить и отметить в отчёте).
- Если удаление теста ломает НЕ перечисленный файл (импорт) — СТОП по этому
  файлу, отметить в отчёте.

## 7. Frozen / Out of scope

- НЕ менять: `app/(grace)/day/[date]/page.tsx`, hooks (`useDay` и др.),
  `lib/adapters/*`, `components/today/*` (legacy компоненты остаются до W9),
  `__tests__/components/TodayScreen.test.tsx`, `__tests__/app/day-page.test.tsx`,
  `__tests__/hooks/*`, `__tests__/api/*` (это F2b «переписать»-список),
  e2e specs, backend, packages/contracts/*.
- НЕ подключать к странице (F2b). НЕ реализовывать calendar/sphere
  страницы (F3).

## 8. Функциональные требования

### 8.1 Компоненты (components/today-convergence/)

- `today-screen.tsx` — root `<section data-testid="today-screen">` с
  атрибутами: `data-screen-state="ready"` (transport loading/error —
  отдельные состояния компонента, см. ниже), `data-state`,
  `data-day-tone` (отсутствует при null), `data-content-state`,
  `data-access-state`, `data-birth-time-mode`. Nullable атрибуты НЕ
  получают строку "null" — атрибут отсутствует.
- `convergence-hero.tsx` — `data-testid="convergence-hero"`,
  `data-day-tone`, `data-evidence-level`; сферы
  `data-testid="convergence-sphere-{key}"` с `data-polarity`; вторичные
  строки `data-testid="convergence-secondary"`. Слово «сошлось» ТОЛЬКО
  здесь.
- `main-event.tsx` — `data-testid="main-event"`, `data-polarity`.
- `impulses-list.tsx` — `data-testid="impulses-list"` `data-count`;
  импульс `data-testid="impulse-{eventId}"` с `data-polarity` и
  `data-time-mode`.
- `today-narrative.tsx` — LLM-зона `data-testid="today-narrative"` с
  `data-state="ready|pending|unavailable|not_needed"`: ready → тексты из
  claim.text; pending → скелетон только в LLM-зоне (`role="status"`,
  `aria-live="polite"`); unavailable → честная строка «Персональный разбор
  пока не готов» + retry-кнопка (callback prop); not_needed → не рендерится.
- `today-lookahead.tsx` — `data-testid="today-lookahead"`,
  `data-target-date` (только quiet + lookahead).
- `period-context.tsx` — «Контекст периода» блок (disclosure pattern по
  §9: `aria-expanded`/`aria-controls`, контент остаётся в DOM через hidden).
- `sphere-navigator.tsx` — `data-testid="sphere-navigator"`, 12 тайлов в
  фиксированном каноническом порядке (work, money, documents, relationships,
  sport, communication, health, decisions, travel, creativity, study,
  shopping), тайл `data-testid="sphere-tile-{key}"` с
  `data-has-today="true|false"` (true для сфер из payload), нейтральная
  точка-маркер без tone-цвета. Тайлы — ссылки (href пропсом; навигация —
  F3, сейчас `#`-заглушка недопустима — используй реальный path
  `/day/spheres/{key}` как статический href).
- `birth-time-banner.tsx` — `data-testid="birth-time-banner"` для
  bucket/unknown, dismissible (one-shot состояние через prop + onDismiss).
- `day-general-sky.tsx` — `data-testid="day-general-sky"` для
  personal=false (маркер «не персональный прогноз» обязателен).
- `today-unavailable.tsx` — state=unavailable: «Не удалось рассчитать
  день. Обновить» + retry (prop), `role="alert"` для статуса.
- Transport states компонента: `screenState="loading"` → скелетон по форме
  (`role="status"`); `screenState="error"` → root
  `data-screen-state="error"`, `role="alert"`, одна retry-кнопка.
- `how-calculated.tsx` — disclosure «Как это рассчитано»
  (aria-expanded/controls), текст статический RU.

### 8.2 Цвета/типографика (03 §3-§4)

- Тёплая бумага; polarity — лёгкий фон/метка + всегда текст; красный
  запрещён; steady — без акцента; `--accent` (сливовый) только hero-рамка
  и интерактив. Tone/полярность никогда не только цветом.
- Использовать существующие CSS tokens/Tailwind классы проекта; новые
  semantic tokens — через существующий механизм (globals.css/tailwind
  config) МИНИМАЛЬНО; если нужен новый token — добавить в
  `app/globals.css` по существующему паттерну (это разрешено, файл вне §6
  запрета — но только additive :root переменные).

### 8.3 Время и тексты (03 §10)

- exact: `пик 15:40, окно 13:00–18:00`; bucket: «во второй половине дня»;
  unknown: часть суток/дата. Таблица маппинга partOfDay→RU строка —
  константа в компоненте (night «ночью», morning «утром», day «днём»,
  evening «вечером»; для окна — «во второй половине дня» стиль по таблице).
- Никаких `…` обрезок, template-заглушек, LLM-полей вне claim.text.

### 8.4 Component tests (`__tests__/components/today-convergence/`)

- Рендер КАЖДОЙ из 16 fixtures: root атрибуты соответствуют fixture
  (state/tone/contentState/access/birthTimeMode), ключевые блоки
  присутствуют/отсутствуют по матрице (hero только convergence; impulses
  quiet; teaser preview; пустой locked; unavailable состояния).
- Accessibility: loading role=status; error role=alert; disclosure
  aria-expanded переключается; icon-only кнопки с aria-label.
- Время: exact/bucket/unknown форматы по §8.3 (snapshot text match на
  RU-строки).
- pending: скелетон только в narrative-зоне; deterministic блоки видимы.
- Негатив: fixture №12 (state=unavailable) не рендерит hero/impulses.
- Каждый тест обращается только к публичному DOM-контракту
  (data-testid/role/aria), не к CSS-классам.

## 9. Must-preserve invariants

- Полный `npx vitest run` зелёный (после удалений: старые тесты уходят,
  новые добавляются; остальные 1300+ не тронуты).
- `npx tsc --noEmit` чист по новым файлам (pre-existing ошибки вне §6 —
  отметить в отчёте, не чинить).
- `python3 scripts/grace_front_lint.py` PASS (новый каталог попадает под
  marker gate; GRACE-разметка TSX по канону: AI_HEADER/MODULE_CONTRACT/
  MODULE_MAP с owned_tests).
- `grace/frontend.paths` — проверить, покрывает ли `components/`; если
  новый подкаталог требует регистрации — добавить строку (это разрешено).
- ESLint по новым файлам чист.

## 10. Verification

```bash
cd /tmp/solarsage-convergence-b
npx vitest run __tests__/components/today-convergence 2>&1 | tail -3
npx vitest run 2>&1 | grep -E "Test Files|Tests "
npx tsc --noEmit 2>&1 | tail -5
python3 scripts/grace_front_lint.py 2>&1 | tail -1
npx eslint components/today-convergence __tests__/components/today-convergence 2>&1 | tail -3
rg -n 'DayStatus|TodayFocus|relativeStatus' __tests__ --glob '!**/audit/**' | head -5
# ожидание: 0 active legacy matches по удалённым suites
```

## 11. Expected evidence

- Список новых компонентов и тестов; подтверждённые удаления из §6;
  вывод команд §10; скрин текстового рендера не нужен — DOM contract
  assertions в тестах.

## 12. Escalation rule

Нужно менять page/hooks/adapters/legacy компоненты или удалить что-то вне
§6 → СТОП, доложить. Нехватка дизайн-детали → принять минимальное решение
по 03 и зафиксировать в отчёте.

## 13. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
