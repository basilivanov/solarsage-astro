# Stage B4.W2 architectural review R2 — proof must test the claimed behavior

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Базовый SHA: `c0c86c540a1d8f77b282ff21705758c8594d5a6e`  
Предыдущие ТЗ: `91`, `92`  
Статус: **SECOND REVIEW CORRECTIONS — NO COMMIT / NO PUSH**

## 1. Не менять принятую production-композицию

Сохранить текущий порядок, copy mappings, target guard, exact-row production
scroll/focus и responsive layout. R2 исправляет только ложноположительные tests,
тип/DOM toggle и неактуальные GRACE contracts.

Allowlist остаётся exact 8 W2 paths. Документы не редактировать. Всё остальное
запрещено.

## 2. Подтверждённые проблемы R1

1. Callback заявляет `exact_row_scroll_focus_test` и
   `same_sphere_repeat_test`, но таких tests в файле нет.
2. Missing-row test рендерит только `ConcreteDayAdvice`, в котором по определению
   нет `why-horizon-sphere`, поэтому assertion `0` тривиален и не проверяет
   filtering horizon links.
3. Technical ARIA test проверяет `t.closest("[data-horizon]")`, тогда как toggle
   сам не имеет required `data-horizon`.
4. Новые tests используют много `!` (`querySelector(...)!`, `id!`, `regionId!`,
   `row!`) вопреки запрету новых non-null assertions.
5. Verdict matrix проверяет details copy только для `good`, а callback заявляет
   полный matrix.
6. Long DOM order test пропускает exact strength/risk/validity/actions/avoid
   nodes; fast optional-strength path не проверен.
7. Timing test проверяет только фрагменты строк, не exact backend labels для всех
   range/peak/state.
8. Production GRACE contracts всё ещё описывают старый API:
   tech inputs упоминает `horizonId`, card/actions outputs/maps не отражают новый
   DOM, TodayScreen/Why/Concrete contracts не фиксируют новые invariants.

## 3. R2.1 — никаких новых non-null assertions

В обоих test files удалить все non-null assertions, добавленные W2/R1.

Допустимый test helper:

~~~ts
function requireElement<T extends Element>(value: T | null | undefined, label: string): T {
  if (!value) throw new Error(`${label} is missing`)
  return value
}
~~~

Для string attributes использовать аналогичное явное narrowing. Не применять
`as`, `!`, suppression directives для обхода null/types в новом W2 block.
Старый pre-existing code вне изменяемых assertions не переписывать.

## 4. R2.2 — verdict matrix действительно все четыре details states

В `ConcreteDayAdvice.keyboard.test.tsx` для каждого:

~~~text
good / work
caution / money
avoid / health
neutral / relationships
~~~

последовательно rerender selectedKey и доказать:

- row exact `data-status` before selection;
- exact compact copy;
- selected row `aria-expanded=true`;
- `aria-controls == details.id`;
- details exact `data-status`;
- details exact visible details copy;
- row `data-status` после selection unchanged.

После каждого rerender заново находить row в current DOM. Не ограничиваться
первым `good`.

Первый canonical 12-row test остаётся единственным доказательством all 12/order.
Название matrix test не должно утверждать, что его 4-row fixture содержит 12.

## 5. R2.3 — direct toggle `data-horizon`

Production `HorizonTechniqueDisclosure`:

~~~text
wrapper data-horizon
toggle data-horizon
opened region data-horizon
~~~

все exact required generated horizon.

ARIA test должен проверять:

~~~ts
toggle.getAttribute("data-horizon") === expectedHorizon
~~~

Не использовать `closest` как подмену. Exact toggle id/controls/region label
остаются.

## 6. R2.4 — exact DOM order test

Для long card через safe helper получить:

~~~text
meaning
timing
manifestations
strength
risk
validity
actions
avoid
spheres
technical toggle
~~~

Assert every adjacent relation with `DOCUMENT_POSITION_FOLLOWING`:

~~~text
meaning < timing < manifestations < strength < risk
< validity < actions < avoid < spheres < tech
~~~

Для fast card assert:

- `why-horizon-strength` absent;
- patterns container exists without fabricated placeholder;
- manifestations < risk < validity < actions < avoid < spheres < tech.

## 7. R2.5 — exact timing strings

Use `textContent` exact:

~~~text
long:
  range = Период: 12 мая 2026 — 11 мая 2027
  peak absent
  state = Сейчас: Фон уже действует

medium:
  range = Период: 3–18 июля
  peak = Пик: Точный пик — 10 июля, 14:32 по Москве
  state = Сейчас: Набирает силу

fast:
  range = Период: 8–10 июля по Москве
  peak = Пик: Пик был 8 июля в 08:00
  state = Сейчас: Пик уже пройден
~~~

Если JSX вставляет whitespace, нормализовать только DOM whitespace в test
helper; не делать contains partial-date assertions.

## 8. R2.6 — real exact-row scroll/focus + same-click test

Добавить реальный full `TodayScreen` test.

Setup:

1. `navigationState.search = "why=1"`.
2. Render canonical `TodayScreen`.
3. Найти exact work navigator row до click по public testids/data-sphere-key.
4. Запомнить его `data-status`.
5. Установить own-property spies на этот element через configurable
   `Object.defineProperty`:

~~~text
workRow.scrollIntoView = rowScrollSpy
workRow.focus = rowFocusSpy
~~~

6. `requestAnimationFrame` сделать deterministic immediate spy/stub до click и
   восстановить в конце/через test lifecycle.
7. Найти horizon chip `data-sphere-key=work` и click.

Assert после первого click:

~~~text
work row data-selected=true
work row aria-expanded=true
details data-sphere-key=work
status before == after
rowScrollSpy called with {behavior:"smooth", block:"center"}
rowFocusSpy called with {preventScroll:true}
~~~

Затем clear только row spies, click тот же chip ещё раз, assert:

- scroll/focus повторились;
- row остаётся selected/expanded;
- details всё ещё work;
- никакого deselect effect.

Test должен падать, если production снова scroll-ит общий navigator container.

## 9. R2.7 — non-trivial missing-row test

Не рендерить только `ConcreteDayAdvice`.

Сделать type-safe filtered `concreteAdvice` без row `work`, затем render
`WhyExpanded` в current backend-horizons mode с:

~~~text
v2 = canonical backend horizons (long likelySpheres still contains work)
wireIdentity = current
concreteAdvice = filtered
onSphereSelect = spy
open = true
~~~

Assert:

- no horizon chip with `data-sphere-key=work`;
- no visible button with accessible name `Открыть сферу «Работа» в навигаторе`;
- at least one other matched chip exists, например `decisions` или `money`;
- click other matched chip calls spy with exact key;
- no fallback/fabricated work label.

Этот test должен проходить через `WhyTimeHorizonCard` filtering.

## 10. R2.8 — sphere chip callback contract

Direct Why render с `onSphereSelect=vi.fn()`:

- work chip native button/data/aria/visible copy;
- click -> callback once with exact `work`.

Touch target structural class `min-h-11` можно проверить дополнительно, но это
не заменяет callback assertion.

## 11. R2.9 — GRACE comments must match code

Исправить comments, не runtime:

### `horizon-technique-disclosure.tsx`

- inputs: required generated horizon, no `horizonId`;
- outputs include wrapper/toggle/region data-horizon, unique ids and aria link;
- invariant single useId suffix, closed content absent, backend order exact.

### `why-time-horizon-card.tsx`

- outputs include index/meaning/timing children/manifestations/patterns/guidance/
  spheres/technical selectors;
- invariants multiline: exact backend copy/order, enum tone, human DOM order,
  matched-row-only chips, >=44px chip, technical last/closed;
- module map lists backend semantic regions separately and legacy card.

### `horizon-actions.tsx`

- outputs guidance/validity/actions/avoid;
- invariant DOM order validity -> do -> avoid; responsive only CSS;
- module map reflects validity + action grid.

### `concrete-day-advice.tsx`

- invariant exact four visible mappings and color-secondary semantics;
- data-status stays exact verdict; unknown neutral fallback.

### `today-screen.tsx`

- side effects/invariants exact row scroll/focus, existing-row guard, same-key
  repeat, missing no-op.

### `why-expanded.tsx`

- outputs/map include `why-horizons-intro` semantic header;
- invariant exact backend intro copy/order and no generic narrative.

### `TodayScreen.v2-downstream.test.tsx`

- purpose/map/invariants own human DOM order, exact timing, technical ARIA,
  exact row navigation, missing-row filtering tests.

No duplicate contract keys; canonical field order; no invented logs.

## 12. Gates

~~~bash
npx vitest run __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
pnpm typecheck
npx vitest run
pnpm guardrails:prod
NEXT_DIST_DIR=.next-b4-w2-candidate pnpm build
bash scripts/grace/check-markers.sh
git diff --check
~~~

Удалить только isolated candidate dist. Fresh full count вернуть exact.
Unrelated Grace SyntaxError не исправлять.

## 13. Запрещено

- false/trivial tests;
- new non-null assertions/unsafe casts;
- checking ancestor instead of public target contract;
- changing accepted product order/copy;
- paths outside exact 8;
- subagents;
- add/commit/push;
- W3/3003/services/backend/contracts/fixtures/e2e/assets.

## 14. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W2_R2
changed_paths: EXACT_8
new_non_null_assertions: 0
unsafe_casts: 0
verdict_details_all_4: PASS
toggle_data_horizon_direct: PASS
long_exact_dom_order: PASS
fast_optional_dom_order: PASS
timing_exact_strings: PASS
exact_row_own_spies: PASS
same_chip_repeat: PASS
missing_row_real_why_render: PASS
sphere_callback_exact: PASS
grace_comments_truthful: PASS
targeted_vitest: <exact>
full_vitest: <exact fresh>
typecheck: PASS
prod_guard: PASS
isolated_build: PASS
isolated_dist_removed: YES
grace_gate: UNRELATED_BASELINE_ERROR_UNCHANGED
git_diff_check: PASS
generated_diff: EMPTY
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться.
