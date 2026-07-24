# Slice 20 — core capture/fetch safety and GRACE closure

## Цель

Закрыть privacy-safe correlation propagation, корректный route payload и
недостающие GRACE contracts в двух core observability модулях.

## Разрешённые файлы

- `lib/log/capture-error.ts`
- `lib/log/instrumented-fetch.ts`
- `__tests__/lib/capture-error.test.ts`
- `__tests__/lib/instrumented-fetch.test.ts`

## Требования

### Correlation

1. В instrumented fetch принимать correlation ID только если trimmed value:
   - длина 1..128;
   - соответствует safe structural charset `[A-Za-z0-9._:-]`;
   - не содержит `bearer|token|secret`.
2. Выбор outgoing correlation:
   - safe caller `X-Correlation-Id` header (case-insensitive) -> использовать и
     синхронизировать logger context;
   - иначе safe current logger correlation;
   - иначе mint safe ID и установить context.
3. Unsafe caller correlation header удалить/заменить выбранным safe ID. В
   outgoing headers оставить один canonical `X-Correlation-Id`.
4. Response `X-Correlation-Id` применять до response logs только если safe;
   unsafe response header игнорировать. Не логировать raw rejected value.

### Route/error capture

5. `sanitizeRoute` сохраняет safe `{placeholder}` segment, как template
   sanitizer; реальные dynamic UUID/date/numeric/unsafe segments по-прежнему
   параметризуются.
6. `instrumentedFetch` передаёт в `captureFrontendError.context.route` только
   path template без HTTP-method prefix; `http.route_template` сохраняет method.
7. Sampling, contract clone, timeout/abort/HTTP behavior не менять.

### GRACE/tests

8. В module maps перечислить все public entrypoints и owned tests. Добавить
   START_FUNCTION_CONTRACT для public:
   - resetFingerprintDeduplicationForTests;
   - sanitizeRoute;
   - sanitizeRouteTemplate;
   - normalizeFrontendError;
   - captureFrontendError;
   - isApiLogPath;
   - instrumentedFetch.
   Каждый содержит emitted_logs/error_behavior.
9. Оба test-файла получают named module contract/map и clean mock reset.
10. Tests дополнительно доказывают:
    - safe caller correlation adopted;
    - unsafe global/caller header заменён и нигде в log calls не виден;
    - unsafe response correlation ignored, safe response adopted;
    - capture context route `/api/day/{date}`, а HTTP template
      `GET /api/day/{date}`;
    - sanitizeRoute сохраняет placeholder.

Проверка:

```bash
npx vitest run __tests__/lib/capture-error.test.ts __tests__/lib/instrumented-fetch.test.ts __tests__/lib/logger.test.ts && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
