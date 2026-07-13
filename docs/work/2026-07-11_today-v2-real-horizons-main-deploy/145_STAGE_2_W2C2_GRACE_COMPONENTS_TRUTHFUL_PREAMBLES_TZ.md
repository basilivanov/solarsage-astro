# Stage 2.W2C-2 — truthful GRACE preambles for legacy component slice

Дата: `2026-07-13`
Branch: `preview/solarsage-v2-human-first-navigator-ux`
Parent: `141_STAGE_2_W2C_GRACE_ACTIVE_SLICE_SUBWAVE_MASTER_TZ.md`
Predecessor: W2C-1 must be accepted, committed and pushed first.

Статус: **PREPARED NEXT WAVE — NOT AUTHORIZED UNTIL ARCHITECT SENDS THIS PATH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Цель волны

Закрыть ровно 11 оставшихся GRACE marker violations в
`components/grace/*`, заменив generic/ложные module preambles на правдивые
контракты и карты модулей.

Это comment-only migration. Нельзя менять runtime-код, JSX, строки,
селекторы, типы, импорты, exports, formatting тела или поведение.

После принятого W2C-1 исходный остаток должен быть:

```text
32 violations
27 failing paths
20 green paths
47 checked paths
```

После W2C-2 ожидается ровно:

```text
21 violations
16 failing paths
31 green paths
47 checked paths
```

Оставшиеся failing prefixes после этой волны:

```text
lib/api
lib/grace
```

## 2. Exact edit allowlist

Редактировать только эти 11 файлов:

```text
components/grace/CalendarGrid.tsx
components/grace/CalendarMonth.tsx
components/grace/DayNavigation.tsx
components/grace/ErrorBoundary.tsx
components/grace/LoadingSpinner.tsx
components/grace/LockedDay.tsx
components/grace/Reading.tsx
components/grace/ReadingCard.tsx
components/grace/TodayScreen.tsx
components/grace/TopFlags.tsx
components/grace/WeekStrip.tsx
```

Не редактировать app pages, `components/today/*`, contracts, tests, configs,
linters, manifests, scripts или docs. W2C-3/W2C-4 не начинать.

No git add/commit/push в implementation-wave. Запрещены subagents/delegation
в любом виде. После callback остановиться.

## 3. Важная архитектурная оговорка

Это legacy component slice, но текущая волна не является dead-code cleanup.

Текущий call graph:

- `ErrorBoundary` используется product route
  `app/(grace)/day/[date]/page.tsx` и имеет direct unit test;
- `ReadingCard` имеет direct unit test;
- `CalendarGrid` вызывает `CalendarMonth`;
- legacy `TodayScreen` вызывает `DayNavigation`, `LockedDay`, `WeekStrip`,
  `TopFlags`, `Reading`;
- у остальных компонентов сейчас нет внешнего product importer, найденного
  репозиторным поиском.

Отсутствие importer не разрешает удалять, переносить, переименовывать или
«осовременивать» файлы. Нужно только правдиво документировать фактический
экспорт и поведение.

Не путать:

```text
components/grace/TodayScreen.tsx
components/today/today-screen.tsx
```

и:

```text
components/grace/WeekStrip.tsx
components/today/week-strip.tsx
```

Тесты нового V2 Today UI относятся к `components/today/*`, а не к legacy
компонентам этой волны.

## 4. Общий формат каждой preamble

В каждом allowlisted файле заменить весь generic header/module-contract/
legacy mini-header перед первым runtime statement на одну canonical preamble:

```ts
// ############################################################################
// AI_HEADER: <NAME> — <one-line truthful description>
// ROLE: <truthful callers and responsibility>
// ############################################################################

// START_MODULE_CONTRACT: <ID>
// purpose: ...
// owns:
//   - exact/path.tsx
// inputs: ...
// outputs: ...
// dependencies: ...
// side_effects: ...
// emitted_logs: none.
// invariants:
//   - ...
// failure_policy: ...
// END_MODULE_CONTRACT: <ID>

// START_MODULE_MAP: <same ID>
// public_entrypoints:
//   - ExportedComponent
// semantic_blocks:
//   - BLOCK_NAME: truthful conceptual ownership.
// owned_tests:
//   - exact test path, or none direct.
// END_MODULE_MAP: <same ID>
```

