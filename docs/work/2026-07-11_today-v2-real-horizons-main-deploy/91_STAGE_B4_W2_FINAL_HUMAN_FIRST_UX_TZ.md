# Stage B4.W2 ТЗ — final human-first horizons UX and exact 12-sphere navigation

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Базовый SHA: `c0c86c540a1d8f77b282ff21705758c8594d5a6e`
Prerequisite: accepted and pushed B4.W1
Родительское ТЗ: `80_STAGE_B4_FRONTEND_REAL_DATA_PREVIEW_MASTER_TZ.md`
Статус: **AUTHORIZED IMPLEMENTATION WAVE — NO COMMIT / NO PUSH**

## 0. Роль и граница

Ты кодер. Реализуй только B4.W2 поверх принятого generated-wire consumer.
Архитектурные и продуктовые решения ниже закрыты: не придумывай новые тексты,
астрологическую логику, поля контракта или альтернативную композицию.

Не использовать субагентов/делегирование. Не делать commit/push. Не запускать
B4.W3 launcher/real E2E, не менять backend/contracts/auth/routes/fixtures/services.

## 1. Preflight

~~~bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short --branch
git diff --cached --name-only
~~~

Ожидается:

- exact preview branch;
- local/origin exact базовый SHA;
- tracked tree и index чисты;
- только известные unrelated untracked paths:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Любой иной diff — blocker.

## 2. Product outcome

Backend-owned `v2.horizons` уже содержит весь подтверждённый контент. Frontend
должен сделать его легко читаемым человеку, который не знает терминов
профекция/фирдар/транзит/орб.

Три карточки остаются отдельными зонами и идут в backend order:

~~~text
long   -> 01, backend eyebrow начинается с «Долгий цикл»
medium -> 02, backend eyebrow начинается с «Текущий период»
fast   -> 03, backend eyebrow начинается с «Быстрый триггер»
~~~

Не парсить и не обрезать backend eyebrow. Показывать его дословно; frontend
добавляет только визуальный номер `01/02/03` по закрытому `horizon` enum.

### Единственный DOM/визуальный порядок внутри backend horizon card

~~~text
1. номер + backend eyebrow + backend title + visible tone
2. human meaning: summary, затем plainExplanation
3. backend timing: range, optional peak, current state
4. manifestations («Где это вероятнее проявится»)
5. optional strength / optional risk
6. actions heading + validity + ordered do/avoid
7. matched clickable links into 12-sphere navigator
8. closed technical disclosure «Как это рассчитано»
~~~

Это порядок DOM, а не только CSS. Не оставлять timing раньше human meaning,
strength/risk раньше manifestations или sphere chips раньше actions.

Intro над карточками использует только backend `intro.eyebrow/headline/body`.
Не добавлять постоянную фразу «Это не три случайных факта» или другой
frontend-authored narrative. Она не должна быть одинаковой для всех людей.

## 3. Closed tone presentation

Для `TodayV2Horizon.tone` использовать ровно эту visible mapping:

~~~text
supportive -> Поддерживает
neutral    -> Ровный фон
tense      -> Требует внимания
mixed      -> Смешанный сигнал
~~~

Требования:

- mapping только по enum, никогда по тексту/цвету;
- root card и badge сохраняют exact `data-status` backend enum;
- visible text обязателен: цвет вторичен;
- styles могут остаться в текущих semantic palettes (emerald/slate/rose/violet),
  но contrast должен работать в light/dark;
- не использовать старые visible labels `Поддерживающий фон`,
  `Нейтральный фон`, `Напряжённый фон`, `Смешанный фон` для horizon cards.

## 4. Human card composition

Файл: `components/today/why-time-horizon-card.tsx`.

### 4.1 Header

- добавить визуальный круг/rail с номером `01/02/03`;
- стабильный selector `data-testid="why-horizon-index"`;
- backend eyebrow и title вывести дословно;
- tone badge допускает перенос рядом/ниже, не ломает 390px;
- root сохраняет:

~~~text
data-testid="why-horizon"
data-horizon="long|medium|fast"
data-status="supportive|neutral|tense|mixed"
data-timing-state="..."
~~~

### 4.2 Meaning before timing

Обернуть `summary` + `plainExplanation` в:

~~~text
data-testid="why-horizon-meaning"
~~~

Не объединять, не переписывать, не сокращать. Summary визуально сильнее,
plainExplanation спокойнее, но обе строки читаемы.

