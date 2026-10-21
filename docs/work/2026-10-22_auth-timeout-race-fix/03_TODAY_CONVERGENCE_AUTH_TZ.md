# TZ 03: useTodayConvergence — общее auth-состояние, 401 → re-auth

1. **Packet title**: SLICE-03 today convergence consumes shared auth
2. **Phase / Wave**: W-AUTH-TIMEOUT-RACE-FIX (2026-10-22), срез 03/05
3. **Modules**: M-HOOK-TODAY-CONVERGENCE (`lib/grace/hooks/useTodayConvergence.ts`)
4. **Goal**: хук данных дня работает на общем auth-состоянии (после среза 02 второй
   POST уже исчерпан), а HTTP 401 от day-API приводит к повторной авторизации, а не к
   мёртвому error-экрану.

## 5. Exact write scope

- `lib/grace/hooks/useTodayConvergence.ts`
- `__tests__/hooks/useTodayConvergence.test.ts`

## 6. Frozen / out-of-scope

- `hooks/use-telegram-auth.ts`, `app/(grace)/layout.tsx` — принято в срезе 02, не трогать.
- `lib/api/today-convergence.ts` — не трогать (TodayConvergenceApiError уже несёт status).
- Любые страницы/компоненты Today — не трогать.

## 7. Must-preserve invariants

- pending polling bounded (4 с / 120 с), impression once per snapshot, abort/unmount safety — поведение и существующие тесты сохраняются.
- Контракт результата хука (`screenState`, `payload`, `retryAfterSeconds`, `retrying`, `refetch`) — без изменений.
- GRACE-маркеры: обновить contract (dependencies: shared auth state; invariants: 401 re-auth bounded).

## Техническое задание

1. `const { isLoading: authLoading, isAuthenticated, retry: retryAuth } = useTelegramAuth();`
   — теперь это общее состояние (срез 02), второго POST нет по построению.
2. INITIAL_LOAD: пока `authLoading` — ждать (как сейчас). Дополнительно: если auth
   завершился с `isAuthenticated === false` и `error != null` — НЕ дёргать day-API
   (layout всё равно показывает auth-error); остаться в `loading`. Ветка not-in-telegram
   без ошибки (dev skip) — поведение сохранить: fetch идёт, как сейчас.
3. 401-handling: в `load()` и в `refetch()` при `TodayConvergenceApiError` со `status === 401`:
   - один раз на монтирование (ref-флаг): вызвать `retryAuth()` и остаться в `loading`
     (когда общий auth перейдёт в authenticated, эффект INITIAL_LOAD перезапустится по deps);
   - повторный 401 после re-auth → обычный `screenState="error"` (не зацикливаться).
4. Тесты: существующие зелёные + новые:
   a. 401 при первичной загрузке → `retryAuth` вызван один раз, screenState остаётся loading;
   b. повторный 401 после re-auth → screenState="error";
   c. authLoading → fetch не вызывается (регресс).

## 8. Verification (одна команда)

```bash
npx vitest run __tests__/hooks/useTodayConvergence.test.ts __tests__/app/day-page.test.tsx
```

## 9. Expected evidence

diff по 2 файлам; вывод verification (PASS).

## 10. Escalation rule

Нужен третий файл или смена контракта хука → стоп, доложить, новый packet.

## 11. No-commit rule

Ничего не коммитить и не пушить — коммит делает ревьюер.