Requirements:

- AI_HEADER находится в первых 30 строках;
- contract/map ID совпадают внутри файла и уникальны между файлами;
- `owns` содержит только точный путь файла;
- никаких `n/a`, `Function args`, `Return values`, `local modules`,
  `log and raise`, `Tests for ... behavior` в product component contracts;
- `emitted_logs: none.` — компоненты не вызывают frontend logger;
- conceptual semantic blocks не требуют добавления `START_BLOCK` в body;
- существующее тело начинается ровно с прежней первой directive/import/
  declaration и после preamble остаётся побайтно эквивалентным.

## 5. Exact truthful contract content

Формулировки можно грамматически выровнять, но нельзя менять их фактический
смысл или придумывать поведение.

### 5.1. CalendarGrid.tsx

```text
ID: M-GRACE-COMPONENT-CALENDAR-GRID
AI_HEADER name: GRACE_CALENDAR_GRID
ROLE: Presentational wrapper that receives one CalendarPayload and delegates
      month rendering to CalendarMonth.
purpose: Render the calendar-grid structural container for one calendar payload.
inputs: payload — canonical CalendarPayload for the displayed month.
outputs: calendar-grid div containing one CalendarMonth.
dependencies: CalendarMonth; packages/contracts CalendarPayload.
side_effects: none.
invariants:
  - data-testid="calendar-grid" remains stable.
  - The payload is passed to CalendarMonth unchanged.
failure_policy: Does not catch child/render errors; they propagate to caller.
public_entrypoints: CalendarGrid
semantic_blocks:
  - GRID_WRAPPER: stable container and CalendarMonth delegation.
owned_tests: none direct.
```

### 5.2. CalendarMonth.tsx

```text
ID: M-GRACE-COMPONENT-CALENDAR-MONTH
AI_HEADER name: GRACE_CALENDAR_MONTH
ROLE: Presentational month grid that converts CalendarPayload days into dated
      Next.js links with status and lock semantics.
purpose: Render month title, weekday headings and day navigation cells.
inputs: month — CalendarPayload containing month id and day entries.
outputs: localized Russian month heading and role=grid list of /day/:date links.
dependencies: next/link; lib/utils cn; packages/contracts CalendarPayload.
side_effects: none directly; link activation delegates navigation to Next.js.
invariants:
  - data-testid="calendar-day-${date}", data-date and data-status remain stable.
  - locked days retain the lock marker and remain linked to their day route.
  - current-month/today/access styling decisions remain unchanged.
failure_policy: Assumes valid YYYY-MM month data; render errors propagate.
public_entrypoints: CalendarMonth
semantic_blocks:
  - MONTH_HEADING: localized month/year label.
  - WEEKDAY_HEADER: Russian weekday abbreviations.
  - DAY_GRID: linked day cells with current/locked/status state.
owned_tests: none direct.
```

### 5.3. DayNavigation.tsx

```text
ID: M-GRACE-COMPONENT-DAY-NAVIGATION
AI_HEADER name: GRACE_DAY_NAVIGATION
ROLE: Date header that derives previous/next dates and exposes day/calendar links.
purpose: Render navigation around a current ISO date.
inputs: currentDate — ISO-like date string consumed by Date.
outputs: header with previous-day, calendar and next-day links plus localized label.
dependencies: next/link; JavaScript Date/Intl locale formatting.
side_effects: none directly; link activation delegates navigation to Next.js.
invariants:
  - day-nav-prev/day-nav-calendar/day-nav-next test IDs and aria-labels remain stable.
  - Previous and next routes remain one calendar day from currentDate.
failure_policy: Does not validate malformed dates; resulting render behavior propagates.
public_entrypoints: DayNavigation
semantic_blocks:
  - DATE_DERIVATION: previous/next ISO date and localized label.
  - NAVIGATION_HEADER: stable accessible links.
owned_tests: none direct.
```

### 5.4. ErrorBoundary.tsx

