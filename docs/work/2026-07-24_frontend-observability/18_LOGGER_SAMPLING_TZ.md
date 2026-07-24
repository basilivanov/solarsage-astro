# Slice 18 — logger sampling and public contract

## Цель

Сделать sampling semantics детерминированными и документировать расширенный
top-level envelope API без изменения correlation/redaction/legacy behavior.

## Разрешённые файлы

- `lib/log/index.ts`
- `__tests__/lib/logger.test.ts`

## Требования

1. Sampling применяется только к level кроме `error`/`fatal`:
   - отсутствующий sample_rate -> emit;
   - finite rate clamp в `[0,1]`;
   - `0` -> всегда drop без зависимости от `Math.random`;
   - `1` -> всегда emit;
   - `0 < rate < 1` -> emit iff `Math.random() < rate`;
   - NaN/Infinity считать invalid и fail-open как `1` (logger не ломает flow).
2. `error` и `fatal` всегда emit даже при sample_rate=0.
3. Не менять envelope fields, redaction, level filtering, wrapper event-name
   conversion и legacy Logger behavior.
4. Убрать декоративные/legacy дубли; добавить named module map и
   function contracts минимум для `setCorrelationId`, `getCorrelationId`,
   `setLogContext`, `logEvent`, `logStart`, `logSuccess`, `logFailure`.
5. Module meta inputs/outputs/emitted logs должны отражать `error`, `http`,
   `operation_id`, `phase`, `duration_ms`, `sample_rate` и реальные события.

## Tests

- существующие tests сохранить;
- deterministic mocks `Math.random`:
  rate 0 drop, rate 1 emit, below rate emit, equal/above rate drop;
- NaN/Infinity emit;
- error и fatal bypass sampling;
- top-level error/http/operation/phase redaction test сохранить;
- restore mocks/env cleanly.

Проверка:

```bash
npx vitest run __tests__/lib/logger.test.ts __tests__/lib/capture-error.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
