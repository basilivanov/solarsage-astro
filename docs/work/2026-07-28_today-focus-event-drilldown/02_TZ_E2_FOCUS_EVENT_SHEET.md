# 02 TZ E2 — Focus Event Sheet (frontend)

1. **Packet title**: E2-FOCUS-EVENT-SHEET
2. **Phase / Wave**: W5-FOCUS-EVENT-DRILLDOWN, срез E2 (frontend). Зависит от E1 (endpoint `GET /api/day/{date}/focus-event/{event_id}` уже в main).
3. **Modules**: M-TODAY-FOCUS (кликабельные события), новый M-TODAY-FOCUS-EVENT-SHEET (модалка), M-CONTRACTS (barrel-экспорт типа)
4. **Goal**: события блока «Сошлось сегодня»/«События дня» кликабельны; по клику открывается bottom-sheet с дрилдауном, данные подгружаются лениво (fetch при открытии), состояния loading/error/ready покрыты. Дизайн — в стиле существующего `SphereDetailsSheet` (премиальный, max-w-md, мягкие скругления).

## 5. Exact write scope

- `components/today/focus-event-sheet.tsx` — НОВАЯ модалка
- `components/today/today-focus.tsx` — кликабельные строки событий + проброс onEventSelect
- `components/today/today-screen.tsx` — состояние выбранного события + рендер FocusEventSheet
- `packages/contracts/index.ts` — barrel-экспорт `FocusEventDrilldown` (+ вложенных типов при необходимости)
- `lib/contracts/today.ts` — ре-экспорт типа дрилдауна
- `__tests__/components/FocusEventSheet.test.tsx` — НОВЫЙ юнит-тест
- `__tests__/components/TodayFocus.test.tsx` — тест кликабельности строки события
- `e2e/mock-visual/day-v2.spec.ts` — mock-route нового endpoint'а + проверка открытия модалки
- `e2e/mock-visual/fixtures/json/` — при необходимости fixture дрилдауна (новый файл)

## 6. Frozen / Out of scope

- НЕ менять backend (apps/api) — E1 принят.
- НЕ менять `sphere-details-sheet.tsx`, `components/ui/sheet.tsx`.
- Строки факторов в техническом disclosure («Марс тригон Плутон · усиливает») НЕ делать кликабельными — только события.
- НЕ менять существующие e2e-бейзлайны кроме обусловленных новой кликабельностью (обновление только через `--update-snapshots` после визуальной проверки ревьюером).
- Никаких новых npm-зависимостей.

## 7. Must-preserve invariants

- `npx vitest run` — зелёный; `npx tsc --noEmit -p tsconfig.json` — 0 ошибок.
- `E2E_BASE_URL=https://dev.astro.vasiliy-ivanov.ru npx playwright test e2e/mock-visual/day.spec.ts e2e/mock-visual/day-v2.spec.ts` — зелёный (после ребилда фронта).
- `data-testid="today-focus-event"` сохранить на строке события.
- UI Semantic Contract (AGENTS.md): loading `role="status"`, error `role="alert"`, модалка `role="dialog"` + `aria-modal`, стабильные data-testid.

## Дизайн (обязателен к исполнению)

### Кликабельные события (`today-focus.tsx`)

- Строка события (`today-focus-event`) становится `<button type="button">` на всю ширину строки:
  - hover: лёгкое подчёркивание заголовка / смена фона строки;
  - справа chevron-right (lucide `ChevronRight`, h-4 w-4, muted) как affordance;
  - `aria-haspopup="dialog"`;
  - клик → `onEventSelect(event)`.
- Новый опциональный проп `onEventSelect?: (event: TodayFocusEvent) => void`.
  Если проп не передан — строки остаются plain div (обратная совместимость юнит-тестов).

### Модалка (`focus-event-sheet.tsx`)

- Основа: `Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription` из `@/components/ui/sheet` (как SphereDetailsSheet, `max-w-md` на десктопе).
- Props: `date: string` ("2026-07-28"), `event: TodayFocusEvent | null`, `onClose: () => void`.
- Lazy fetch: при открытии (event != null) →
  `fetch(`/api/day/${date}/focus-event/${encodeURIComponent(event.id)}`, { credentials: "include" })`.
  Кеш в useRef Map<eventId, FocusEventDrilldown> — повторное открытие без запроса.
  Смена event → сброс состояния. AbortController при закрытии/смене.
- Состояния:
  - loading: скелетон (animate-pulse строки) в `role="status"`, `data-testid="focus-event-sheet" data-state="loading"`;
  - error: `role="alert"`, текст «Не удалось загрузить разбор события» + кнопка «Повторить»;
  - ready: `data-state="ready"`.
- Секции ready (все data-testid обязательны):
  1. Header: `SheetTitle` = humanTitle (`focus-event-title`), под ним бейдж
     kind_label + локальное время (`focus-event-kind`), напр. «точный пик · 13:31»;
     бейдж в фиолетовой гамме как в фокус-карточке.
  2. «Что именно взаимодействует» (`focus-event-planets`): две карточки-строки:
     source (label + frame_label + function_text) → стрелка ↓/→ → target.
  3. «Как работает {aspect_label}» (`focus-event-mechanics`): aspect_symbol +
     aspect_label + aspect_mechanics текстом.
  4. «Что это значит сегодня» (`focus-event-meaning`): meaning (если не null).
  5. «Точные цифры» (`focus-event-numbers`): definition-list строк
     label — value (моноширинное value), по числам из numbers[].
  6. Футер: technique_label мелким muted (`focus-event-technique`).
- Закрытие по swipe/X — стандартное из Sheet.

### Композиция (`today-screen.tsx`)

- `const [selectedFocusEvent, setSelectedFocusEvent] = useState<TodayFocusEvent | null>(null)`;
- `<TodayFocusCard ... onEventSelect={setSelectedFocusEvent} />`;
- рендер `<FocusEventSheet date={selectedDate} event={selectedFocusEvent} onClose={() => setSelectedFocusEvent(null)} />`;
  источник даты — тот же `selectedDate`, что уходит в другие компоненты экрана (формат YYYY-MM-DD — проверить по коду).

### Тесты

- `FocusEventSheet.test.tsx`: mock global.fetch → (а) ready: все 6 секций,
  значения из fixture-объекта; (б) loading виден до resolve; (в) fetch 500 →
  error + кнопка «Повторить» дёргает fetch повторно; (г) повторное открытие
  того же события — без второго fetch.
- `TodayFocus.test.tsx`: клик по `today-focus-event` вызывает onEventSelect с этим событием.
- e2e `day-v2.spec.ts`: `page.route('**/api/day/*/focus-event/*', ...)` → fixture JSON;
  в готовом состоянии клик по первому `today-focus-event` →
  `expect(page.getByTestId('focus-event-sheet'))` ready + содержит «Точные цифры»;
  структурные проверки, НОВЫХ скриншотных бейзлайнов не добавлять.

## 8. Verification

```bash
npx vitest run __tests__/components/FocusEventSheet.test.tsx __tests__/components/TodayFocus.test.tsx && npx tsc --noEmit -p tsconfig.json
```

## 9. Expected evidence

Файлы, вывод verification, краткое описание states/flow в отчёте.

## 10. Escalation

Нужен backend-фикс или поле, которого нет в FocusEventDrilldown — стоп, доклад, новый packet.

## 11. No-commit

Ничего не коммитить и не пушить — коммит делает ревьюер.
