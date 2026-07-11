# S1.W3 Guidance — DayPage full-suite baseline fix

Дата: 2026-07-11

Статус: точечная подсказка текущей S1.W3. Commit/push запрещены.

## Фактическая причина

После добавления `useSearchParams` mock первый DayPage test монтирует normal
flow и запускает calendar effect. `mockGetMonthCalendar` после
`vi.clearAllMocks()` возвращает `undefined`, поэтому production code вызывает
`.then` у `undefined`.

## Точное test-only решение

В `__tests__/app/day-page.test.tsx` внутри existing `beforeEach`:

```ts
beforeEach(() => {
  vi.clearAllMocks()
  mockGetMonthCalendar.mockResolvedValue({ days: [] })
})
```

Для страницы в этом fallback case нужен только `calendar.days`; не фабриковать
лишний полный CalendarPayload.

Второй test уже вызывает свой `mockResolvedValue({...full fixture...})` и тем
самым переопределит fallback.

Дополнительно сделать timer cleanup надёжным:

```ts
afterEach(() => {
  vi.useRealTimers()
})
```

и импортировать `afterEach` из Vitest. Удалить локальный `vi.useRealTimers()` в
конце второго test либо оставить только один общий cleanup; предпочтителен
общий `afterEach`.

Production `app/(grace)/day/[date]/page.tsx` не менять.

После исправления запустить:

```bash
npx vitest run \
  __tests__/app/day-page.test.tsx \
  __tests__/guardrails/preview-isolation.test.ts
```

Затем продолжить все gates из `27_S1_W3_IMPLEMENTATION_TZ.md`.