```text
ID: M-GRACE-COMPONENT-ERROR-BOUNDARY
AI_HEADER name: GRACE_ERROR_BOUNDARY_VIEW
ROLE: Client error-state view used by the day route; it displays an already-caught
      Error and optionally navigates to /debug in explicit dev mode.
purpose: Present a stable role=alert fallback from error/title/message props.
inputs: error; optional title; optional message.
outputs: error-boundary alert with resolved title/message and optional debug button.
dependencies: next/navigation useRouter; NEXT_PUBLIC_DEV_MODE.
side_effects: router.push('/debug') only when the rendered dev button is clicked.
invariants:
  - This is a presentation component, not a React class error catcher.
  - data-testid="error-boundary", data-testid="error-message" and role=alert remain stable.
  - Message priority remains explicit message -> error.message -> generic fallback.
failure_policy: Displays provided/fallback error text; navigation errors are not caught.
public_entrypoints: ErrorBoundary
semantic_blocks:
  - ERROR_COPY_RESOLUTION: title/message/dev-mode derivation.
  - ERROR_ALERT: accessible visual fallback.
  - DEV_DEBUG_ACTION: conditional /debug navigation.
owned_tests:
  - __tests__/components/ErrorBoundary.test.tsx
  - __tests__/app/day-page.test.tsx (route integration/mocked boundary)
```

### 5.5. LoadingSpinner.tsx

```text
ID: M-GRACE-COMPONENT-LOADING-SPINNER
AI_HEADER name: GRACE_LOADING_SPINNER
ROLE: Stateless accessible loading indicator.
purpose: Render the shared visual loading state.
inputs: none.
outputs: role=status loading-spinner with Russian loading text.
dependencies: React JSX only.
side_effects: none.
invariants:
  - data-testid="loading-spinner", role=status and aria-label="Загрузка" remain stable.
failure_policy: No local failure handling; render errors propagate.
public_entrypoints: LoadingSpinner
semantic_blocks:
  - LOADING_STATUS: spinner graphic and accessible status text.
owned_tests: none direct.
```

### 5.6. LockedDay.tsx

```text
ID: M-GRACE-COMPONENT-LOCKED-DAY
AI_HEADER name: GRACE_LOCKED_DAY
ROLE: Client locked-access view with subscription and referral navigation actions.
purpose: Explain a locked day and expose two access recovery CTAs.
inputs: none.
outputs: locked-day view with subscribe and invite buttons.
dependencies: next/navigation useRouter.
side_effects: router.push('/paywall') or router.push('/referral') on CTA click.
invariants:
  - locked-day, cta-subscribe and cta-invite test IDs remain stable.
  - Subscribe and invite routes remain /paywall and /referral.
  - Referral copy continues to promise the existing 14-day behavior.
failure_policy: Navigation failures are not caught locally.
public_entrypoints: LockedDay
semantic_blocks:
  - LOCK_EXPLANATION: locked state icon and user-facing copy.
  - ACCESS_ACTIONS: subscription/referral buttons.
  - REFERRAL_NOTE: existing 14-day explanatory copy.
owned_tests: none direct.
```

### 5.7. Reading.tsx

```text
ID: M-GRACE-COMPONENT-READING
AI_HEADER name: GRACE_READING
ROLE: Stateless renderer for narrative day-reading paragraphs.
purpose: Render non-empty reading paragraphs with first/last paragraph styling.
inputs: paragraphs — ordered array of strings.
outputs: null for an empty array, otherwise reading section and paragraph list.
dependencies: React JSX only.
side_effects: none.
invariants:
  - Empty paragraphs produce no DOM.
  - aria-label="Разбор дня" and data-testid="reading" remain stable.
  - Input order and first/last styling decisions remain unchanged.
failure_policy: Does not validate paragraph content; render errors propagate.
public_entrypoints: Reading
semantic_blocks:
  - EMPTY_GUARD: suppress empty reading.
  - SECTION_HEADING: visible separator/title.
  - PARAGRAPH_LIST: ordered styled narrative.
owned_tests: none direct.
```

### 5.8. ReadingCard.tsx

```text
ID: M-GRACE-COMPONENT-READING-CARD
AI_HEADER name: GRACE_READING_CARD
ROLE: Interactive saved-reading summary button that normalizes status presentation.
purpose: Render one ReadingEntry preview and invoke the caller action on activation.
inputs: entry — ReadingEntry; onClick — caller callback.
outputs: reading-card button with date, status label, headline and preview.
dependencies: React; lib/contracts/readings ReadingEntry; lib/utils cn.
side_effects: invokes the supplied onClick callback on button activation.
invariants:
  - data-testid="reading-card" and button semantics remain stable.
  - Missing/unknown dayStatus falls back to calm styling and label.
  - supportive/tense/calm labels and styles remain unchanged.
failure_policy: Does not catch callback or render errors; they propagate.
public_entrypoints: ReadingCard
semantic_blocks:
  - STATUS_PRESENTATION: status style/label lookup with calm fallback.
  - READING_BUTTON: interactive entry summary.
owned_tests:
  - __tests__/components/ReadingCard.test.tsx
```

