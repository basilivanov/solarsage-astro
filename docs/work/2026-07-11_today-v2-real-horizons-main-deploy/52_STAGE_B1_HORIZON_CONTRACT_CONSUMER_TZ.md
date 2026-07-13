# Stage B1 Implementation TZ — additive horizon contract and consumer boundary

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Expected HEAD/origin: `f0d8bef19ec4f0806039cf44a173a22bb4f60a1c`
Parents:

- `50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md`
- `51_STAGE_B_AND_MAIN_RELEASE_WAVE_PLAN.md`

Статус: **START_STAGE_B1_HORIZON_CONTRACT / implement B1 only**.

## 0. Режим работы

1. Полностью прочитать этот файл и relevant sections master `50` до edits.
2. Работать только в текущей preview branch.
3. Не запускать субагентов/delegated agents.
4. До architect acceptance запрещены `git add`, commit, push, merge, rebase,
   checkout, switch и reset.
5. Не начинать B2/B3/B4/B5 или release.
6. Не менять `main`, systemd, nginx, production env, ports или running services.
7. Не запускать ручной uvicorn и не использовать API port 8001.
8. Не трогать unrelated paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

9. Generated OpenAPI/TS/Zod редактируются только generator-ом.
10. Production backend population обязана остаться `horizons=None`; B1 —
    contract + consumer, не selection/guidance implementation.
11. Existing dev fixture isolation сохраняется; product runtime не импортирует
    fixture.
12. Если нужен path вне exact allowlist — остановиться и вернуть path + reason.

## 1. Цель волны

После B1:

```text
Pydantic TodayV2HorizonsBlock
  -> additive OpenAPI
  -> generated TypeScript/Zod
  -> frontend prefers backend v2.horizons
  -> contract-valid dev/test payload renders final structural skeleton
  -> legacy selector remains only for horizons null/absent
```

Не должно быть:

- production horizon selection;
- production actions/facts generation;
- new sidecar call;
- cache/content/feature flag bump;
- LLM integration;
- canon files;
- real API preview claim;
- DB migration.

## 2. Preflight

До edits выполнить:

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short
git diff --cached --name-only
pnpm contracts:check
```

Expected:

```text
branch: preview/solarsage-v2-human-first-navigator-ux
HEAD/origin: f0d8bef19ec4f0806039cf44a173a22bb4f60a1c
tracked worktree: clean
index: empty
only known unrelated untracked paths
contracts:check: PASS
```

Baseline evidence:

```text
focused Stage A contracts: 110 passed
contract Vitest: 132 passed
sidecar full: 201 passed
API full: 6 failed, 843 passed, 5 skipped
```

Allowed API failures в B1 только прежние exact six:

```text
test_calendar_status_cache_duplicate_rereads_winning_row
test_semantic_v2_service_no_convergence
test_semantic_v2_service_with_convergence
test_audit_canon_versions_only_contains_strings
test_techniques_list_is_sorted
test_today_payload_v2_block_included_when_flag_enabled
```

Новых failures быть не должно.

## 3. Exact allowlist

Разрешены только:

```text
apps/api/app/schemas/today_horizons.py
apps/api/app/schemas/today.py
apps/api/app/schemas/__init__.py
apps/api/tests/test_today_horizons_contract.py
apps/api/tests/test_contract_registry.py

packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
packages/contracts/index.ts
packages/contracts/runtime.ts
lib/contracts/today.ts

components/today/today-screen.tsx
components/today/why-expanded.tsx
components/today/why-time-horizon-card.tsx
components/today/horizon-actions.tsx
components/today/horizon-technique-disclosure.tsx

