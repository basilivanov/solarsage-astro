# Slice 07 — readings history API instrumentation

## Цель

Убрать последний raw fetch из readings history, сохранив per-day fail-soft
агрегацию и каталог без изменений.

## Разрешённые файлы

- `lib/api/readings.ts`
- `__tests__/api/readings.test.ts`

## Требования

1. `fetchDayForReadings` использует `instrumentedFetch`:
   - operation `readings.day_history`;
   - routeTemplate `GET /api/day/{date}`;
   - actual URL содержит date, но date не попадает в routeTemplate/log payload;
   - сохранить credentials и Accept.
2. Добавить diagnostic responseContract через существующий
   `TodayPayloadWireSchema.safeParse`, contract `TodayPayload`, version `v1`.
   Оригинальный caller flow сохранить: non-ok/network -> null; успешный body
   возвращается как раньше. Не менять продуктовую фильтрацию locked/preview/
   hasMore/catalog.
3. Параллельный `Promise.all` и индивидуальный catch каждого day остаются.
4. Обновить GRACE dependencies/emitted_logs/function block только затронутой
   функции.

## Tests

В существующем test mock-ать `instrumentedFetch`, сохранить business assertions
и добавить:

- stable operation/route/init, actual URL date отдельно;
- на `limit=3` три instrumented calls с одним routeTemplate;
- responseContract принимает канонический `dayPayloadV2` fixture и отклоняет
  `{}`;
- mixed success/network/non-ok по-прежнему omits failed entries;
- mocks/globals cleanup после suite.

Проверка:

```bash
npx vitest run __tests__/api/readings.test.ts __tests__/contracts/generated-runtime.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
