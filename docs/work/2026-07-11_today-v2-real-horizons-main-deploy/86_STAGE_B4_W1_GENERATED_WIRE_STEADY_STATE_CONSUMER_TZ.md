# Stage B4.W1 ТЗ — generated-wire steady-state consumer без frontend-пересчёта

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Базовый SHA: `1a944717efa7a70124f81cb950992998491bf72e`  
Родительское ТЗ: `80_STAGE_B4_FRONTEND_REAL_DATA_PREVIEW_MASTER_TZ.md`  
Статус: **AUTHORIZED IMPLEMENTATION WAVE — NO COMMIT / NO PUSH**

## 0. Роль исполнителя и жёсткая граница волны

Ты кодер. Архитект уже закрыл продуктовую и контрактную развилку ниже; не
выбирай другой вариант и не расширяй задачу.

В этой волне нужно сделать только steady-state consumer для уже существующего
сгенерированного `TodayPayload`. Не делать визуальный редизайн B4.W2, launcher
на `3003`, Playwright real-preview, backend, OpenAPI, генерацию новых контрактов,
systemd, nginx, auth, commit или push.

Не использовать субагентов и делегирование.

## 1. Preflight — выполнить до правок

Из корня `/opt/solarsage-astro`:

~~~bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
git diff --cached --name-only
~~~

Ожидается:

- ветка `preview/solarsage-v2-human-first-navigator-ux`;
- local HEAD и origin равны базовому SHA из шапки;
- index пуст;
- tracked tree чист;
- допустимы только уже известные unrelated untracked paths:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Если есть иной tracked diff или staged path — остановись и верни точный список,
ничего не исправляя.

## 2. Подтверждённая текущая архитектура

Не исследуй заново и не меняй эти решения:

1. `lib/grace/api/client.ts::fetchDay` уже валидирует сырой HTTP JSON через
   generated `TodayPayloadWireSchema` и только после этого возвращает
   `TodayPayload`.
2. `lib/adapters/today-payload.ts` — чистая граница wire -> UI. Сейчас она
   сохраняет `v2` по identity, но теряет `api.meta`, поэтому UI не может
   отличить актуальный wire pair от старого cached pair.
3. Текущий production pair:

~~~text
payloadVersion = today.v2.1
frontendPayloadVersion = 3
~~~

4. Единственный старый pair, которому разрешён selector-derived migration
   fallback:

~~~text
payloadVersion = today.v2
frontendPayloadVersion = 2
~~~

5. `contentVersion` нужно сохранить для наблюдаемости и будущих тестов, но **не
   использовать как feature gate**: контентная версия может расти без смены
   структуры wire-контракта.
6. Для текущего pair при `v2.horizons === null` нельзя вызывать
   `selectWhyTimeHorizons`, нельзя строить даты/фазы/советы на фронте и нельзя
   подменять отсутствие backend-owned блока старыми тремя карточками.
7. Generated TypeScript/Zod — единственный источник raw wire shape. Ручную
   копию `TodayMeta`, `TodayV2*` или enum payload versions не создавать.

## 3. Закрытое архитектурное решение

### 3.1 UI wire identity

В `lib/contracts/today.ts` добавить UI-поле `wireIdentity` со строго тремя
полями:

~~~text
payloadVersion
frontendPayloadVersion
contentVersion
~~~

Runtime schema этого объекта получить **из generated wire schema**, а не
переписать вручную. Использовать существующий
`TodayPayloadWireSchema.shape.meta.pick(...)` либо эквивалентный type-safe pick
из той же generated schema. Не добавлять ручной `z.enum(["today.v1", ...])`.

Рекомендуемые публичные имена:

~~~ts
TodayWireIdentitySchema
TodayWireIdentity
~~~

Добавить `wireIdentity` в `TodayPayloadSchema` как optional compatibility field:

~~~text
wireIdentity: TodayWireIdentitySchema.optional()
~~~

Optional нужен только потому, что tracked старые adapted audit fixtures были
созданы до этого поля. Это **не** означает optional в реальном fetch flow:
`adaptTodayPayload` обязан всегда его заполнить. Зафиксировать оба инварианта в
GRACE module contract/comments:

- real adapter output always carries exact generated meta identity;
- missing identity is treated as unknown/fail-closed, а не как legacy V2.

Не переносить в UI весь `api.meta`: только три перечисленных поля, без spread.

### 3.2 Adapter

В `adaptTodayPayload` добавить:

~~~ts
wireIdentity: {
  payloadVersion: api.meta.payloadVersion,
  frontendPayloadVersion: api.meta.frontendPayloadVersion,
  contentVersion: api.meta.contentVersion,
}
~~~

Требования:

- значения копируются точно, без default/normalization/coercion;
- `v2` остаётся тем же объектом по identity;
- порядок/копирайтинг/provenance/horizons не меняются;
- повторного production parse не добавлять: fetch boundary уже провалидирован;
- никаких импортов mocks/demo/e2e в production modules.

### 3.3 Передача в UI

В `TodayScreen` передать `payload.wireIdentity` в `WhyExpanded` отдельным prop.
Тип prop — `TodayWireIdentity | undefined` из `lib/contracts/today.ts`.

Не читать версии из `v2.audit`: там нет полного frontend/content identity, и
audit не является consumer-routing boundary.

### 3.4 Закрытая таблица выбора режима

Расширить `resolveWhyExpandedMode` входом `wireIdentity` и одним новым режимом
`horizons-unavailable`.

Реализовать ровно эту матрицу:

| Wire identity | `v2` | `v2.horizons` | Режим | Selector |
|---|---:|---:|---|---:|
| `today.v2.1` + `3` | есть | есть | `backend-horizons` | **never** |
| `today.v2.1` + `3` | есть | `null` | `horizons-unavailable` | **never** |
| `today.v2` + `2` | есть | есть | `backend-horizons` | **never** |
| `today.v2` + `2` | есть | `null` | `legacy-v2` | разрешён ровно здесь |
| missing / иной / mismatched pair | есть | любое | `horizons-unavailable` | **never** |
| любое | нет | n/a | существующий `human-only -> legacy -> empty` порядок | never |

Дополнительные правила:

- текущий pair определяется только совместным совпадением двух полей;
- `contentVersion` не участвует в mode resolution;
- `today.v2.1 + 2`, `today.v2 + 3`, `today.v1 + 1` при наличии `v2`, а также
  missing identity считаются несовместимыми и fail-closed;
- сам факт наличия `v2.horizons` не должен обходить проверку pair;
- `selectWhyTimeHorizons(v2)` вычислять лениво только если итоговый mode ровно
  `legacy-v2`; не вызывать его до mode resolution и не вызывать в unavailable;
- standalone `whyToday`/legacy sections продолжают работать как раньше только
  когда `v2` отсутствует. При несовместимом `v2` не маскировать проблему
  приблизительным human-only timing story.

Версионные pair-константы допустимы как consumer routing constants, но не как
ручная Zod/raw schema. Имена должны явно различать current и previous accepted
pair.

### 3.5 Honest unavailable state

Внутри уже существующего top-level блока `data-testid="why-expanded"` для mode
`horizons-unavailable` показать стабильный самостоятельный section:

~~~text
data-testid="why-horizons-unavailable"
data-state="empty"
data-source="backend-horizons"
~~~

Зафиксированный пользовательский текст:

~~~text
Три временных горизонта пока недоступны

Мы покажем их, когда получим подтверждённые сроки и персональные связи. Не будем заменять их приблизительной версией.
~~~

Допустимо разбить эти две строки на heading/paragraph, но не менять смысл и не
добавлять технические термины (`профекция`, `фирдар`, `транзит`, `орб`) или raw
version numbers. Цвет не должен быть единственным носителем состояния.

Unavailable state должен отображаться даже если в `v2` нет usable legacy
evidence, `whyToday` пуст и legacy sections пусты. То есть top-level Why block в
этом режиме не скрывать.

Backend ready state сохраняет текущий публичный DOM:

~~~text
data-testid="why-horizons"
data-state="ready"
data-source="backend-horizons"
~~~

Карточки сохраняют `data-testid="why-horizon"`, `data-horizon`, `data-status` и
`data-timing-state` без изменений.

## 4. Точные изменения по файлам

Разрешённый implementation allowlist:

~~~text
lib/contracts/today.ts
lib/adapters/today-payload.ts
components/today/today-screen.tsx
components/today/why-expanded.tsx
__tests__/lib/adapt-payload.test.ts
__tests__/components/TodayScreen.v2-downstream.test.tsx
~~~

Плюс этот уже созданный архитектором документ, который менять не требуется:

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/86_STAGE_B4_W1_GENERATED_WIRE_STEADY_STATE_CONSUMER_TZ.md
~~~

Любой иной tracked path запрещён. В частности не менять:

~~~text
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
packages/contracts/openapi.json
packages/contracts/index.ts
packages/contracts/runtime.ts
apps/api/**
app/**
e2e/**
package.json
pnpm-lock.yaml
next.config.*
systemd/nginx/env files
~~~

И всегда не трогать unrelated paths из preflight.

## 5. Обязательные тесты

### 5.1 Adapter/contract tests

В `__tests__/lib/adapt-payload.test.ts` доказать:

1. `today.v1 / 1 / content 1` сохраняются в `wireIdentity` точно.
2. canonical `today.v2.1 / 3 / content 10` сохраняются точно.
3. `payload.v2` всё ещё равен исходному `v2Block` по object identity.
4. adapted payload с новым полем валиден.
5. старый вручную собранный adapted payload без `wireIdentity` всё ещё может
   пройти UI schema для compatibility, но никакой identity не фабрикуется.

Не менять canonical JSON fixture ради этих тестов.

### 5.2 Component/mode tests

В `TodayScreen.v2-downstream.test.tsx` создать явные test constants для current
и previous pair, чтобы каждый direct render документировал режим.

Обязательно доказать:

1. current pair + horizons:
   - `why-horizons` ready/backend;
   - три backend cards в порядке `long, medium, fast`;
   - selector spy вызван `0` раз.
2. current pair + `horizons=null`:
   - top-level Why видим;
   - `why-horizons-unavailable[data-state=empty]` видим;
   - `data-source=backend-horizons`;
   - пользовательский текст присутствует;
   - нет `why-horizons`, `why-time-horizon`, astrology calculation;
   - selector spy вызван `0` раз.
3. previous accepted pair + `horizons=null`:
   - старые selector cards `long, medium, fast` сохраняются;
   - selector spy вызван ровно `1` раз;
   - nested technical disclosure работает как раньше.
4. mismatched/missing identity + `v2`:
   - unavailable;
   - selector spy `0`;
   - safe `whyToday` не превращается в подменные timing cards.
5. no-`v2` branches (`human-only`, `legacy`, `empty`) не регрессируют.
6. `TodayScreen` реально передаёт adapter identity: canonical adapted payload
   через полный экран открывает backend-owned horizons, а не incompatible state.

Все существующие legacy-selector тесты с `v2.horizons=null`, которые проверяют
старую миграционную ветку, явно передать `previousWireIdentity`. Не оставлять их
на implicit/missing identity.

Не ослаблять существующие проверки отсутствия `Transit_`/`Natal_`, технической
лексики в human copy, activation-id integrity, sphere navigation и timing attrs.

## 6. GRACE и качество реализации

Для каждого существенно изменённого TS/TSX файла актуализировать существующие:

- `AI_HEADER` / role при необходимости;
- `START_MODULE_CONTRACT` inputs/outputs/invariants/failure policy;
- `START_MODULE_MAP` semantic blocks/tests;
- function contract у `resolveWhyExpandedMode` и иных нетривиальных новых
  функций.

Не добавлять logger events: эта волна не вводит новый side effect. В
`emitted_logs` оставить `none` там, где это правда.

Не использовать `any`, `as unknown as`, non-null assertions для обхода типов,
парсинг текста, frontend timing calculation или advice generation.

## 7. Проверки после реализации

Запускать из корня репозитория в указанном порядке:

~~~bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.v2-downstream.test.tsx
pnpm typecheck
npx vitest run __tests__/contracts/generated-runtime.test.ts __tests__/contracts/today-fixture-roundtrip.test.ts
bash scripts/grace/check-markers.sh
pnpm guardrails:prod
git diff --check
~~~

После `scripts/grace/check-markers.sh` не исправлять unrelated старые ошибки
вне allowlist. Если gate падает только на существующем файле вне allowlist,
вернуть точную ошибку архитектору.

Финальная механическая сверка:

~~~bash
git diff --name-only
git diff --cached --name-only
git status --short --branch
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
git diff -- .grace artifacts/design docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md grace.db skills
~~~

Ожидается:

- diff только в шести implementation files из allowlist;
- generated contract diff пуст;
- index пуст;
- commit/push не созданы;
- unrelated paths untouched;
- B4.W2/W3 не начаты.

## 8. Запрещено

- `git add`, commit, push;
- переключать ветку;
- редактировать generated contract/OpenAPI;
- менять backend или cache;
- запускать/restart systemd, nginx, API, sidecar, production frontend;
- поднимать `3003` в этой волне;
- добавлять fixture/runtime mock path;
- импортировать `lib/mocks`, `lib/demo-data`, `e2e` из product code;
- вызывать legacy selector для current/missing/mismatched identity;
- начинать tone-copy/visual polish B4.W2;
- исправлять любой unrelated diff.

## 9. Точный callback и остановка

После проверок вернуть архитектору один callback:

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W1
branch: <branch>
base_sha: <sha>
changed_paths:
- <path>
...
wire_identity_schema: GENERATED_META_PICK
adapter_identity: EXACT payload/frontend/content
current_pair_horizons: BACKEND_ONLY
current_pair_null: UNAVAILABLE_SELECTOR_0
previous_pair_null: LEGACY_SELECTOR_1
mismatch_or_missing: UNAVAILABLE_SELECTOR_0
targeted_vitest: <result>
typecheck: <result>
generated_runtime_tests: <result>
grace: <result>
prod_guard: <result>
git_diff_check: <result>
generated_diff: EMPTY
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановись и жди архитектурного ревью.