### 5.9. TodayScreen.tsx

```text
ID: M-GRACE-COMPONENT-TODAY-SCREEN
AI_HEADER name: GRACE_LEGACY_TODAY_SCREEN
ROLE: Legacy TodayPayload composition surface for the components/grace component family;
      distinct from the active components/today/today-screen.tsx V2 surface.
purpose: Compose locked or unlocked legacy day content from canonical TodayPayload.
inputs: payload — TodayPayload containing access, date, headline, week, flags,
        reading and why-this-happens sections.
outputs: today-screen root; locked branch or full legacy day presentation.
dependencies: WeekStrip; TopFlags; Reading; DayNavigation; LockedDay;
              packages/contracts TodayPayload.
side_effects: none directly; child navigation components may navigate on interaction.
invariants:
  - data-testid="today-screen" exists in both access branches.
  - locked access renders navigation plus LockedDay and suppresses full content.
  - data-testid="today-headline" and child ordering remain stable when unlocked.
  - Paragraph and bullet why blocks retain order; unknown kinds render nothing.
failure_policy: Does not catch malformed payload or child render errors; they propagate.
public_entrypoints: TodayScreen
semantic_blocks:
  - LOCKED_BRANCH: navigation and access lock view.
  - DAY_HEADER: date navigation and headline/subtitle.
  - DAY_SUMMARY: week, flags and reading composition.
  - WHY_SECTIONS: ordered paragraph/bullet explanation cards.
owned_tests: none direct; active V2 TodayScreen tests target components/today instead.
```

### 5.10. TopFlags.tsx

```text
ID: M-GRACE-COMPONENT-TOP-FLAGS
AI_HEADER name: GRACE_TOP_FLAGS
ROLE: Stateless renderer for ordered TopFlag summaries and optional hint detail.
purpose: Render non-empty top flags with icon, title, summary and hint copy.
inputs: flags — ordered TopFlag array.
outputs: null for empty flags, otherwise top-flags section.
dependencies: packages/contracts TopFlag.
side_effects: none.
invariants:
  - Empty flags produce no DOM.
  - data-testid="top-flags" remains stable.
  - Input order, data-icon and optional howItFeels/whyToday rendering remain unchanged.
failure_policy: Does not validate flag content; render errors propagate.
public_entrypoints: TopFlags
semantic_blocks:
  - EMPTY_GUARD: suppress empty flag list.
  - FLAG_LIST: ordered summary rows.
  - FLAG_HINT: optional feelings/timing detail.
owned_tests: none direct.
```

### 5.11. WeekStrip.tsx

```text
ID: M-GRACE-COMPONENT-WEEK-STRIP
AI_HEADER name: GRACE_LEGACY_WEEK_STRIP
ROLE: Legacy seven-day link strip for WeekStripDay contract data; distinct from
      components/today/week-strip.tsx.
purpose: Render dated day links with current-date and day-status presentation.
inputs: days — ordered WeekStripDay array; currentDate — selected ISO date.
outputs: week-strip section containing /day/:date links.
dependencies: next/link; lib/utils cn; packages/contracts WeekStripDay; Date.
side_effects: none directly; link activation delegates navigation to Next.js.
invariants:
  - aria-label="Неделя" and data-testid="week-strip" remain stable.
  - data-date and data-status remain on every link.
  - current-date styling and supportive/tense/neutral symbols remain unchanged.
failure_policy: Assumes Date can parse each day.date; render errors propagate.
public_entrypoints: WeekStrip
semantic_blocks:
  - WEEK_LIST: ordered day links.
  - DAY_PRESENTATION: active state, localized weekday/day and status symbol.
owned_tests: none direct; existing WeekStrip unit test targets components/today.
```

## 6. Mandatory preflight

До edits:

1. полностью прочитать 141 и 145;
2. доказать, что W2C-1 commit уже local/tracking/remote equal и является HEAD;
3. проверить ожидаемый marker baseline `32/27/20/47`;
4. проверить, что exact 11 allowlisted paths дают ровно 11 map violations;
5. сохранить все 11 файлов в `/tmp/stage2-w2c2-before/` с относительными путями;
6. сохранить SHA-256 каждого файла;
7. проверить чистый tracked worktree кроме architect docs и frozen untracked paths;
8. проверить пустой index;
9. проверить canonical services unchanged и listeners `3003/8001/18092` absent.

Stop on mismatch. Never reset/rebase/force/stash.

## 7. Mechanical equivalence proof

После edits для каждого файла доказать:

- diff меняет только ведущие комментарии и соседние blank lines;
- первая runtime directive/import/declaration и всё после неё побайтно совпадают
  с копией в `/tmp/stage2-w2c2-before/`;
- comment-stripped content before/after совпадает;
- import/export count и exact exported component name не изменились;
- число существовавших START/END function/block markers в body не изменилось;
- никакой formatter не запускался по allowlist.

Любая executable hunk line — STOP и callback с доказательством, без auto-fix.

## 8. Required gates

### 8.1. Exact GRACE checks

```bash
python3 scripts/test_grace_front_lint.py
python3 scripts/grace_front_lint.py \
  components/grace/CalendarGrid.tsx \
  components/grace/CalendarMonth.tsx \
  components/grace/DayNavigation.tsx \
  components/grace/ErrorBoundary.tsx \
  components/grace/LoadingSpinner.tsx \
  components/grace/LockedDay.tsx \
  components/grace/Reading.tsx \
  components/grace/ReadingCard.tsx \
  components/grace/TodayScreen.tsx \
  components/grace/TopFlags.tsx \
  components/grace/WeekStrip.tsx
bash scripts/grace/check-negative.sh
```

Expected:

```text
self-tests: 11 PASS
authorized files: 11 clean
negative harness: clean baseline + 6 PASS / 0 FAIL
exact marker codes and ESLint rule IDs preserved
```

### 8.2. Frontend static checks

```bash
pnpm lint
pnpm typecheck
```

Expected: ESLint zero errors/warnings; typecheck PASS.

### 8.3. Direct component regressions

```bash
npx vitest run \
  __tests__/components/ErrorBoundary.test.tsx \
  __tests__/components/ReadingCard.test.tsx \
  __tests__/app/day-page.test.tsx
```

All selected files/tests must pass. Record exact totals; do not invent expected
test count before the run.

### 8.4. Full marker remainder

Run full marker gate, capture output and prove exactly:

```text
violations=21
failing_paths=16
green_paths=31
checked_paths=47
components/grace failing paths=0
remaining prefixes=lib/api_AND_lib/grace_ONLY
```

### 8.5. Aggregate diagnostic

Run `pnpm guardrails:frontend` diagnostically. It may be non-zero only because
of the same exact W2C-3/W2C-4 marker remainder `21/16/31/47`, after all earlier
sections pass.

Finally run `git diff --check` and exact scope audit.

## 9. Frozen state

Never touch/stage:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Do not operate systemd/nginx/env/database. Keep canonical services unchanged;
ports `3003`, `8001`, `18092` absent.

## 10. Required callback

```text
READY_STAGE_2_W2C2_GRACE_COMPONENTS_REVIEW
tracked_scope: EXACT_11_COMPONENTS
comment_only_equivalence: PASS_11
runtime_suffix_hashes: UNCHANGED_11
module_ids: UNIQUE_AND_PAIRED_11
authorized_paths_grace: PASS_11
grace_linter_self_tests: 11_PASS
negative_harness: 6_PASS_0_FAIL_EXACT_REASONS
eslint: PASS_ZERO
typecheck: PASS
targeted_tests: PASS_<EXACT_FILES_AND_TESTS>
remaining_grace: 21_VIOLATIONS_16_FAILING_31_GREEN_47_CHECKED
remaining_prefixes: LIB_API_AND_LIB_GRACE_ONLY
guardrails_frontend: EXPECTED_MARKER_REMAINDER_ONLY
git_diff_check: PASS
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
```

После callback остановиться. W2C-3 не начинать.
