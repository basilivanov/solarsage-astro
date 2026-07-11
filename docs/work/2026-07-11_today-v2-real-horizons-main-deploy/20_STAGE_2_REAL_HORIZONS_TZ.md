# Стадия 2 ТЗ — real timing, backend horizons, personal actions и frontend

Master:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/00_MASTER_TZ.md
```

Prerequisite: Stage 1 полностью принята и pushed. Выполнять волны строго
последовательно, без commit до architect review каждой волны.

## S2.W1 — Sidecar timing truth

### Цель

Сделать сроки частью расчётной истины, а не visual fixture copy.

### Contract changes

В обеих canonical ActivationEvidence schemas:

```text
apps/solarsage/solarsage/schemas/activation.py
apps/api/app/schemas/activation.py
```

добавить:

```py
active_from: str | None = None
exact_at: str | None = None
active_until: str | None = None
```

`exact_at` уже существует — сохранить wire name и дополнить реальным значением.

Semantics:

- timestamps: timezone-aware ISO-8601 UTC with `Z`;
- date-only periods: `YYYY-MM-DD` in the calculation target timezone;
- `active_from` and `active_until` are inclusive display boundaries;
- `exact_at` is the exact hit inside the selected current pass;
- fields may be null only for an activation type with no meaningful calculable
  boundary; horizon selection may not choose such evidence when a required
  timing horizon needs complete dates.

### Period boundaries

Populate timing deterministically:

#### Annual profection

- `active_from`: most recent birthday on/before target local date;
- `active_until`: day before next birthday;
- both house and lord activations get identical boundaries.

#### Monthly profection

- `active_from`: current monthly anniversary from the existing non-drifting
  annual-year-start calculation;
- `active_until`: day before next monthly anniversary;
- clamp rules must reuse existing `_add_months_with_clamp`.

#### Firdar major/minor

- derive dates from the same canon/year-length and age arithmetic used by
  `calculate_firdar`;
- do not invent a separate conversion constant;
- major activations use major start/end;
- minor activations use minor start/end;
- add explicit tested helper in firdar service if current result only exposes
  fractional ages.

#### Solar/lunar return

- `exact_at`: calculated return UTC instant;
- `active_from`: that return instant;
- `active_until`: instant immediately before the next corresponding calculated
  return; display formatting may show the next-return date as exclusive only in
  technical debug, but user-facing interval must not overlap two periods.

### Transit aspect timing solver

Create a dedicated sidecar service, not UI/API approximation:

```text
apps/solarsage/solarsage/services/transit_timing.py
```

Inputs:

- target instant/JD;
- source planet;
- fixed natal/angle/lot target longitude;
- aspect angle;
- canonical max orb;
- calculation timezone metadata.

Outputs:

```py
TransitTimingResult(
    active_from_utc,
    exact_at_utc,
    active_until_utc,
    occurrence_index,
    exact_hits_in_window,
)
```

Required algorithm properties:

1. Use Swiss Ephemeris positions, not linear `orb / current_speed` estimates.
2. Find the contiguous current orb window containing the requested target
   instant.
3. Correctly handle 0°/360° wrap.
4. Correctly handle retrograde motion, stations and multiple exact passes.
5. Choose the exact hit inside the contiguous current window; if there are
   multiple, choose the closest to target and expose all hit timestamps in
   debug.
6. Coarse search is adaptive by source planet speed/window, followed by bounded
   bisection/root refinement.
7. Exact-time refinement target: <= 60 seconds.
8. Orb-boundary refinement target: <= 5 minutes.
9. No unbounded scan. Define per-planet maximum search horizon and return a
   typed warning/failure when a boundary cannot be bracketed.
10. Batch/cache ephemeris positions per source/time within one activation-layer
    request; do not independently recalculate the entire chart for every pair.

Populate timing for transit-to-natal, transit-to-angle and transit-to-lot
aspect activations. Planet-in-house timing is out of this wave unless a reliable
house ingress/egress solver already exists; it may remain null and must not be
selected as the only fast/medium timing evidence.

### Phase consistency

`phase`, `applying` and timing must agree:

- target before exact hit in current window → `applying`;
- within exact tolerance → `exact`;
- after last relevant exact hit → `separating`;
- period activation → `period`.

Add model/service invariant tests. Do not silently emit applying with an
`exact_at` before target.

### Version bumps

Update API and sidecar canonical constants together:

```text
CALCULATION_VERSION      ss-calc-1.2.0
ACTIVATION_LAYER_VERSION al-1.1
```

Scoring version remains `ss-scoring-2.0`.

### Tests

Sidecar:

- schema round trip active/exact/until;
- annual/monthly boundary leap-day and month-clamp cases;
- firdar major/minor boundaries;
- direct transit pass;
- retrograde triple pass;
- longitude wrap;
- Moon short window;
- slow outer-planet window;
- phase/timing consistency;
- deterministic identical output;
- performance budget.

API:

- sidecar validation preserves timing exactly;
- activation ID and timing parity;
- fallback activations keep null timing without fabricating;
- OpenAPI/generated contracts include camelCase fields.

### Performance gate

Record benchmark for representative full activation-layer request. Timing
resolution must not multiply request latency without a documented bound.
Preferred target: p95 sidecar calculation under 2 seconds on this host for one
day/profile; if not achieved, return evidence and optimize batch caching before
acceptance.

### Gates

```bash
cd apps/solarsage && python -m pytest tests/ -q
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_activation_contracts.py \
  tests/test_today_meta_versions.py \
  tests/test_pipeline_invariants.py -q
