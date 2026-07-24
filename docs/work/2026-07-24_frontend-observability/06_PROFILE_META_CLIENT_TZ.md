# Slice 06 — profile-meta API instrumentation

## Цель

Мигрировать только fail-soft profile meta aggregator с двух raw fetch на общий
wrapper, не меняя его fallback/partial business contract.

## Разрешённые файлы

- `lib/api/profile-meta.ts`
- `__tests__/api/profile-meta.test.ts`

## Требования

1. Оба параллельных запроса через `instrumentedFetch`:
   - `profile_meta.horary_quota`, `GET /api/horary/quota`;
   - `profile_meta.referral`, `GET /api/referral`.
   Сохранить credentials и Accept header.
2. Для quota использовать существующий `HoraryQuotaSchema.safeParse` как
   diagnostic responseContract. Для referral не придумывать фиктивную schema;
   typed-only validation оставить follow-up.
3. Полностью сохранить текущую семантику:
   - `Promise.all` остаётся параллельным;
   - reject любой promise -> общий catch/defaults;
   - non-ok одного response не мешает разобрать другой resolved response;
   - все existing defaults/rewardDays/bonusDays/alias остаются.
4. Обновить GRACE dependencies/emitted_logs/function block только по затронутому
   коду.

## Tests

В существующем test mock-ать `instrumentedFetch` как boundary, сохранить все
business assertions и добавить:

- exact operation/routeTemplate/init обоих calls;
- quota responseContract valid/invalid;
- один rejected promise даёт общий fallback как раньше;
- tests не оставляют stubbed globals/mocks после suite.

Проверка:

```bash
npx vitest run __tests__/api/profile-meta.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
