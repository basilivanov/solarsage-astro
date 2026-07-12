# Stage B4.W1 architectural review R1 — order-independent proof and GRACE truthfulness

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Базовый SHA: `1a944717efa7a70124f81cb950992998491bf72e`  
Предыдущее ТЗ: `86_STAGE_B4_W1_GENERATED_WIRE_STEADY_STATE_CONSUMER_TZ.md`  
Статус: **ARCH REVIEW CORRECTIONS — NO COMMIT / NO PUSH**

## 1. Итог ревью

Production-матрица в текущем diff концептуально верна:

- generated meta pick используется без ручной raw schema;
- adapter сохраняет exact payload/frontend/content identity;
- current pair использует backend horizons либо honest unavailable;
- previous accepted pair сохраняет selector fallback;
- missing/mismatched pair fail-closed;
- selector вычисляется лениво только для `legacy-v2`.

Не переписывать эту архитектуру. Нужны только перечисленные ниже исправления
качества доказательства, GRACE-контрактов и нового тестового кода.

## 2. Preflight

Ожидается незакоммиченный B4.W1 diff ровно в шести implementation/test files из
ТЗ `86`, пустой index, HEAD/origin на базовом SHA. Дополнительно untracked
архитекторские документы `86` и `87` допустимы.

Проверить:

~~~bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
git diff --cached --name-only
git diff --name-only
~~~

Если появился иной tracked path — остановиться.

## 3. Исправление R1.1 — убрать unsafe cast из compatibility test

Файл:

~~~text
__tests__/lib/adapt-payload.test.ts
~~~

Текущий новый код:

~~~ts
delete (without as any).wireIdentity
~~~

запрещён исходным ТЗ и прямо противоречит module invariant этого test file:
`No unsafe casts`.

Заменить на type-safe object rest/destructuring. Требуемая логика:

~~~ts
const { wireIdentity, ...withoutWireIdentity } = payload
expect(wireIdentity).toBeDefined()
expect(withoutWireIdentity).not.toHaveProperty("wireIdentity")
expect(() => validateAdaptedTodayPayload(withoutWireIdentity)).not.toThrow()
~~~

Имя intentionally-unused destructured binding подобрать так, чтобы lint не
ругался, либо использовать его в assertion как показано. Не применять `any`,
`unknown as`, `@ts-ignore`, mutation/delete или non-null assertion.

Также в новых wireIdentity assertions не использовать `payload.wireIdentity!`.
Сначала сузить значение обычным `if (!wireIdentity) throw new Error(...)`, затем
проверять поля.

## 4. Исправление R1.2 — selector spies должны быть order-independent

Файл:

~~~text
__tests__/components/TodayScreen.v2-downstream.test.tsx
~~~

### 4.1 Проблема

В mismatch test spy создаётся **после** `render`. Такой тест не доказывает, что
selector не был вызван во время render. Сейчас он может случайно видеть старый
spy из предыдущего test, потому что `vi.clearAllMocks()` очищает calls, но не
восстанавливает spied implementation. Это order-dependent false confidence.

### 4.2 Обязательная изоляция

В test lifecycle восстанавливать spies между тестами (`vi.restoreAllMocks()`),
сохранив существующую очистку обычных mocks при необходимости. После этого
каждый test, который утверждает selector call count, обязан создать свой spy
**до render**.

Не полагаться на порядок `it(...)` и не оставлять spy жить между тестами.

### 4.3 Усилить exact matrix proof

Закрыть следующую матрицу отдельными order-independent assertions:

1. current `today.v2.1/3`, horizons present:
   - backend ready;
   - selector `0` (существующий test можно сохранить/усилить).
2. current `today.v2.1/3`, horizons null:
   - `why-expanded` видим;
   - unavailable empty/backend source;
   - нет `why-horizons`;
   - нет `why-time-horizon`;
   - нет `astrology-calculation` и toggle;
   - selector `0`.
3. previous `today.v2/2`, horizons present:
   - backend ready;
   - selector `0`.
4. previous `today.v2/2`, horizons null:
   - legacy `long/medium/fast`;
   - selector ровно `1`.
5. mismatched identity **с horizons null**:
   - unavailable;
   - selector `0`;
   - даже присутствующий safe `whyToday` не превращается в legacy timing cards.
6. missing identity **с horizons null**:
   - unavailable;
   - selector `0`;
   - нет legacy timing cards/technical disclosure.
7. current pair с horizons present и другим валидным `contentVersion` (например,
   `999`) всё ещё backend ready и selector `0`. Это доказывает, что
   `contentVersion` сохранён, но не является feature gate.

Для новых null-horizon тестов не добавлять новые `structuredClone`/non-null
assertion. Достаточно:

~~~ts
if (!payload.v2) throw new Error("canonical fixture v2 block is missing")
const v2 = { ...payload.v2, horizons: null }
~~~

Глубокий clone не нужен, если меняется только root `horizons`.

### 4.4 Test constants