### 4.3 Timing

Использовать только backend labels, без `Date`, parsing, timezone conversion или
phase inference:

- `timing.rangeLabel` всегда;
- `timing.peakLabel` только если non-null;
- `timing.stateLabel` всегда.

Сохранить `data-testid="why-horizon-timing"` и добавить стабильные дочерние:

~~~text
why-horizon-timing-range
why-horizon-timing-peak   (only when present)
why-horizon-timing-state
~~~

Допустимые статические подписи слева: `Период`, `Пик`, `Сейчас`. Не менять
backend text справа.

### 4.4 Manifestations

Section:

~~~text
data-testid="why-horizon-manifestations"
heading: Где это вероятнее проявится
~~~

Порядок backend array exact. Для каждого item exact title, optional condition,
body. Не показывать provenance/raw ids.

### 4.5 Strength/risk

После manifestations:

- strength только если non-null, existing `why-horizon-strength`;
- risk только если non-null, existing `why-horizon-risk`;
- mobile one column;
- на достаточной ширине можно 2 columns;
- fast с отсутствующим strength не получает пустую заглушку.

### 4.6 Actions before spheres

`HorizonActions` идёт до sphere links. Он сохраняет backend order и exact copy.
В `components/today/horizon-actions.tsx`:

- добавить `data-testid="why-horizon-validity"` на heading/validUntil block;
- сохранить existing `why-horizon-actions`, `why-horizon-avoid`;
- mobile one column; desktop `sm` может показывать do/avoid рядом;
- backend `actions.heading` и `validUntilLabel` exact;
- do и avoid не сортировать, не объединять, не выводить provenance;
- static headings остаются `Что сделать` / `Чего лучше не делать`.

### 4.7 Sphere links after actions

Перед chips visible heading:

~~~text
Открыть в навигаторе по 12 сферам
~~~

Container:

~~~text
data-testid="why-horizon-spheres"
~~~

Каждый matched chip:

~~~text
data-testid="why-horizon-sphere"
data-sphere-key="<row.key>"
visible text = exact concreteAdvice row.label
aria-label="Открыть сферу «<label>» в навигаторе"
~~~

Правила:

- порядок `horizon.likelySpheres` exact;
- отображать только keys, для которых реально существует concreteAdvice row;
- не создавать fallback label/button для отсутствующей row;
- callback получает exact row.key;
- button native/keyboard-focusable, visible focus ring;
- не менять verdict выбранной sphere.

### 4.8 Technical disclosure last

`HorizonTechniqueDisclosure` всегда последняя часть card.

Внутри закрытого main card не должно быть слов/сырых tokens:

~~~text
Профекция
Фирдар
транзит
орб
аппликация
return
Transit_
Natal_
activationIds
natalFactIds
profileFactIds
~~~

Кнопка `Как это рассчитано` допустима и закрыта по умолчанию.

## 5. Accessible technical disclosure

Файл: `components/today/horizon-technique-disclosure.tsx`.

Не менять backend explanation order/copy.

Требования:

- button получает стабильный unique `id`;
- button `aria-expanded` и `aria-controls` exact;
- opened content `role="region"`;
- region `aria-labelledby` указывает на exact button id;
- `data-testid` existing сохраняются;
- wrapper/toggle/content получают `data-horizon` из нового typed prop
  `long|medium|fast` либо эквивалентного generated horizon type;
- technical item показывает backend label, `whatItIs`, `whyItMattersNow`;
- разрешены статические подзаголовки `Что это` и `Почему важно сейчас`;
- optional technique timing отображает backend range/peak/state exact;
- закрытый content отсутствует из DOM, а не просто скрыт CSS;
- technical disclosure остаётся последним элементом card.

Не добавлять `aria-label` с raw technique. Accessible name региона — видимая
кнопка `Как это рассчитано`.

## 6. Exact 12-sphere navigation behavior

Файлы:

~~~text
components/today/today-screen.tsx
components/today/concrete-day-advice.tsx
~~~

### 6.1 Target existence guard

`selectPersonalStorySphere(key)` сначала проверяет, что exact key существует в
`payload.concreteAdvice.rows`. Если row отсутствует — return, без selection,
scroll, focus или fabricated UI.

### 6.2 Scroll/focus exact row

Текущий код scroll-ит весь navigator container. Заменить на exact matching row:

