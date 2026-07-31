# 50B — P7-F4 FOLLOW-UP: STALE IMPORTS + READINGS CLIENT TZ

Controller packet по coder-loop §10.7. Архитектор: main agent. Кодер: codex CLI
(второй), cwd `/tmp/solarsage-convergence-b`, ветка `work/today-convergence-2b`.

ВАЖНО: ты и есть coder. Skill coder-loop использовать НЕЛЬЗЯ — задачу
выполняешь сам и отчитываешься здесь ревьюеру. Это follow-up к packet 50:
его эскалации приняты, scope зафиксирован здесь явно.

## 1. Packet title

P7-F4b — отвязка 6 stale imports удалённого day-v2 fixture, readings
client на day-history, удаление legacy dev tooling по W9.

## 2. Phase / Wave

W-TODAY-CONVERGENCE-REWRITE / P7 (W7 frontend), срез F4b.

## 3. Modules

- `M-WEB-API-READINGS` — lib/api/readings.ts (переписать)
- Test cleanups по списку §6.

## 4. Goal

`tsc --noEmit` чист, rg-gate чист, readings экран читает
`GET /api/readings/day-history` (DayHistoryPayload) вместо N параллельных
legacy GET /api/day. Legacy TodayPayload wire тесты удалены по W9
staged правилу (их контракт удалён из API в P4-D2; равноценное покрытие
нового пути существует: useTodayConvergence, day-history API tests).

## 5. Норматив (прочитать перед кодированием)

- `docs/work/2026-07-29_today-convergence-rewrite/04_W2_W3_RUNTIME_CONTRACT_TZ.md`
  §6 (:318, :341-343): day-history payload, «никогда не запускать N cold
  calculations».
- `docs/work/2026-07-29_today-convergence-rewrite/W9_LEGACY_REMOVAL_MANIFEST.md`
  staged правила удаления тестов.
- Существующее:
  - `packages/contracts/day-history.ts` (DayHistoryPayload types +
    `DayHistoryPayloadWireSchema` в `packages/contracts/_generated.zod.ts`).
  - `components/readings/readings-screen.tsx` — consumer (проверь, какие
    поля ReadingsList/ReadingEntry использует экран).
  - Backend payload: items[{date, snapshotId, state, dayTone, sphereKeys,
    impulseCount}] + access.

## 6. Exact write scope

1. `lib/api/readings.ts` — переписать `getReadingsList` (и
   `listReadingsAsync`, если использует тот же путь) на
   `GET /api/readings/day-history?limit=N` с
   `DayHistoryPayloadWireSchema` zod-валидацией. Маппинг в
   ReadingsList/ReadingEntry по факту нужд экрана (проверь
   readings-screen.tsx; legacy поля paragraphs/headline более не
   существуют — экран должен показывать state/dayTone/sphereKeys;
   если экран требует недоступных данных — поправь экран минимально,
   файл `components/readings/readings-screen.tsx` разрешён).
2. `__tests__/api/readings.test.ts` — переписать под новый client.
3. `__tests__/api/grace-client.test.ts` — удалить day-specific кейсы
   (fetchDay marker/contract ~:140-400 по dayPayloadV2); calendar/profile/
   access кейсы сохранить.
4. Удалить `__tests__/api/today-instrumentation.test.ts` (legacy fetchDay
   instrumentation; новый путь покрыт F2b).
5. Удалить `__tests__/lib/adapt-payload.test.ts` (legacy adapter test;
   adapter уходит в W9, замена — прямой envelope, покрыт F1/F2b).
6. `__tests__/contracts/generated-runtime.test.ts` — удалить
   TodayPayloadWireSchema кейс (legacy wire identity; root удаляется в W8).
7. Удалить `app/api/dev-fixtures/three-horizon-timing/route.ts` (legacy
   dev tooling на удалённом fixture; если каталог опустел — удалить и
   его; проверь, что ничто не ссылается на route).
8. Удалить `e2e/dev-timing-fixture.spec.ts` (W9 delete-list).
9. `e2e/mock-visual/README.md` — заменить ссылку day-v2.spec на
   today-convergence.spec.
10. `e2e/mock-visual/screenshot.ts` — обновить устаревший комментарий
    про day-v2 suite (только текст).

## 7. Frozen / Out of scope

- НЕ удалять: `lib/adapters/today-payload.ts`, `lib/grace/hooks/useDay.ts`,
  `lib/grace/api/client.ts` (fetchDay) — owning legacy code уходит в W9
  отдельным changeset; здесь удаляются только их ТЕСТЫ по правилу
  «контракт удалён + равноценное покрытие есть».
- НЕ менять: backend, components/today-convergence/*, e2e mock suite
  (принят в packet 50), acceptance-day.spec.ts.

## 8. Verification

```bash
cd /tmp/solarsage-convergence-b
npx tsc --noEmit 2>&1 | tail -3
npx vitest run 2>&1 | grep -E "Test Files|Tests "
rg -n 'day-v2|dayPayloadV2|day-2026-07-05' e2e/ __tests__ app/ --glob '!**/acceptance-day*' | head -3
# ожидание: 0 matches
python3 scripts/grace_front_lint.py 2>&1 | tail -1
```

## 9. Expected evidence

- Список изменённых/удалённых файлов с однострочным обоснованием каждого
  удаления; вывод §8; readings-screen render contract (какие поля
  показываются).

## 10. Escalation rule

readings-screen требует данных, которых нет в DayHistoryPayload → СТОП,
доложить (решение архитектора, не растягивать wire). Сомнение по
удалению конкретного файла → оставить и отметить.

## 11. No-commit rule

Ничего не коммить и не пушить — коммит делает ревьюер.
