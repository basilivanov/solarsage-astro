# Stage B4.W2 architectural review R1 — complete proof, typed accessibility, truthful GRACE

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Базовый SHA: `c0c86c540a1d8f77b282ff21705758c8594d5a6e`  
Предыдущее ТЗ: `91_STAGE_B4_W2_FINAL_HUMAN_FIRST_UX_TZ.md`  
Статус: **ARCH REVIEW REJECTED UNTIL CORRECTED — NO COMMIT / NO PUSH**

## 1. Что принято и не переписывается

Текущий production diff правильно реализует основную композицию:

- backend card order сохранён;
- meaning перенесён перед timing;
- manifestations стоят перед strength/risk;
- actions стоят перед sphere links;
- technical disclosure последний;
- tone/sphere visible copy соответствует ТЗ;
- TodayScreen guard и exact target-row scroll/focus концептуально верны;
- backend intro стал semantic header.

Не менять эти решения и не возвращать старый порядок.

## 2. Причины отклонения

### Критические

1. Новый `ConcreteDayAdvice.keyboard.test.tsx` использует:

~~~ts
{ key: "love", ... } as any
~~~

`love` не входит в generated sphere enum, `as any` прямо запрещён, а module
invariant этого же файла утверждает `No unsafe casts`.

2. Почти весь обязательный test matrix из раздела 9 ТЗ `91` отсутствует:

- нет card index proof;
- нет DOM order proof;
- нет timing child selector proof;
- нет closed technical leakage proof;
- нет full ARIA/id/data-horizon proof;
- нет exact row scroll/focus/repeat-click/status proof;
- нет missing-row/no-fabrication proof;
- нет legacy constant absence proof.

Callback не может заявлять эти свойства без тестов.

3. `HorizonTechniqueDisclosure` принимает `horizon?: string`, хотя ТЗ требует
required closed generated horizon type. Toggle не имеет `data-horizon`.

### Существенные

4. Sphere chip остаётся ниже 44px (`py-1.5` без min-height).
5. GRACE contracts шести production files практически не обновлены под новый
DOM/order/status/navigation contract.
6. Test file получил неполный GRACE contract: отсутствуют inputs/outputs,
module map, failure policy; `side_effects` и `emitted_logs` склеены в одну строку.
7. Callback указал full suite `1012`, хотя добавлены два новых tests к ранее
подтверждённым `1012`; требуется fresh run и реальный итог, не старое число.

## 3. Preflight и allowlist

Продолжать поверх текущего незакоммиченного W2 diff. Index пуст, HEAD/origin на
базовом SHA. Разрешены те же восемь implementation/test paths:

~~~text
components/today/why-expanded.tsx
components/today/why-time-horizon-card.tsx
components/today/horizon-actions.tsx
components/today/horizon-technique-disclosure.tsx
components/today/concrete-day-advice.tsx
components/today/today-screen.tsx
__tests__/components/TodayScreen.v2-downstream.test.tsx
__tests__/components/ConcreteDayAdvice.keyboard.test.tsx
~~~

Документы `91`/`92` не редактировать. Иные paths запрещены.

## 4. R1.1 — type-safe verdict test без дублирования

В `ConcreteDayAdvice.keyboard.test.tsx`:

1. Удалить `love`, `as any` и unused `rerender`.
2. Использовать четыре валидных distinct keys, например:

~~~text
work          -> good
money         -> caution
health        -> avoid
relationships -> neutral
~~~

3. Для каждого exact verdict проверить:

- native button;
- `data-status` exact;
- compact copy exact;
- rerender с selectedKey;
- details `data-status` exact;
- details visible copy exact;
- selected row `aria-expanded=true`;
- row `aria-controls` equals details id;
- verdict/status не изменился после selection.

4. Не создавать второй дублирующий test «all 12 buttons», если первый уже
доказывает то же самое. Либо объединить, либо оставить один canonical test.

5. Никаких `any`, `unknown as`, suppressions или новых non-null assertions.

## 5. R1.2 — полный GRACE contract test file

Для `ConcreteDayAdvice.keyboard.test.tsx` добавить полный формат:

~~~text
START_MODULE_CONTRACT: named id
purpose
owns (list)
inputs
outputs
dependencies
side_effects
emitted_logs
invariants (list)
failure_policy
END_MODULE_CONTRACT

