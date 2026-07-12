# Stage B4.W2 architectural review R3 — final contract/comment and test cleanup

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Базовый SHA: `c0c86c540a1d8f77b282ff21705758c8594d5a6e`  
Предыдущие ТЗ: `91`–`93`  
Статус: **FINAL NARROW CLEANUP — NO COMMIT / NO PUSH**

## 1. Принято

Функциональная production-логика и R2 tests приняты. Не менять copy, order,
selection, timing, filtering или accessibility behavior.

Выполнить только пункты ниже. Allowlist этой R3:

~~~text
components/today/why-time-horizon-card.tsx
components/today/horizon-actions.tsx
components/today/horizon-technique-disclosure.tsx
components/today/why-expanded.tsx
__tests__/components/TodayScreen.v2-downstream.test.tsx
~~~

Другие W2 files оставить как есть. Документы не редактировать.

## 2. Tone badge safe wrap

В backend horizon tone badge добавить безопасные local classes:

~~~text
max-w-full whitespace-normal text-center
~~~

Сохранить visible copy/data-status/style mapping. Это только защита 390px от
длинного label, без изменения UI semantics.

## 3. Repeat-click assertions and RAF lifecycle

В exact-row full TodayScreen test:

- использовать `vi.spyOn(window, "requestAnimationFrame").mockImplementation(...)`
  вместо прямого присваивания global function;
- spy создать до click;
- в `finally` нельзя оборачивать весь test, если это ухудшает читаемость;
  достаточно explicit `rafSpy.mockRestore()` в конце при существующем
  `beforeEach vi.restoreAllMocks`, но не присваивать `origRaf` вручную;
- после второго click дополнительно assert:

~~~text
workRow aria-expanded == true
details still data-sphere-key == work
workRow data-status remains initial status
~~~

Существующие row-own scroll/focus assertions сохранить.

## 4. Test module map truth

В `TodayScreen.v2-downstream.test.tsx` module map добавить semantic blocks:

~~~text
HUMAN_DOM_ORDER
EXACT_TIMING_MATRIX
TECHNICAL_ACCESSIBILITY_MATRIX
SPHERE_NAVIGATION_MATRIX
MISSING_ROW_FILTERING
~~~

Invariants добавить:

- W2 test helpers use explicit narrowing, no new unsafe/non-null assertions;
- exact element spies prove row target, not container.

Не менять tests кроме пункта 3.

## 5. Production GRACE exactness

### `why-time-horizon-card.tsx`

Заменить generic outputs на перечисление публичных backend selectors:

~~~text
why-horizon
why-horizon-index
why-horizon-tone
why-horizon-meaning
why-horizon-timing + range/peak/state
why-horizon-manifestations
why-horizon-patterns + strength/risk
why-horizon-guidance
why-horizon-spheres + sphere
why-horizon-technical-toggle/content
legacy why-time-horizon
~~~

Добавить invariant exact backend copy/order preserved; current wording про tone,
DOM order, matched rows, touch target and closed tech сохранить.

Module map разделить хотя бы на:

~~~text
BACKEND_TONE_PRESENTATION
BACKEND_HORIZON_HEADER_AND_MEANING
BACKEND_TIMING
BACKEND_MANIFESTATIONS_AND_PATTERNS
BACKEND_GUIDANCE_AND_SPHERES
BACKEND_TECHNICAL_DISCLOSURE
LEGACY_HORIZON_CARD
~~~

### `horizon-actions.tsx`

Invariants добавить:

- DOM order validity -> do -> avoid;
- responsive CSS does not reorder DOM;
- output omitted никогда не сортирует backend arrays.

Module map:

~~~text
VALIDITY
ACTION_GRID
~~~

### `horizon-technique-disclosure.tsx`

Invariants добавить:

- one `useId` suffix owns toggle/region pair;
- required generated horizon repeated on wrapper/toggle/region;
- closed content absent from DOM;
- backend explanations/timing preserve order/copy.

### `why-expanded.tsx`

Invariants добавить:

- backend intro renders exact eyebrow/headline/body without generic narrative;
- backend horizon items preserve backend order.

Module map добавить:

~~~text
BACKEND_HORIZONS_INTRO
BACKEND_HORIZONS_LIST
~~~

Не дублировать keys, поля contract в canonical order. Logs не добавлять.

## 6. Gates

~~~bash
npx vitest run __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
pnpm typecheck
git diff --check
git diff --name-only
git diff --cached --name-only
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
~~~

Full suite/build уже свежие и production runtime в R3 не меняется кроме CSS
wrap; повтор full suite не обязателен для coder callback. Архитектор выполнит
финальную независимую полную приёмку.

## 7. Запрещено

- менять product behavior/copy/order;
- добавлять tests вне repeat assertions;
- unsafe casts/non-null assertions;
- files вне exact 5;
- subagents;
- add/commit/push;
- W3/3003/services.

## 8. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W2_R3
changed_now: EXACT_5
product_behavior: UNCHANGED
tone_badge_wrap: PASS
raf_spy_lifecycle: PASS
same_repeat_expanded_details_status: PASS
test_module_map: TRUTHFUL
card_grace_contract: COMPLETE
actions_grace_contract: COMPLETE
technical_grace_contract: COMPLETE
why_intro_grace_contract: COMPLETE
targeted_vitest: <exact>
typecheck: PASS
git_diff_check: PASS
generated_diff: EMPTY
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться.