pnpm contracts:generate
pnpm contracts:check
git diff HEAD --check
```

### Callback

```text
READY_S2_W1_REAL_TIMING
versions: <calc>; <activation>
period_boundaries: <proof>
transit_accuracy: <proof/tolerances>
retrograde_test: PASS
api_sidecar_parity: PASS
benchmark: <numbers>
tests: <results>
commit: NOT_YET
push: NOT_YET
```

Suggested commit after acceptance:

```text
feat(solarsage): calculate activation timing windows
```

---

## S2.W2 — Structured horizon wire contract and deterministic selection

### Цель

Backend, а не frontend, выбирает три горизонта и формирует coherent personal
story structure.

### Pydantic schemas

Добавить в `apps/api/app/schemas/today.py` и export through OpenAPI.

```py
TodayV2Capability = Literal[
    "horizon_timing",
    "horizon_guidance",
    "personal_actions",
    "visible_sphere_status",
]

TodayV2HorizonId = Literal["long", "medium", "fast"]

TodayV2HorizonPhase = Literal[
    "upcoming",
    "building",
    "exact",
    "easing",
    "active",
    "background",
]

class TodayV2HorizonIntro(CamelModel):
    eyebrow: str
    headline: str
    body: str
    evidence_ids: list[str]

class TodayV2HorizonTiming(CamelModel):
    active_from: str | None = None
    exact_at: str | None = None
    active_until: str | None = None
    phase: TodayV2HorizonPhase
    current_label: str

class TodayV2PersonalMeaning(CamelModel):
    summary: str
    strength: str | None = None
    risk: str | None = None
    evidence_ids: list[str]
    natal_fact_ids: list[str] = []

class TodayV2PersonalAction(CamelModel):
    id: str
    text: str
    conditional: bool = False
    valid_from: str | None = None
    valid_until: str | None = None
    sphere_keys: list[str]
    evidence_ids: list[str]
    natal_fact_ids: list[str] = []

class TodayV2HorizonActions(CamelModel):
    do: list[TodayV2PersonalAction]
    avoid: list[TodayV2PersonalAction]

class TodayV2Horizon(CamelModel):
    id: TodayV2HorizonId
    title: str
    body: str
    range_label: str
    timing: TodayV2HorizonTiming
    likely_sphere_keys: list[str]
    personal_meaning: TodayV2PersonalMeaning
    actions: TodayV2HorizonActions
    evidence_ids: list[str]
