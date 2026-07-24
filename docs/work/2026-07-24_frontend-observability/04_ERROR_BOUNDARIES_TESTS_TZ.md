# Slice 04 — browser capture и Next boundaries acceptance tests

## Цель

Закрыть публичный DOM/listener contract уже созданных browser/React error
boundaries. Не менять logger, capture normalization, fetch, shipper, registry или
API clients.

## Разрешённые файлы

- `components/telemetry/frontend-error-capture.tsx`
- `app/error.tsx`
- `app/global-error.tsx`
- `__tests__/components/FrontendErrorCapture.test.tsx`
- новый `__tests__/app/error-boundaries.test.tsx`

Product-файлы менять только если тест выявляет реальный дефект; косметический
рефакторинг не нужен.

## Acceptance

### FrontendErrorCapture

- один mount добавляет ровно `error` и `unhandledrejection` handlers;
- unmount снимает те же function references;
- remount не оставляет duplicate active handler;
- error -> `frontend.runtime_failed`, source `window.error`, exact module/block;
- rejection -> `frontend.promise_rejected`, source `unhandledrejection`;
- route берётся только из `window.location.pathname`, query/hash не передаётся;
- компонент рендерит `null` и handler сам не делает direct fetch.

### App/global boundaries

- `role=alert`, стабильные testids и `data-state=error`;
- доступная button `Попробовать снова`;
- raw `error.message`/digest не появляется в DOM;
- mount/error change вызывает capture с `frontend.render_failed`, source
  `react-boundary`, правильными boundary/component/module/block и
  `resetAttempted:false`;
- click сначала capture с `resetAttempted:true` + `force:true`, затем вызывает
  `reset` ровно один раз;
- global boundary реально возвращает `<html lang="ru"><body>...`.

Тесты должны проверять public DOM и exact handler identity, не CSS classes.

## GRACE

Новый test file и существующий новый component test должны иметь полноценные
`AI_HEADER`, module contract/map и owned tests. В module maps product files
добавить owned test path. Для публичных component functions сохранить/добавить
`START_BLOCK` + function contract, если их ещё нет, без переписывания UI.

Проверка только:

```bash
npx vitest run __tests__/components/FrontendErrorCapture.test.tsx __tests__/app/error-boundaries.test.tsx && npx tsc --noEmit
```

Другие файлы не менять. Ничего не коммить и не пушить — коммит делает ревьюер.