~~~text
matching [data-testid="concrete-day-advice-row"][data-sphere-key="..."]
  -> scrollIntoView({ behavior: "smooth", block: "center" })
  -> focus({ preventScroll: true })
~~~

Не scroll-ить общий section вместо target row. Selected state уже раскрывает
details panel; сохранить этот controlled flow.

После click:

- matching row `data-selected="true"`;
- matching row `aria-expanded="true"`;
- details `data-sphere-key` exact;
- row `data-status` не меняется;
- row получает focus;
- click уже выбранной sphere снова scroll/focus-ит её, не закрывает.

### 6.3 Visible semantic sphere status

12 spheres остаются быстрым навигатором, все supplied rows видимы в backend
order. Цвет не является единственным смыслом.

Обновить deterministic presentation copy:

~~~text
good:
  compact = Поддерживает
  details = Поддерживающий сигнал

neutral:
  compact = Ровный фон
  details = Нейтральный сигнал

caution:
  compact = Требует внимания
  details = Напряжённый сигнал · требует внимания

avoid:
  compact = Лучше отложить
  details = Сильное напряжение · лучше отложить
~~~

`data-status` остаётся exact `good|neutral|caution|avoid`; не схлопывать enum.
Mapping только по verdict enum, не по LLM text. При неизвестном значении
existing neutral fallback сохраняется.

Для длинного compact text разрешён перенос; на 390px кнопки не перекрываются и
не выходят за viewport. При необходимости увеличить min-height умеренно.

## 7. Backend intro presentation

Файл: `components/today/why-expanded.tsx`.

В `BackendHorizonsContent`:

- semantic `<header>` либо equivalent;
- `data-testid="why-horizons-intro"`;
- exact backend eyebrow/headline/body;
- спокойная визуальная рамка, отделяющая общий сюжет от трёх cards;
- никаких frontend-authored персональных утверждений;
- items render exact backend order, no sort/filter/reselection.

W1 mode resolution, unavailable state и legacy branch не менять.

## 8. Visual constraints

- основной viewport: 390px;
- no horizontal overflow at 390px;
- long Russian strings wrap (`min-w-0`, sensible `break-words` where needed);
- tone badge does not force title outside card;
- touch targets >= 44px for interactive controls/chips;
- light/dark semantic contrast;
- desktop does not stretch prose into unreadable ultra-wide rows;
- card hierarchy remains calm: no three equally loud nested backgrounds;
- technical region may be denser than human card but stays readable;
- no global CSS changes unless absolutely required; prefer local Tailwind.

Не обновлять bitmap/screenshots/assets в этой wave. W3 сделает real preview and
screenshots on 3003.

## 9. Required tests

### 9.1 `TodayScreen.v2-downstream.test.tsx`

Обновить/добавить tests, которые доказывают:

1. tone visible labels exact:
   - 2 x `Смешанный сигнал`;
   - 1 x `Требует внимания`;
   - old horizon labels отсутствуют.
2. card indexes exact `01,02,03` in long/medium/fast order.
3. DOM order for one full card:
   - meaning before timing;
   - timing before manifestations;
   - manifestations before strength/risk;
   - strength/risk before actions;
   - actions/avoid before spheres;
   - spheres before technical toggle.
   Использовать `compareDocumentPosition`, не CSS selectors/classes.
4. backend timing child selectors contain exact backend text; no recalculation.
5. manifestations/actions/strength/risk preserve existing assertions and order.
6. closed `why-horizons` human text не содержит banned technical vocabulary;
   после открытия first technical region содержит Profекция/Фирдар and exact
   backend timing.
7. each technical toggle:
   - unique id;
   - aria-controls points to opened region id;
   - region role=region;
   - region aria-labelledby equals toggle id;
   - data-horizon exact.
8. sphere chip has exact `data-sphere-key`, aria-label, native button.
9. full TodayScreen click on `Работа`:
   - target row status captured before click and unchanged after;
   - selected/aria-expanded true;
   - details key work;
   - exact row scrollIntoView called with smooth/center;
   - exact row focus called with preventScroll;
   - clicking same chip again repeats scroll/focus without deselection.
10. horizon likely sphere with no concreteAdvice row produces no chip/fallback.
11. backend horizons do not show the constant legacy sentence about three
    random facts.

Spies must be installed before click/render as appropriate and restored between
tests. Не добавлять unsafe casts/suppressions/new non-null assertions.

### 9.2 `ConcreteDayAdvice.keyboard.test.tsx`