```

Extend `TodayV2Block` additively:

```py
capabilities: list[TodayV2Capability] = []
horizon_intro: TodayV2HorizonIntro | None = None
horizons: list[TodayV2Horizon] | None = None
```

During branch development these are optional for old fixture/cache
compatibility. Final new payload must populate all three.

### Validators

When `horizons` is present:

1. Order is exactly `long`, `medium`, `fast`.
2. No duplicate ID.
3. All horizon/effect/action evidence IDs exist in `activation_evidence`.
4. Sphere keys belong to the known concrete/canon sphere set.
5. Human fields contain no banned technical terms:
   `транзит`, `профекция`, `фирдар`, `орб`, raw IDs, frame names.
6. No empty action text.
7. Maximums:
   - `do`: 3;
   - `avoid`: 4;
   - likely spheres: 4;
   - title: 180 chars;
   - body/meaning item: bounded for UI.
8. `conditional=True` is required for claims depending on unknown life context;
   conditional action text must explicitly contain conditional wording.
9. Every personal strength/risk has evidence or natal fact provenance.

### Backend selection service

Create:

```text
apps/api/app/services/horizon_selection_service.py
```

It receives only calculated data:

- ActivationLayer;
- ScoringV2Result;
- concrete advice rows;
- canon sphere mappings.

It returns selected evidence IDs and sphere keys, not final prose.

### Candidate classes

#### Long

Prefer period/return evidence:

```text
annual_profection
firdar_major
firdar_minor
solar_return
```

and duration >= 180 days where available.

#### Medium

Prefer:

- slow/outer transit windows;
- monthly profection;
- lunar return or subperiod;
- duration roughly 14–180 days;
- strongest linkage to current top-ranked spheres.

#### Fast

Prefer:

- Moon/fast-planet transit aspect;
- complete timing window;
- duration from hours to several days;
- high strength and direct overlap with the selected story sphere.

Do not select planet-in-house evidence without timing as the only fast trigger.

### Coherence scoring

Score candidate triples deterministically using:

- shared sphere overlap;
- shared target overlap;
- activation contribution impact;
- strength;
- independent technique-family convergence;
- complete timing bonus;
- why/evidence linkage.

Store selection score/reasons only in safe audit/debug, not human UI.

### Honest intro

If all three horizons have meaningful shared sphere/target convergence, intro may
say one story repeats at three speeds.

If convergence is weak, intro must not claim a single story. Use a truthful
dynamic alternative such as:

```text
Сегодня несколько личных процессов накладываются друг на друга, но действуют в
разном масштабе времени.
```

The currently hardcoded frontend intro becomes a backend field and later a
legacy fallback only.

### Tests

- stable selection under shuffled evidence;
- long/medium/fast ordering;
- coherent triple selection;
- weak-convergence honest intro mode;
- complete timing preference;
- missing candidate behavior without fabrication;
- evidence/sphere validator failures;
- generated TS/Zod contract updates.

### Callback

```text
READY_S2_W2_HORIZON_CONTRACT
schema_exports: <list>
selection_service: <file>
coherence_cases: <results>
validators: <results>
contracts_check: PASS
tests: <results>
commit: NOT_YET
push: NOT_YET
```

Suggested commit:

```text
feat(today): add structured personal horizon contract
```

---

## S2.W3 — Personal fact pack, actions and claim safety

### Цель

Наполнить выбранные горизонты персональными значениями и конкретными действиями,
не выдумывая жизненные события.

### Services

Create:

```text
apps/api/app/services/personal_fact_pack_service.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/horizon_claim_validator.py
```

Add versioned canon:

```text
grace/canon/horizon_guidance.v1.yml
```

Register canon version through existing canon service and audit.

### Internal fact types

Define typed internal models, separate from wire copy:

```text
activation_fact
sphere_fact
convergence_fact
natal_strength
natal_risk
profile_fact
timing_fact
```

Each fact has:

- stable fact ID;
- source kind;
- human-safe semantic code;
- sphere keys;
- activation evidence IDs when applicable;
- natal source refs when applicable;
- confidence;
- no free-form unsupported event.

### Natal facts

Do not use prose from a previously generated natal LLM report as proof.

Natal strengths/risks may be emitted only when:

1. `NatalContextData` contains the required deterministic placement/aspect;
2. a versioned allowlisted canon rule maps that fact to a bounded human pattern;
3. the fact stores exact source refs;
4. wording does not claim a real event or profession.

If no confirmed natal fact is available, `strength`/`risk` remain null or use a
current-period meaning explicitly framed as current, not a stable personality
claim.

### Profile facts

Allowed current profile fields are limited. Do not infer occupation,
relationship or finance context from gender/name/location.

Profile facts may affect grammar/name only unless a future explicit field exists.
Unknown context uses conditional wording.

### Deterministic fallback first

`HorizonGuidanceService` must always be able to build safe deterministic output
without LLM.

#### Long horizon output

- main personal meaning;
- optional confirmed strength;
- optional confirmed risk;
- likely spheres;
- at least one broad rebuild direction when evidence supports it.

#### Medium horizon output

- 1–3 concrete `do` actions;
- exact `validUntil` from timing;
- likely sphere keys;
- 1–4 avoid actions where verdict/polarity supports them.

#### Fast horizon output

- exactly one immediate `do` action;
- exactly one `avoid` action;
- exact/active-until reference;
- current stage explains whether peak is ahead or passed.

### Action derivation

Actions use:

- selected horizon sphere keys;
- `ConcreteAdviceRow.verdict/text/evidence`;
- activation polarity/phase;
- timing validity;
- confirmed natal fact pack.

Do not copy one generic advice row into all three horizons. Each horizon has a
distinct action scale.

### Optional LLM refinement

Add one method that refines all horizons in one structured call, not three
separate calls:

```text
LLMService.generate_horizon_guidance(fact_pack, deterministic_draft)
```

Rules:

- LLM receives only fact pack and deterministic draft;
- returns strict JSON matching horizon guidance schema;
- cannot add evidence IDs/sphere keys not supplied;
- cannot change timing values;
- cannot change horizon selection;
- cannot claim profession/events/relationships/debts;
- conditional life-domain examples remain conditional;
- human surface contains no technical astrology vocabulary.

### Claim validator

`HorizonClaimValidator` validates:

- provenance subsets;
- banned technical vocabulary;
- banned unsupported certainty phrases;
- conditional flag/text consistency;
- action count by horizon;
- exact date immutability;
- no unsafe high-stakes medical/legal/financial directive;
- no destructive decision recommendation at fast emotional peak.

On any failure:

- log safe reason/code;
- discard the entire LLM horizon output or invalid item according to explicit
  deterministic policy;
- return deterministic fallback;
- never return partially untraceable personal copy.

### Example target content for current reference payload

Long meaning may express, when supported by facts:

```text
Вы умеете выдерживать ответственность и сохранять порядок под давлением. Но в
ситуации неопределённости можете пытаться вернуть устойчивость через ещё больший
контроль.
```

If stable natal support is not actually proven, replace with current framing:

```text
Сейчас у вас есть поддержка для более собранного и последовательного подхода.
При неопределённости риск — пытаться вернуть устойчивость через ещё больший
контроль.
```

Medium actions through 18 July, when supported:

- separate actual responsibilities from habitual ones;
- discuss one concrete boundary around workload, responsibility, money or
  agreement terms, using conditional wording for unknown context;
- change one system element and observe before rebuilding everything.

Avoid:

- resign/break an agreement on emotion only as a conditional context example;
- ultimatums;
- new responsibility taken only to regain control;
- major decision at emotional peak.

### Logging

Add events to registries before use, for example:

```text
day.horizon_guidance_started
day.horizon_guidance_succeeded
day.horizon_guidance_fallback
day.horizon_guidance_failed
```

Every log has slice/module/block/correlation_id. Do not log raw fact pack,
profile data or birth information.

### Tests

- fact pack includes only supplied sources;
- absent natal fact does not create strength/risk;
- conditional unknown-context wording;
- deterministic fallback for all three horizons;
- LLM valid response accepted;
- fabricated profession/event rejected;
- mutated date rejected;
- foreign evidence ID rejected;
- banned astrology jargon rejected from human copy;
- LLM failure returns deterministic result;
- actions differ by horizon scale.

### Callback

```text
READY_S2_W3_PERSONAL_GUIDANCE
fact_sources: <list>
natal_claim_policy: <proof>
deterministic_fallback: PASS
llm_validator_cases: <results>
example_horizons: <artifact path>
logs_registry: <events>
tests: <results>
commit: NOT_YET
push: NOT_YET
```

Suggested commit:

```text
feat(today): build evidence-backed horizon guidance
```

---

## S2.W4 — Frontend consumes real horizons and actions

### Цель

Перевести accepted preview design на backend-owned `v2.horizons`.

### Required behavior

1. `WhyExpanded` reads:
   - `v2.horizonIntro`;
   - `v2.horizons`.
2. New payload path does not call frontend `selectWhyTimeHorizons` for selection.
3. Existing selector is a clearly marked migration fallback only when
   `horizons` is absent in an old cached payload.
4. Add structural source marker:

```text
data-source="backend-horizons|legacy-derived"
```

5. Final production real payload must render `backend-horizons`.
6. Static intro becomes fallback only. Backend intro changes by actual
   convergence/story.
7. Timing renders exact backend values; frontend only formats timezone/date.
8. Invalid/missing date never renders `NaN`.

### Horizon-specific UI

#### Long

Visible sections:

```text
Что это может значить именно для вас
На что можно опереться          (only when strength exists)
Где привычный риск             (only when risk exists)
Где это вероятнее проявится
```

#### Medium

```text
Что попробовать до <date>
- 1–3 actions