START_MODULE_MAP
public_entrypoints
semantic_blocks
owned_tests
END_MODULE_MAP
~~~

Не склеивать поля. Invariants должны реально выполняться.

Актуализировать module contract/map `TodayScreen.v2-downstream.test.tsx`, чтобы
он явно владел human DOM order, technical accessibility и exact sphere target
navigation tests.

## 6. R1.3 — typed technical disclosure

В `horizon-technique-disclosure.tsx`:

- import type `TodayV2Horizon` либо generated equivalent;
- prop:

~~~ts
horizon: TodayV2Horizon["horizon"]
~~~

  required, не optional `string`;
- убрать redundant `horizonId` prop, если он теперь равен horizon; preferred API:

~~~ts
HorizonTechniqueDisclosure({ explanations, horizon })
~~~

- вызвать `useId()` один раз, sanitized suffix переиспользовать для toggle and
  region ids;
- wrapper, toggle и opened content имеют exact `data-horizon`;
- toggle required unique `id`;
- `aria-controls` equals exact region id;
- region `role=region` and `aria-labelledby=toggle.id`;
- content отсутствует из DOM closed;
- backend explanation/timing order/copy unchanged.

Обновить caller в horizon card.

## 7. R1.4 — touch/layout polish

В `why-time-horizon-card.tsx`:

- sphere chip `min-h-11` (>=44px), px/line-height не создают overflow;
- header text container `flex-1 min-w-0`;
- tone badge допускает безопасный wrap (`max-w-full`, no forced overflow);
- optional: объединить strength/risk в stable container
  `data-testid="why-horizon-patterns"` с `grid gap-3 sm:grid-cols-2`; если
  добавлено, empty strength не создаёт placeholder;
- не менять exact backend copy/order;
- не использовать local date parsing для backend path.

В `horizon-actions.tsx` добавить stable outer selector, например
`data-testid="why-horizon-guidance"`, и оформить do/avoid one-column mobile +
`sm:grid-cols-2` desktop. DOM order внутри: validity, do, avoid. Existing testids
сохранить.

## 8. R1.5 — полный `TodayScreen.v2-downstream` proof

Добавить все tests ниже. Не подтверждать свойства только чтением JSX.

### 8.1 Intro, indexes, tone

- `why-horizons-intro` exact backend eyebrow/headline/body;
- indexes exact `01,02,03` corresponding `long,medium,fast`;
- tone labels exact `Смешанный сигнал x2`, `Требует внимания x1`;
- old backend horizon tone labels absent:

~~~text
Смешанный фон
Напряжённый фон
Поддерживающий фон
Нейтральный фон
~~~

### 8.2 DOM order

Для long card получить stable nodes:

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

Через `compareDocumentPosition(...DOCUMENT_POSITION_FOLLOWING)` доказать exact
последовательность. Не использовать CSS class names как contract.

Для fast card доказать absence strength без пустого placeholder и правильный
порядок manifestations -> risk -> guidance -> spheres -> technical.

### 8.3 Timing child contract

- long range/state selectors exact, peak absent;
- medium range/peak/state exact;
- fast range/peak/state exact;
- text берётся verbatim из backend fixture;
- никакого frontend reformat expectation.

### 8.4 Closed human copy / technical content

До открытия всех disclosures:

- `why-horizon-technical-content` count 0;
- `why-horizons.textContent` не содержит case-insensitive:

~~~regex
/Профекция|Фирдар|транзит|орб|аппликац|return|Transit_|Natal_|activationIds|natalFactIds|profileFactIds/i
~~~

- constant legacy sentence про «три случайных факта» отсутствует.

После открытия first disclosure:

- exact Profекция/Фирдар texts and backend timing visible;
- no raw ids/provenance keys.

### 8.5 ARIA and horizon identity

Для каждого из 3 toggles:

- native button;
- unique non-empty id;
- `data-horizon` exact order long/medium/fast;
- closed `aria-expanded=false`;
- click -> `aria-expanded=true`;
- within same card region id equals toggle `aria-controls`;
- region `role=region`;
- region `aria-labelledby` equals toggle id;
- region `data-horizon` equals card horizon;
- close again or isolate test so queries не путают несколько open regions.

### 8.6 Sphere chip public contract

Для matched chip `Работа`:

- tag BUTTON;
- `data-testid`, `data-sphere-key=work`;
- visible copy exact row label;
- `aria-label=Открыть сферу «Работа» в навигаторе`;
- onSphereSelect receives exact `work` when direct component/Why render path is
  tested.

### 8.7 Full TodayScreen exact row navigation

Test must install spies on the **specific work row instance** before click:

- row-specific `scrollIntoView` spy;
- row-specific `focus` spy;
- requestAnimationFrame deterministic immediate stub/spy, restored afterward.

Then click horizon sphere chip and assert:

~~~text
row data-selected=true
row aria-expanded=true
details data-sphere-key=work
row data-status before == after
scrollIntoView exactly with {behavior:"smooth", block:"center"}
focus with {preventScroll:true}
~~~

Clear row spies, click same horizon chip again, assert scroll/focus repeat and
row remains selected (no deselect).

Не использовать prototype-wide spy для доказательства exact target: он не
показывает, какой element был вызван.

### 8.8 Missing target row

Создать type-safe adapted payload variant, где concreteAdvice rows не содержат
`work`, а long horizon likelySpheres по-прежнему содержит `work`.

Assert:

- no `why-horizon-sphere[data-sphere-key="work"]`;
- никакого fallback `Работа` chip;
- другие реально matched chips сохраняются;
- no selection/scroll/focus for missing target.

Не менять fixture file.

## 9. R1.6 — truthful production GRACE

Актуализировать existing contracts/maps в шести production files.

### `why-time-horizon-card.tsx`

- outputs/testids and exact DOM order;
- enum-only tone map;
- backend copy/order exact;
- matched-row-only spheres;
- technical last/closed leakage invariant;
- semantic blocks for backend header/meaning/timing/manifestations/patterns/
  actions/spheres/technical plus legacy card.

### `horizon-actions.tsx`

- outputs validity/guidance/actions/avoid selectors;
- exact order and responsive layout;
- backend order/copy invariant.

### `horizon-technique-disclosure.tsx`

- required typed horizon input;
- outputs data-horizon/id/aria linkage;
- single useId suffix;
- closed content absent invariant.

### `concrete-day-advice.tsx`

- exact visible verdict map;
- color secondary;
- data-status remains backend verdict enum;
- 12 rows/order/selection unchanged.

### `today-screen.tsx`

- target-existence guard;
- exact matching row scroll/focus;
- same-selected repeat behavior;
- missing target no-op.

### `why-expanded.tsx`

- backend intro semantic header selector;
- exact backend intro copy/order;
- no frontend generic narrative.

Fields must be separate and canonical. No invented logs; emitted_logs `none`.

## 10. Fresh gates and honest count

~~~bash
npx vitest run __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
pnpm typecheck
npx vitest run
pnpm guardrails:prod
NEXT_DIST_DIR=.next-b4-w2-candidate pnpm build
bash scripts/grace/check-markers.sh
git diff --check
~~~

Удалить только generated `.next-b4-w2-candidate` после build. Вернуть exact
fresh full Vitest summary из stdout. Не писать заранее `1012`; количество должно
соответствовать текущим tests.

Grace baseline SyntaxError вне allowlist не исправлять.

Финально доказать exact 8 tracked paths, empty index, empty generated diff.

## 11. Запрещено

- менять accepted W1 routing;
- менять backend/contracts/fixtures/e2e/assets;
- добавлять invalid enum data;
- unsafe casts/suppressions/new non-null assertions;
- callback claims без test proof;
- subagents;
- commit/push/add;
- 3003/services/W3/main.

## 12. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W2_R1
changed_paths: EXACT_8
unsafe_casts_added: 0
invalid_sphere_keys: 0
test_grace_contract: COMPLETE
production_grace_contracts: COMPLETE
human_dom_order_test: PASS
card_indexes_test: PASS
timing_children_test: PASS
closed_technical_leakage_test: PASS
technical_aria_matrix_test: PASS
technical_horizon_type: GENERATED_REQUIRED
sphere_chip_touch_target: 44PX_MIN
sphere_chip_contract_test: PASS
exact_row_scroll_focus_test: PASS
same_sphere_repeat_test: PASS
missing_row_test: PASS
verdict_copy_matrix_test: PASS
targeted_vitest: <exact summary>
full_vitest: <fresh exact summary>
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