Импортировать `TodayWireIdentity` как type и объявить test constants через
`satisfies TodayWireIdentity`, без цепочки `as const` на каждом поле. Исправить
комментарий: эти constants соответствуют consumer boundary в
`components/today/why-expanded.tsx`, а не `lib/presentation/today-v2`.

В новом `TodayScreen passes adapter wireIdentity` test не использовать
`payload.wireIdentity!`; сузить локальную переменную через явную проверку.

Исправить случайно добавленные лишние leading spaces перед `expect(...)`.

## 5. Исправление R1.3 — GRACE contracts должны описывать реальную матрицу

Актуализировать только комментарии/GRACE в уже изменённых allowlist files.

### `lib/contracts/today.ts`

- добавить `WIRE_IDENTITY` в module map;
- invariant: schema identity derived from generated Today meta, no manual raw
  redeclaration;
- invariant: field optional only for old adapted artifacts; real adapter owns
  population, missing remains unknown.

### `lib/adapters/today-payload.ts`

- output/invariant явно говорит, что adapter всегда переносит exact
  payload/frontend/content identity;
- invariant: no normalization/defaulting and no full-meta spread;
- сохранить existing V2 identity/pass-through invariant.

### `components/today/today-screen.tsx`

- invariant: passes `payload.wireIdentity` to Why boundary unchanged.

### `components/today/why-expanded.tsx`

- inputs включают wire identity;
- outputs включают `horizons-unavailable`;
- MODE_RESOLUTION перечисляет новый режим;
- добавить semantic block для honest unavailable content;
- invariant: legacy selector only for exact previous accepted pair;
- invariant: current/missing/mismatched never infer horizons;
- failure policy описывает fail-closed unavailable, а не старое общее legacy
  fallback утверждение;
- в function contract держать `side_effects`, `emitted_logs`, `error_behavior`
  отдельными корректными строками;
- убрать redundant `TodayWireIdentity | undefined` внутри optional prop:
  достаточно `wireIdentity?: TodayWireIdentity`.

### Test module contracts

`TodayScreen.v2-downstream.test.tsx`:

- старый invariant `legacy selector remains reachable only when horizons are
  null/absent` неверен;
- заменить на exact previous pair + null;
- добавить current/unavailable/mismatch and order-independent spy coverage в
  purpose/map/invariants.

`adapt-payload.test.ts`:

- IDENTITY_TESTS описывает и V2 object identity, и exact wire meta identity, и
  optional old-adapted compatibility;
- invariant `No unsafe casts` должен реально выполняться.

Не менять runtime поведение ради комментариев.

## 6. Allowlist

Разрешены только текущие шесть файлов:

~~~text
lib/contracts/today.ts
lib/adapters/today-payload.ts
components/today/today-screen.tsx
components/today/why-expanded.tsx
__tests__/lib/adapt-payload.test.ts
__tests__/components/TodayScreen.v2-downstream.test.tsx
~~~

Документы `86`/`87` не редактировать. Всё остальное запрещено, включая
generated contracts, backend, fixtures, package files и unrelated paths.

## 7. Проверки

Из корня:

~~~bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.v2-downstream.test.tsx
pnpm typecheck
npx vitest run __tests__/contracts/generated-runtime.test.ts __tests__/contracts/today-fixture-roundtrip.test.ts
pnpm guardrails:prod
git diff --check
~~~

GRACE gate также повторить:

~~~bash
bash scripts/grace/check-markers.sh
~~~

Архитектор независимо подтвердил baseline failure вне allowlist:

~~~text
scripts/grace_front_lint.py:588
SyntaxError: from __future__ imports must occur at the beginning of the file
~~~

Не исправлять этот unrelated tracked file в B4.W1. Вернуть точный unchanged
failure. Это не отменяет обязанности сделать GRACE comments новых файлов
правдивыми.

Финально:

~~~bash
git diff --name-only
git diff --cached --name-only
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
git diff --check
~~~

## 8. Запрещено

- менять production mode matrix;
- ослаблять fail-closed behavior;
- `any`, unsafe casts, suppression directives или новые non-null assertions;
- order-dependent spies;
- исправлять baseline GRACE script;
- менять что-либо вне allowlist;
- commit/push/add;
- начинать B4.W2/W3, preview 3003 или services.

## 9. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W1_R1
branch: <branch>
base_sha: <sha>
changed_paths: <exact six paths>
unsafe_casts_added: 0
new_non_null_assertions: 0
spies_restored_between_tests: YES
spies_created_before_render: YES
current_ready: BACKEND_SELECTOR_0
current_null: UNAVAILABLE_SELECTOR_0
previous_ready: BACKEND_SELECTOR_0
previous_null: LEGACY_SELECTOR_1
mismatch_null: UNAVAILABLE_SELECTOR_0
missing_null: UNAVAILABLE_SELECTOR_0
content_version_not_gate: PROVEN
grace_contracts: UPDATED_TRUTHFULLY
targeted_vitest: <result>
typecheck: <result>
generated_runtime_tests: <result>
prod_guard: <result>
grace_gate: UNRELATED_BASELINE_ERROR_UNCHANGED
git_diff_check: <result>
generated_diff: EMPTY
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться.