Чего сейчас лучше не делать
- avoid actions

Вероятные сферы
```

#### Fast

```text
Что сделать сегодня
<one action>

Что лучше отложить
<one action>

Когда пик/напряжение ослабеет
<timing/stage>
```

### Sphere links

Likely sphere chips/buttons use existing human labels and may focus/open the
corresponding 12-sphere navigator row. Preserve accessible focus/scroll
contracts.

### DOM contracts

Add:

```text
data-testid="why-horizon-intro"
data-testid="why-horizon-personal-meaning"
data-testid="why-horizon-strength"
data-testid="why-horizon-risk"
data-testid="why-horizon-actions-do"
data-testid="why-horizon-actions-avoid"
data-testid="why-horizon-spheres"
data-testid="why-horizon-action"
data-horizon="long|medium|fast"
data-source="backend-horizons|legacy-derived"
```

Use lists for action lists. Buttons/chips are real buttons when interactive.

### Visual constraints

- mobile 390px first;
- avoid one enormous undifferentiated text wall;
- timing and action blocks visually distinct but within the same horizon card;
- human copy visible by default; technical astrology remains in separate
  calculation disclosure;
- no color-only semantics;
- dark theme readable.

### Contract migration

Use generated wire TS/Zod from Stage 1. Do not add new manual raw V2 schema.

### Tests

- backend horizons preferred over legacy selector;
- dynamic intro rendered;
- every horizon specific section rendered correctly;
- missing optional strength/risk hides section;
- action evidence is not exposed as raw IDs;
- sphere link focuses correct navigator row;
- timing format and invalid-date guard;
- no technical vocabulary in human blocks;
- legacy cached payload fallback still renders and is marked;
- visible sphere verdict statuses remain.

### Browser artifacts

Create review screenshots from real backend response on local 3003, no fixture
query:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/assets/
  01-real-day-horizons-mobile.png
  02-real-medium-actions-mobile.png
  03-real-fast-action-mobile.png
```

