# Slice 02 — canonical instrumented fetch contract

## Цель

Исправить только сетевую diagnostic boundary и передачу error meta. Не менять
API clients/callsites, shipper, registry, boundaries или layout.

## Разрешённые файлы

- `lib/log/instrumented-fetch.ts`
- `lib/log/capture-error.ts` — только расширение `CaptureErrorContext` и передачи
  уже sanitised top-level meta
- `__tests__/lib/instrumented-fetch.test.ts`
- `__tests__/lib/capture-error.test.ts` — только regression на новые meta

## Требования

1. Если correlation отсутствует, создать UUID/safe fallback, вызвать
   `setCorrelationId` и отправить его в `X-Correlation-Id`. Echoed response
   correlation применить до response/failure logs.
2. Для каждого fetch создать отдельный safe `operation_id` instance. Поле
   `operation` (`today.load`) остаётся semantic label в error payload; не
   использовать label как instance ID.
3. `ui.fetch_*` payload обязан соответствовать XML registry:
   - started: `{route: routeTemplate, method}`;
   - succeeded: `{route, method, status}`;
   - failed: `{route, method, status?}`.
   Не класть actual URL/query/body/headers в payload.
4. Все lifecycle/error envelopes должны иметь top-level `http`
   (`method/route_template/status?`), `duration_ms` где запрос завершён,
   `operation_id`, осмысленный `phase` (`request`, `response`, `failure` или
   `contract-validation`). Для этого безопасно расширить capture context.
5. HTTP/network/timeout/external-abort классификация остаётся различимой.
   HTTP Response возвращается; network/timeout/abort rethrow. Caller AbortSignal
   сохраняется и listener/timer всегда cleanup. Abort логировать warn, остальные
   failures error. Errors не sampling-ить.
6. Response contract:
   - проверять clone, не потреблять оригинальный response;
   - `valid:false`, thrown validator и invalid JSON обязаны писать
     `frontend.api_response_invalid`;
   - логировать только contract metadata, capped issue field names и shape hash,
     никогда values/body/error message;
   - сохранить публичную fetch-семантику и существующие caller validators:
     wrapper после diagnostic capture возвращает оригинальный response, caller
     parse/validator остаётся authoritative и выбрасывает свой domain error.
   - убрать ложный `createResponseContractValidator` из module map либо реально
     реализовать только если это нужно; не оставлять несуществующий entrypoint.
7. `/api/_log` должен bypass instrumentation целиком, чтобы исключить recursive
   logging loop.
8. Route template валидировать как structural label: без query/hash/actual
   opaque segments; actual `url` при этом не менять. Logger остаётся fail-safe.

## Targeted tests

Покрыть в `instrumented-fetch.test.ts`:

- mint correlation + response echo;
- exact registry-compatible lifecycle payload;
- unique operation ID и top-level http/duration/phase;
- отсутствие URL query/body/header secret во всех переданных log/capture args;
- HTTP 500, network, timeout, external abort;
- invalid schema, thrown validator, invalid JSON — log, original Response не
  consumed;
- `/api/_log` bypass без log calls.

В `capture-error.test.ts` один regression: safe http/duration/phase/operation ID
оказываются top-level, unsafe meta не проходит.

Проверка только:

```bash
npx vitest run __tests__/lib/capture-error.test.ts __tests__/lib/instrumented-fetch.test.ts
```

Никакие другие файлы не менять. Ничего не коммить и не пушить — коммит делает
ревьюер.
