# S1.W2 Architecture Review R4 — GRACE marker and unused import cleanup

Дата: 2026-07-11

Вердикт: **REWORK REQUIRED — structural comments/imports only**.
Поведение и тесты не менять. Commit/push запрещены. S1.W3 не начинать.

## 1. Удалить unused type import

В `lib/presentation/today-v2.ts` импортируется, но больше не используется:

```ts
SphereScoreV2
```

Удалить только этот specifier из import list.

## 2. Сделать настоящие GRACE function markers

Сейчас contracts у `fetchDay`, `fetchCalendar`, `adaptTodayPayload` находятся
внутри JSDoc как строки `* START_FUNCTION_CONTRACT`. Это не canonical marker
из AGENTS.md и может не распознаваться структурным scanner.

### 2.1 `lib/grace/api/client.ts`

Оставить краткий обычный JSDoc, если нужен, но вынести contracts в line comments
непосредственно перед соответствующими functions:

```ts
// START_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.fetchDay
// purpose: ...
// inputs: ...
// returns: ...
// side_effects: ...
// emitted_logs: none.
// error_behavior: ...
// END_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT.fetchDay
export async function fetchDay(...) {
```

Аналогично преобразовать уже написанный contract для `fetchCalendar`, чтобы в
существенно изменённом файле не оставалось псевдо-markers внутри JSDoc.

### 2.2 `lib/adapters/today-payload.ts`

Вынести existing
`F-M-ADAPTERS-TODAY-PAYLOAD.adaptTodayPayload` contract из JSDoc в canonical
`// START_FUNCTION_CONTRACT` / `// END_FUNCTION_CONTRACT` line comments
непосредственно перед `export function adaptTodayPayload`.

Содержимое contracts и runtime code не менять.

## 3. Gates

```bash
rg -n '^\s*// START_FUNCTION_CONTRACT: F-M-WEB-API-CLIENT\.(fetchDay|fetchCalendar)$' \
  lib/grace/api/client.ts

rg -n '^\s*// START_FUNCTION_CONTRACT: F-M-ADAPTERS-TODAY-PAYLOAD\.adaptTodayPayload$' \
  lib/adapters/today-payload.ts

rg -n '\bSphereScoreV2\b' lib/presentation/today-v2.ts
npx tsc --noEmit
git diff HEAD --check
```

Expected:

```text
fetch markers: 2
adapter marker: 1
SphereScoreV2 scan: no output
tsc: PASS
diff_check: PASS
commit: NOT_YET
push: NOT_YET
```

## 4. Callback

```text
READY_S1_W2_WIRE_MIGRATION_R5
canonical_fetch_function_markers: 2
canonical_adapter_function_markers: 1
unused_sphere_score_v2_import: REMOVED
runtime_behavior_changed: NO
tsc: PASS
diff_check: PASS
commit: NOT_YET
push: NOT_YET
```