Do not use Playwright route interception for these three artifacts.

### Callback

```text
READY_S2_W4_REAL_FRONTEND
real_url: <url without fixture>
data_source: backend-horizons
intro: <text>
long: <sections>
medium: <actions/timing>
fast: <actions/timing>
screenshots: <paths>
tests: <results>
commit: NOT_YET
push: NOT_YET
```

Suggested commit:

```text
feat(today): render backend personal horizon actions
```

---

## S2.W5 — Cache/version integration and real E2E

### Version/cache changes

After new backend/frontend path is complete, bump together:

```text
TODAY_V2_PAYLOAD_VERSION     today.v2.1
V2_FRONTEND_PAYLOAD_VERSION  3
TODAY_CONTENT_VERSION        10
prompt version               3 if new LLM prompt ships
```

Update cache read/write identity, meta tests, audit artifacts and calendar
compatibility tests. Old cache must miss; do not deserialize old today.v2 as if
it contained backend horizons.

### Real integration test

Add backend integration test that exercises:

```text
trusted sidecar ActivationLayer with timing
  -> API validation
  -> scoring
  -> horizon selection
  -> fact pack/guidance
  -> TodayPayload.model_dump(by_alias=True)
  -> generated runtime Zod
  -> frontend adapter
```

Assertions:

- activation ID sets preserved;
- timing fields preserved;
- three horizons ordered;
- all provenance refs resolve;
- medium/fast actions have correct validity;
- payload versions/cache versions exact;
- frontend data source is backend-horizons.

### Real browser E2E

Use signed Telegram initData generator and real API. No `page.route('/api/**')`.

Test:

- auth succeeds;
- `/api/day/<date>` response includes backend horizons;
- frontend root ready;
- dynamic intro and all three horizons visible;
- medium action deadline and fast action displayed;
- timing stages match JSON;
- 12-sphere statuses visible;
- no dev fixture root/endpoint;
- no console errors;
- screenshot.

### Full gates before release

```bash
pnpm contracts:generate
pnpm contracts:check
npx vitest run
cd apps/solarsage && python -m pytest tests/ -q
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
NEXT_DIST_DIR=.next-s2-release-proof pnpm build
E2E_BASE_URL=http://127.0.0.1:3003 npx playwright test
git diff HEAD --check
```

Restore generated Next type files and delete only proof dist after build.

### Stage 2 readiness callback

```text
READY_STAGE_2_FOR_MAIN_RELEASE
commits: <wave SHAs>
versions: <all>
contracts: PASS
sidecar_tests: <count>
api_tests: <count>
frontend_tests: <count>
build: PASS
real_e2e: PASS <artifact>
real_payload_artifact: <path>
frontend_data_source: backend-horizons
dev_fixture_dependency_in_real_flow: NO
commit: NOT_YET_FOR_W5
push: NOT_YET_FOR_W5
```

Suggested commit:

```text
test(today): prove real personal horizons end to end
```