e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
__tests__/contracts/generated-runtime.test.ts
__tests__/contracts/today-fixture-roundtrip.test.ts
__tests__/components/TodayScreen.v2-downstream.test.tsx
__tests__/lib/presentation/today-v2.test.ts
e2e/dev-timing-fixture.spec.ts
e2e/mock-visual/day-v2.spec.ts

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/51_STAGE_B_AND_MAIN_RELEASE_WAVE_PLAN.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/52_STAGE_B1_HORIZON_CONTRACT_CONSUMER_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/**
```

Не менять:

```text
apps/api/app/services/**
apps/solarsage/**
grace/canon/**
apps/api/app/core/config.py
apps/api/app/core/logging_events.py
lib/log/events.gen.ts
lib/adapters/today-payload.ts
lib/presentation/today-v2.ts
app/api/dev-fixtures/**
lib/dev-fixtures/**
app/(grace)/day/[date]/page.tsx
package.json
pnpm-lock.yaml
systemd/nginx/env
```

`lib/presentation/today-v2.ts` legacy selector специально не меняется в B1;
consumer branching должен быть виден прямо в `WhyExpanded`.

## 4. New API module

Создать `apps/api/app/schemas/today_horizons.py` с полным GRACE header,
module contract/map, semantic blocks и function contracts для нетривиальных
validators/helpers.

Module owns только public horizon wire models and pure validation helpers. Он
не импортирует services, settings, DB, sidecar или frontend files.

### 4.1 Literal aliases

```py
TodayV2HorizonId = Literal["long", "medium", "fast"]

TodayV2HorizonTone = Literal[
    "supportive",
    "neutral",
    "tense",
    "mixed",
]

TodayV2TimingState = Literal[
    "upcoming",
    "building",
    "active",
    "exact",
    "peaked",
    "fading",
    "background",
]

TodayV2TimingPrecision = Literal["date", "instant"]

TodayV2ClaimKind = Literal[
    "explanation",
    "strength",
    "risk",
    "manifestation",
    "action",
    "avoid",
    "technique_definition",
]

TodayV2GuidanceMode = Literal["deterministic", "llm_refined"]

TodayV2ProductSphereKey = Literal[
    "work",
    "money",
    "documents",
    "relationships",
    "sport",
    "communication",
    "health",
    "decisions",
    "travel",
    "creativity",
    "study",
    "shopping",
]
```

`likely_spheres` intentionally uses the existing 12 product navigator keys,
not the nine technical scoring keys. B2 later owns deterministic mapping from
scoring sphere to product sphere.

### 4.2 Common string constraints

Use explicit `Field` constraints so generated OpenAPI/Zod receives useful
limits:

```text
IDs: min_length=1, max_length=160
human labels/headings: min_length=1, max_length=160
titles: min_length=1, max_length=240
body/explanation/action text: min_length=1, max_length=1200
timezone: min_length=1, max_length=80
```

Opaque natal/profile fact IDs:

```regex
^[a-z0-9][a-z0-9._:-]{1,127}$
```

No spaces, `@`, `/`, raw names, coordinates or free text in fact IDs.

### 4.3 Provenance

```py
class TodayV2Provenance(CamelModel):
    activation_ids: list[str] = Field(default_factory=list)
    natal_fact_ids: list[OpaqueFactId] = Field(default_factory=list)
    profile_fact_ids: list[OpaqueFactId] = Field(default_factory=list)
    sphere_keys: list[TodayV2ProductSphereKey] = Field(default_factory=list)
```

Validator:

- at least one source list non-empty;
- every list unique, preserving input order;
- empty strings rejected by field constraints;
- no mutation/reordering.

### 4.4 Grounded item

```py
class TodayV2GroundedItem(CamelModel):
    id: str
    kind: TodayV2ClaimKind
    text: str
    conditional: bool = False
    provenance: TodayV2Provenance
```

B1 structural contract does not inspect Russian words. B2 claim validator will
enforce conditional phrasing and forbidden claims.

### 4.5 Timing model

```py
class TodayV2HorizonTiming(CamelModel):
    active_from: str
    exact_at: str | None = None
    active_until: str
    precision: TodayV2TimingPrecision
    state: TodayV2TimingState
    range_label: str
    peak_label: str | None = None
    state_label: str
    timezone: str
```

Pure validator rules:

#### Date precision

- machine values match exact `YYYY-MM-DD`;
- parse with `date.fromisoformat`;
- instant strings are rejected.

#### Instant precision

- RFC3339/ISO datetime with explicit `Z` or numeric offset;
- naive datetime rejected;
- normalize only for comparison, preserve original wire string.

#### Ordering/state

- `active_from <= active_until`;
- exact, when present, lies inside inclusive range;
- `state="exact"` requires exact_at;
- exact_at requires non-empty peak_label;
- null exact_at requires `peak_label=None`;
- range_label/state_label/timezone non-empty after `.strip()` check;
- validator returns original strings, not reformatted values.

### 4.6 Technique explanation

```py
class TodayV2TechniqueExplanation(CamelModel):
    technique: str
    label: str
    what_it_is: str
    why_it_matters_now: str
    timing: TodayV2HorizonTiming | None = None
    activation_ids: list[str]
```

Rules:

- activation_ids min 1 and unique;
- all human strings non-empty;
- no dictionary-only item: `why_it_matters_now` required.

### 4.7 Manifestation

```py
class TodayV2Manifestation(CamelModel):
    id: str
    title: str
    body: str
    condition: str | None = None
    sphere_keys: list[TodayV2ProductSphereKey]
    provenance: TodayV2Provenance
```

Rules:

- sphere_keys min 1, max 3, unique;
- condition if present is non-empty;
- semantic requirement for unknown context is enforced in B2 claim validator,
  not guessed structurally in B1.

### 4.8 Actions

```py
class TodayV2HorizonActions(CamelModel):
    heading: str
    valid_until: str
    valid_until_label: str
    do: list[TodayV2GroundedItem]
    avoid: list[TodayV2GroundedItem]
```

Generic rules:

- both lists non-empty;
- every `do.kind == "action"`;
- every `avoid.kind == "avoid"`;
- item IDs unique within block;
- normalized action text unique within block.

Normalize only for duplicate detection:

```text
strip -> casefold -> collapse whitespace -> strip terminal .,!?:;—-
```

Wire text stays unchanged.

### 4.9 Horizon

```py
class TodayV2Horizon(CamelModel):
    id: str
    horizon: TodayV2HorizonId
    tone: TodayV2HorizonTone
    eyebrow: str
    title: str
    summary: str
    plain_explanation: str
    timing: TodayV2HorizonTiming
    likely_spheres: list[TodayV2ProductSphereKey]
    manifestations: list[TodayV2Manifestation]
    strength: TodayV2GroundedItem | None = None
    risk: TodayV2GroundedItem | None = None
    actions: TodayV2HorizonActions
    technique_explanations: list[TodayV2TechniqueExplanation]
    activation_ids: list[str]
```

Rules:

- activation_ids min 1, unique;
- likely_spheres min 1, max 3, unique;
- manifestations min 1, max 3;
- technique_explanations min 1;
- strength, if present, has kind `strength`;
- risk, if present, has kind `risk`;
- manifestation sphere keys and nested provenance sphere keys are subset of
  likely_spheres;
- all nested provenance activation IDs are subset of horizon activation_ids;
- `actions.valid_until == timing.active_until`;
- technique explanation timing, if present, equals horizon timing exactly;
- medium and fast require non-null exact_at/peak_label;
- action counts:

```text
long:   do 1..2, avoid 1..2
medium: do 2..3, avoid 1..3
fast:   do exactly 1, avoid 1..2
```

### 4.10 Intro and block

```py
class TodayV2HorizonIntro(CamelModel):
    eyebrow: str
    headline: str
    body: str
    theme_key: str
    activation_ids: list[str]


class TodayV2HorizonsBlock(CamelModel):
    schema_version: Literal["today-horizons.v1"]
    guidance_mode: TodayV2GuidanceMode
    intro: TodayV2HorizonIntro
    items: list[TodayV2Horizon] = Field(min_length=3, max_length=3)
    warnings: list[str] = Field(default_factory=list)
```

Rules:

- item horizons exact order `long`, `medium`, `fast`;
- horizon IDs unique;
- intro activation_ids min 1, unique;
- intro IDs subset union item activation_ids;
- all grounded item IDs and manifestation IDs globally unique across block;
- normalized action text globally unique across all horizons;
- warnings unique and non-empty when present.

## 5. Integrate into TodayV2Block

In `apps/api/app/schemas/today.py`:

```py
from .today_horizons import TodayV2HorizonsBlock, validate_horizons_against_evidence

class TodayV2Block(CamelModel):
    ...
    horizons: TodayV2HorizonsBlock | None = None
```

Add an `after` validator that does nothing for `horizons is None` and otherwise
validates against `activation_evidence`.

### 5.1 Reference integrity

- every horizon activation ID exists in `activation_evidence`;
- every nested provenance/technique activation ID exists;
- intro IDs exist;
- every technique explanation activation ID is inside its horizon;
- for every explanation at least one referenced evidence item has exact matching
  `technique`.

### 5.2 Timing aggregate policy

For each horizon:

1. collect referenced evidence;
2. ignore evidence with all timing fields null, but it cannot be the only timed
   support;
3. all non-null timing strings must match horizon precision;
4. at least one active_from and one active_until exist;
5. expected horizon active_from is minimum referenced non-null active_from;
6. expected active_until is maximum referenced non-null active_until;
7. horizon values must equal these aggregate boundaries;
8. horizon exact_at, when present, must equal one referenced non-null exact_at.

This is the documented B1 union-window policy. Do not invent intersection or
server-clock behavior.

Validation errors contain structural path/ID/reason, never raw personal text.

### 5.3 Backward compatibility

- Existing constructors with no `horizons` remain valid.
- `horizons=None` remains valid.
- No existing defaults/aliases/versions change.
- `TodayPayload` meta identity does not bump in B1.
- `SemanticV2Service`, `TodayService` and caches remain untouched.

## 6. Public exports and generated boundary

### API exports

Re-export all new literal aliases/models from `apps/api/app/schemas/__init__.py`.
Do not add a new root to `PUBLIC_CONTRACT_ROOTS`; `TodayPayload` remains the
single owning root and pulls nested schemas into OpenAPI.

### Generate

Run:

```bash
pnpm contracts:sync
```

Expected compatibility:

```text
classification: additive
breakingChanges: 0
overrideUsed: false
```

Expected structural delta:

- new `TodayV2*Horizon*` component schemas;
- optional `TodayV2Block.horizons`;
- no removed/required existing fields;
- no version downgrade;
- no dummy root path addition.

### Type barrel

In `packages/contracts/index.ts` re-export generated types for:

```text
TodayV2Provenance
TodayV2GroundedItem
TodayV2HorizonTiming
TodayV2TechniqueExplanation
TodayV2Manifestation
TodayV2HorizonActions
TodayV2Horizon
TodayV2HorizonIntro
TodayV2HorizonsBlock
```

Literal aliases need not be manually re-declared; use property-indexed generated
types if a named alias is required in frontend.

### Runtime barrel

In `packages/contracts/runtime.ts` export generated:

```text
TodayV2HorizonsBlockWireSchema
TodayV2HorizonWireSchema
TodayV2HorizonTimingWireSchema
TodayV2ProvenanceWireSchema
```

### UI contract aliases

`lib/contracts/today.ts` may import/re-export generated types/schemas only.
No manual object/enum Zod declaration for new raw wire shapes.

## 7. Backend contract tests

Create `apps/api/tests/test_today_horizons_contract.py` with GRACE and pure
model factories. Do not call services/DB/network.

Mandatory matrix:

1. complete valid snake input validates;
2. camel dump round-trips;
3. `horizons` omitted/null accepted in `TodayV2Block`;
4. exact item order accepted;
5. wrong order rejected;
6. fewer/more than 3 rejected;
7. duplicate horizon/grounded/manifestation IDs rejected;
8. duplicate normalized action text across horizons rejected;
9. empty provenance rejected;
10. dangling horizon activation rejected;
11. dangling nested provenance activation rejected;
12. intro activation outside item union rejected;
13. technique mismatch/references rejected;
14. invalid product sphere rejected;
15. manifestation/provenance sphere outside likely spheres rejected;
16. date precision format/order/exact boundaries;
17. instant requires timezone and handles offsets deterministically;
18. exact state without exact_at rejected;
19. exact_at without peak_label rejected;
20. null exact with non-null peak_label rejected;
21. medium/fast without peak rejected;
22. action kind/count rules per horizon;
23. valid_until mismatch rejected;
24. timing aggregate min/max accepted;
25. timing aggregate mismatch rejected;
26. referenced untimed evidence allowed alongside timed evidence;
27. only untimed referenced evidence rejected;
28. opaque fact ID format rejects spaces/@/slash;
29. warnings uniqueness/non-empty;
30. errors do not contain human claim text.

Extend registry test:

- exact root count/order remains 22;
- new nested horizon schemas exist in generated OpenAPI;
- no new `/__contracts__/todayv2horizonsblock` dummy root;
- no `*Contract` component leak.

## 8. Canonical B1 fixture

Update the single JSON source:

```text
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
```

Do not create a second payload file. Wrapper remains unchanged and validates
through generated `TodayPayloadWireSchema`.

Add `v2.horizons` using existing activation IDs. It is synthetic test data and
must not be described as real production output.

### 8.1 Intro exact intent

```text
eyebrow: Личная логика периода
headline: Опору сейчас лучше перестраивать без резких движений
body: Долгий цикл меняет отношение к ответственности и контролю, ближайшие недели дают окно для одного практического изменения, а сегодняшний эмоциональный пик показывает, где не стоит торопиться.
themeKey: structure_boundaries_control
```

Intro IDs are the union/subset of selected horizon IDs.

### 8.2 Long fixture horizon

```text
horizon: long
tone: mixed
eyebrow: Долгий цикл · что перестраивать
title: Пересобрать опору, границы и отношение к контролю
timing: 2026-05-12 .. 2027-05-11, precision=date, state=background
rangeLabel: 12 мая 2026 — 11 мая 2027
stateLabel: Фон уже действует
activationIds: act-annual-profection, act-firdar-major
likelySpheres: work, decisions, money
```

Human copy explains duration and meaning without requiring knowledge of
profection/firdar. Strength uses opaque natal fact ID; risk uses another opaque
fact ID. At least one manifestation is conditional:

```text
Если сейчас вы обсуждаете новую роль или объём ответственности…
```

Actions: 1–2 structural do and 1–2 avoid, no firing/ultimatum/fatalism.

Because `act-firdar-major` currently has no fixture timing, aggregate boundary
comes from `act-annual-profection`; untimed evidence remains additional thematic
support.

### 8.3 Medium fixture horizon

```text
horizon: medium
tone: mixed
eyebrow: Текущий период · что попробовать
title: Проверить одну новую границу до 18 июля
timing: 2026-07-03T00:00:00Z .. 2026-07-18T00:00:00Z
exactAt: 2026-07-10T11:32:00Z
precision: instant
state: building
rangeLabel: 3–18 июля
peakLabel: Точный пик — 10 июля, 14:32 по Москве
stateLabel: Набирает силу
activationIds: act-pluto-trine-saturn, act-neptune-opp-saturn
likelySpheres: work, money, decisions
```

Actions use the discussed product intent:

- separate own responsibilities from habitual extras;
- discuss one concrete boundary conditionally;
- change one system element and observe;
- avoid drastic/ultimatum/control-driven decisions.

`act-neptune-opp-saturn` may remain untimed thematic support; aggregate timing
comes from `act-pluto-trine-saturn`.

### 8.4 Fast fixture horizon

```text
horizon: fast
tone: tense
eyebrow: Быстрый триггер · что сделать сегодня
title: Сначала назвать реакцию, потом отвечать
timing: 2026-07-07T21:00:00Z .. 2026-07-09T21:00:00Z
exactAt: 2026-07-08T05:00:00Z
precision: instant
state: peaked
rangeLabel: 8–10 июля по Москве
peakLabel: Пик был 8 июля в 08:00
stateLabel: Пик уже пройден
activationIds: act-moon-opp-pluto
likelySpheres: decisions, relationships, health
```

Exactly one do and 1–2 avoid. Text does not claim an emotion definitely
occurred; it gives a conditional observation/pause action.

### 8.5 Technique explanations

Each actual selected technique has human:

- label;
- `whatItIs`;
- `whyItMattersNow` linked to current horizon and dates;
- activation IDs inside horizon;
- optional timing equal to horizon timing.

No raw `Transit_`/`Natal_` prefixes.

## 9. Frontend consumer architecture

### 9.1 Branch exactly once

In `WhyExpanded`:

```text
if v2.horizons exists:
    render backend-owned intro/items
    do not call selectWhyTimeHorizons
else if v2 exists:
    call existing selectWhyTimeHorizons and render legacy path
else:
    existing whyToday/legacy sections
```

Do not compute backend horizon data with `useMemo` or merge backend and legacy
cards. `v2.horizons` is authoritative atomically.

### 9.2 Props for sphere navigation

Extend `WhyExpanded` props with:

```ts
concreteAdvice?: ConcreteAdviceBlock | null
onSphereSelect?: (key: string) => void
```

`TodayScreen` passes:

```text
payload.concreteAdvice
selectPersonalStorySphere
```

Backend horizon sphere buttons:

- render only when a matching concrete advice row exists;
- visible label comes from that row, not a new local map;
- button calls `onSphereSelect(row.key)`;
- existing TodayScreen state scrolls/focuses navigator and expands row;
- no direct DOM query in horizon component.

### 9.3 Backend content section

For backend horizons render:

```tsx
<section
  data-testid="why-horizons"
  data-state="ready"
  data-source="backend-horizons"
>
```

Intro must use backend `eyebrow/headline/body` exactly. Delete the hardcoded
constant intro from backend path. It may remain only in legacy path if needed
for one migration version.

### 9.4 Components

#### `why-time-horizon-card.tsx`

Own two explicit exports:

```text
WhyTimeHorizonCard        — new backend TodayV2Horizon card
LegacyWhyTimeHorizonCard  — current selector-derived fallback card
```

Backend card never reads raw ActivationEvidence and never formats raw timing.
It renders backend labels/state/text only.

Required root:

```text
data-testid="why-horizon"
data-horizon="long|medium|fast"
data-status="supportive|neutral|tense|mixed"
data-timing-state="..."
```

Visible tone labels:

```text
supportive -> Поддерживающий фон
neutral    -> Нейтральный фон
tense      -> Напряжённый фон
mixed      -> Смешанный фон
```

Required children:

```text
why-horizon-timing
why-horizon-strength       only when present
why-horizon-risk           only when present
why-horizon-actions
why-horizon-avoid
why-horizon-sphere
```

Render manifestations with condition before body when present.

#### `horizon-actions.tsx`

Pure component. Render backend heading, validity label, ordered do/avoid lists.
No generated advice, sorting or text inference.

#### `horizon-technique-disclosure.tsx`

Per-card real button and region:

```text
data-testid="why-horizon-technical-toggle"
data-testid="why-horizon-technical-content"
aria-expanded
aria-controls
role="region"
stable useId-based id
```

Collapsed label: `Как это рассчитано`.
Technical terms only inside opened content.

### 9.5 Legacy fallback

When `horizons` is null/absent:

- existing `selectWhyTimeHorizons` behavior unchanged;
- existing `why-time-horizon` selectors unchanged;
- existing global technical calculation remains available;
- no backend `why-horizon` elements render.

When backend block exists:

- `why-time-horizon` legacy elements absent;
- global raw-evidence technical calculation absent;
- new per-card disclosures render;
- old selector must not be invoked.

## 10. Frontend tests

### 10.1 Component tests

Extend `TodayScreen.v2-downstream.test.tsx`:

- backend intro exact fixture text;
- exactly 3 `why-horizon` in wire order;
- data-horizon/status/timing-state exact;
- timing uses backend labels, no JS recalculation;
- tone visible as text;
- actions/avoid counts and validity labels;
- optional strength/risk present/omitted correctly;
- manifestations conditions visible;
- each technique toggle starts `aria-expanded=false`;
- click opens associated region and human definitions;
- sphere button uses concrete advice row label and callback;
- no raw `Transit_`/`Natal_`;
- no legacy `why-time-horizon` when backend block exists;
- horizons null restores legacy cards;
- V2 without usable legacy evidence still safe.

Add a module mock/spy test proving `selectWhyTimeHorizons` is not called for
backend horizons. If Vitest ESM spy on direct import is unreliable, isolate the
backend/legacy branch into a small exported pure resolver in
`why-expanded.tsx`; do not move selection logic into a new product module.

### 10.2 Contract tests

`generated-runtime.test.ts`:

- valid horizons parse;
- invalid tone/timing scalar fails;
- unknown additive field succeeds and is stripped/tolerated;
- null/absent horizons succeeds.

`today-fixture-roundtrip.test.ts`:

- all horizon/nested provenance activation IDs resolve;
- item order exact;
- action/manifestation IDs unique;
- product sphere keys resolve to concrete advice rows;
- adapter preserves `v2` object identity;
- backend timing labels/state preserved.

### 10.3 Legacy presentation tests

`today-v2.test.ts` must keep all existing legacy selector tests green. Add one
guard that B1 did not change selection constants/algorithm. Do not rewrite the
test matrix.

## 11. Browser fixture proof

Update existing dev timing and mock-visual specs to the backend selectors when
the canonical fixture has `v2.horizons`.

Required dev assertions:

- guarded route remains the only API request;
- `why-horizons[data-source=backend-horizons]` visible;
- 3 ordered cards;
- long `Фон уже действует`;
- medium `Набирает силу` + exact peak;
- fast `Пик уже пройден`;
- one technical disclosure opens;
- Work horizon sphere button selects/focuses Work navigator row;
- normal URL and other-date fixture isolation unchanged.

Run on existing 3003 preview. Do not restart/change 18092 sidecar preview unless
the existing process is unhealthy; B1 does not need sidecar.

Save one mobile structural screenshot to:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/01-backend-contract-horizons-mobile.png
```

This is contract-consumer evidence, not final real-data acceptance.

## 12. Mandatory gates

### 12.1 Backend/contract

```bash
apps/api/.venv/bin/python -m pytest \
  packages/py-contracts/tests \
  apps/api/tests/test_contract_registry.py \
  apps/api/tests/test_today_horizons_contract.py \
  scripts/contracts/test_check_compat.py -q

pnpm contracts:sync
pnpm contracts:check
pnpm contracts:compat
npx vitest run __tests__/contracts
npx tsc --noEmit
```

### 12.2 Frontend focused

```bash
npx vitest run \
  __tests__/components/TodayScreen.v2-downstream.test.tsx \
  __tests__/lib/presentation/today-v2.test.ts \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-fixture-roundtrip.test.ts

E2E_BASE_URL=http://127.0.0.1:3003 \
  npx playwright test e2e/dev-timing-fixture.spec.ts --project=mobile
```

### 12.3 Full regression

```bash
cd apps/solarsage && venv/bin/python -m pytest tests -q
cd apps/api && .venv/bin/python -m pytest tests -q
cd ../..
npx vitest run
```

Expected:

```text
sidecar: 201 passed
API: same six baseline failures only + new tests passing
frontend: no new failures
```

### 12.4 Static/scope

```bash
apps/api/.venv/bin/python -m compileall -q \
  apps/api/app/schemas/today_horizons.py \
  apps/api/app/schemas/today.py \
  apps/api/tests/test_today_horizons_contract.py

git diff --check
git diff --cached --name-only
git status --short
git diff --name-only
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
```

Requirements:

- HEAD/origin remain `f0d8bef...`;
- index empty;
- exact allowlist only;
- generated artifacts deterministic after two generates;
- compatibility additive, zero breaking, no override;
- no service/canon/config/log/package-lock changes;
- unrelated untracked preserved;
- no commit/push.

## 13. Callback

```text
READY_STAGE_B1_HORIZON_CONTRACT
branch: preview/solarsage-v2-human-first-navigator-ux
head: f0d8bef19ec4f0806039cf44a173a22bb4f60a1c
origin_feature: f0d8bef19ec4f0806039cf44a173a22bb4f60a1c
api_horizon_models: PASS <count>
today_v2_optional_horizons: PASS
cross_reference_validator: PASS
timing_validator_matrix: PASS
action_count_validator: PASS
product_sphere_contract: PASS
production_population: NONE
compatibility: ADDITIVE breaking=0 override=false
generated_types: PASS
generated_zod: PASS
generated_diff_after_second_generate: ZERO
backend_contract_tests: <count> passed
contract_vitest: <count> passed
frontend_backend_source: PASS
legacy_selector_bypassed: PASS
legacy_fallback: PASS
sphere_navigation: PASS
technical_disclosures: PASS
fixture_roundtrip: PASS
dev_fixture_isolation: PASS
browser_screenshot: docs/work/2026-07-11_today-v2-real-horizons-main-deploy/b1/01-backend-contract-horizons-mobile.png
sidecar_full: 201 passed
api_full: BASELINE_RED_IDENTICAL <counts>
frontend_full: <counts>
diff_paths: <exact list>
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

После callback остановиться. Не commit/push и не начинать B2.