Добавить полный verdict coverage (`good/neutral/caution/avoid`) и exact visible
compact copy. При selected rerender проверить exact details copy, status
unchanged, aria-expanded/controls. Все 12 native buttons и row order остаются.

Обновить GRACE header/module contract этого test file до полного repo format,
так как файл существенно меняется и сейчас имеет только короткий header.

## 10. Allowlist

~~~text
components/today/why-expanded.tsx
components/today/why-time-horizon-card.tsx
components/today/horizon-actions.tsx
components/today/horizon-technique-disclosure.tsx
components/today/concrete-day-advice.tsx
components/today/today-screen.tsx
__tests__/components/TodayScreen.v2-downstream.test.tsx
__tests__/components/ConcreteDayAdvice.keyboard.test.tsx
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/91_STAGE_B4_W2_FINAL_HUMAN_FIRST_UX_TZ.md
~~~

Этот документ создан архитектором; кодер его не редактирует. Implementation
diff — только первые восемь paths.

Запрещены любые другие tracked paths, особенно:

~~~text
lib/contracts/**
lib/adapters/**
lib/presentation/**
packages/contracts/**
apps/api/**
app/**
e2e/**
package.json / lockfile / next config
fixtures / screenshots / artifacts
services / nginx / env
~~~

## 11. GRACE

Для всех шести production TSX files актуализировать existing module contracts,
maps, semantic blocks, invariants and function contracts. Реальные invariants:

- backend copy/order exact;
- enum-only tone/verdict mapping;
- no frontend astrology/date/advice inference;
- technical vocabulary only in opened disclosure;
- matched-row-only sphere navigation;
- target row scroll/focus; no fabricated missing target;
- public testids/ARIA stable.

Новых logs/events не добавлять: emitted_logs `none`.

## 12. Gates

Из корня, после implementation:

~~~bash
npx vitest run __tests__/components/TodayScreen.v2-downstream.test.tsx __tests__/components/ConcreteDayAdvice.keyboard.test.tsx
pnpm typecheck
npx vitest run
pnpm guardrails:prod
NEXT_DIST_DIR=.next-b4-w2-candidate pnpm build
git diff --check
~~~

После успешного build удалить только generated `.next-b4-w2-candidate` и
доказать, что он не попал в status. Не трогать `.next-prod` и `.next`.

Повторить GRACE gate:

~~~bash
bash scripts/grace/check-markers.sh
~~~

Ожидаемый unrelated baseline failure может остаться только:

~~~text
scripts/grace_front_lint.py:588
SyntaxError: from __future__ imports must occur at the beginning of the file
~~~

Не исправлять вне allowlist.

Финально:

~~~bash
git diff --name-only
git diff --cached --name-only
git status --short --branch
git diff -- packages/contracts/_generated.ts packages/contracts/_generated.zod.ts packages/contracts/openapi.json
git diff --check
~~~

## 13. Запрещено

- frontend selection/ranking/inference of astrology;
- parsing dates/eyebrows/text;
- adding generic personal narrative;
- changing W1 version routing/unavailable/legacy behavior;
- contract/backend/mock/fixture edits;
- screenshots/assets;
- services/3003;
- subagents;
- git add/commit/push;
- B4.W3 or main deploy.

## 14. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_B4_W2
branch: <branch>
base_sha: c0c86c540a1d8f77b282ff21705758c8594d5a6e
changed_paths: <exact 8 implementation/test paths>
human_dom_order: MEANING_TIMING_MANIFESTATIONS_PATTERNS_ACTIONS_SPHERES_TECH
horizon_tones: EXACT_4_VISIBLE_MAPPING
sphere_statuses: EXACT_4_VISIBLE_MAPPING
backend_copy_order: PRESERVED
frontend_inference: NONE
technical_closed_leakage: NONE
technical_region_a11y: PASS
sphere_target_guard: PASS
sphere_scroll_focus: EXACT_ROW
sphere_verdict_unchanged: PASS
missing_sphere_row: NO_FABRICATION
mobile_390_overflow: NONE_BY_STRUCTURE
targeted_vitest: <result>
full_vitest: <result>
typecheck: <result>
prod_guard: <result>
isolated_build: <result>
isolated_dist_removed: YES
grace_gate: UNRELATED_BASELINE_ERROR_UNCHANGED
git_diff_check: <result>
generated_diff: EMPTY
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться и ждать архитектурного ревью.
