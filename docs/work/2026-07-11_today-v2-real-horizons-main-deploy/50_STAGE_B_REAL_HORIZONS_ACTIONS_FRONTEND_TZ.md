# Stage B ТЗ — реальные три горизонта, персональные действия и production UI

Дата: 2026-07-11
Репозиторий: `/opt/solarsage-astro`
Целевая feature branch:
`preview/solarsage-v2-human-first-navigator-ux`
Статус: **future implementation plan; не выполнять до полного принятия Stage A
и явной команды `START_STAGE_B_REAL_HORIZONS`**.

## 0. Место стадии и конечная цель

Prerequisites:

1. S2.W1 real timing принят, committed и pushed.
2. Stage A shared Python contracts принят, committed и pushed.
3. Feature worktree clean; local feature SHA равен origin feature SHA.
4. Main не изменяется до финальной release wave.

Stage B должна превратить calculation evidence в реальный human-first product:

```text
sidecar factual activations + real timing
  -> API coherent three-horizon selection
  -> grounded personal fact pack
  -> grounded explanations/actions
  -> optional constrained LLM wording
  -> public TodayV2 horizons contract
  -> generated TS/Zod
  -> frontend rendering without astrology inference
```

После Stage B и финального release пользователь в обычном `/day/<date>` видит:

- один динамический личный сюжет, не постоянную заготовку;
- долгий фон с реальным сроком;
- средний период с реальным окном и пиком;
- быстрый trigger с коротким окном и состоянием пика;
- где это вероятнее проявится;
- на какую подтверждённую сильную сторону опереться;
- какой подтверждённый паттерн может мешать;
- что конкретно сделать;
- чего лучше не делать;
- до какого срока совет актуален;
- раскрываемое человеческое объяснение профекции, фирдара, return/transit;
- кликабельные 12 сфер как быстрый навигатор;
- явный semantic tone: поддерживающий, нейтральный, напряжённый или смешанный.

## 1. Жёсткие продуктовые правила

### 1.1 Не три случайных факта

Тройка должна быть coherent story, а не просто top-3 strengths.

```text
long   задаёт устойчивый фон/перестройку
medium усиливает или конкретизирует тему на недели/месяцы
fast   даёт непосредственный trigger сегодня
```

Связность доказывается общими targets/spheres/theme keys и независимыми
technique families.

### 1.2 Динамическая вводная

Запрещена одна постоянная фраза для всех:

```text
Это не три случайных факта. Один личный сюжет идёт в трёх скоростях.
```

Она допустима только как одна из deterministic templates при подходящем
coherence pattern. Headline/body строятся из выбранной темы и фактов.

Tests минимум на три разных fact packs должны получать содержательно разные
headline/body, не только заменённое имя планеты.

### 1.3 Human-first

Основной текст не требует знаний терминов `фирдар`, `профекция`, `орб`,
`аппликация`, `return`.

Порядок информации:

```text
человеческий смысл
  -> срок
  -> проявления/действия
  -> раскрываемая техническая причина
```

### 1.4 Не выдумывать жизнь

Запрещено утверждать без user-provided fact:

- конкретную профессию/должность/работодателя;
- наличие партнёра, брака, развода, конфликта;
- долг, доход, покупку, кредит;
- болезнь/диагноз;
- увольнение, переезд, сделку или событие, которое якобы уже произошло;
- намерения другого человека.

Если контекст неизвестен:

```text
Если сейчас вы обсуждаете новую роль или объём ответственности…
```

### 1.5 Максимальная точность означает provenance

Каждое персональное утверждение обязано иметь typed source references. Красивый
текст без provenance считается не персонализацией, а hallucination.

## 2. Architectural ownership

### Sidecar owns

- astronomy calculation;
- activation IDs;
- technique/family;
- target;
- strength/polarity/current phase;
- `activeFrom/exactAt/activeUntil`;
- factual debug/audit.

### API owns

- horizon classification/selection;
- coherent story;
- sphere/theme linkage;
- grounded natal/profile fact pack;
- tone aggregation;
- all user-facing explanations/actions;
- LLM safety/validation/fallback;
- public Today horizon read model;
- cache/content/prompt versions.

### Frontend owns

- layout;
- typography/color/icon mapping from enums;
- date/time formatting only when contract does not provide display copy;
- accordion/navigation/accessibility;
- responsive behavior.

Frontend запрещено:

- выбирать evidence для long/medium/fast для нового payload;
- вычислять duration/phase/astrological meaning;
- создавать personal strengths/risks/actions;
- infer tone из текста;
- сравнивать version strings для UI branching.

## 3. Public API contract

Добавить models в feature-local module, предпочтительно:

```text
apps/api/app/schemas/today_horizons.py
```

и re-export через `app.schemas` / `today.py` без ручного TS/Zod объявления.

### 3.1 Enums

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

TodayV2GuidanceMode = Literal[
    "deterministic",
    "llm_refined",
]
```

Horizon tone не смешивать с existing 12-sphere verdict:

```text
horizon tone: supportive/neutral/tense/mixed
sphere verdict: good/neutral/caution/avoid
```

### 3.2 Provenance

```py
class TodayV2Provenance(CamelModel):
    activation_ids: list[str] = Field(default_factory=list)
    natal_fact_ids: list[str] = Field(default_factory=list)
    profile_fact_ids: list[str] = Field(default_factory=list)
    sphere_keys: list[str] = Field(default_factory=list)
```

Invariant: для personal claim хотя бы один source list non-empty. Profile IDs
opaque и не содержат raw value.

### 3.3 Grounded text/action item

```py
class TodayV2GroundedItem(CamelModel):
    id: str
    kind: TodayV2ClaimKind
    text: str
    conditional: bool = False
    provenance: TodayV2Provenance
```

`conditional=False` разрешено только если claim непосредственно подтверждён.
Unknown life context требует `conditional=True`.

### 3.4 Timing

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

Machine values и human labels coexist намеренно:

- raw values используются для audit/tests/future locale formatting;
- labels являются backend-owned human copy текущего продукта;
- frontend не вычисляет `Пик уже пройден` из wall clock;
- API строит labels с effective user/target timezone.

Required validation:

- consistent date-only или instant format;
- `active_from <= active_until`;
- exact внутри range, если non-null;
- `state=exact` требует exact_at;
- `peak_label` non-null, если exact_at non-null;
- range/state labels non-empty.

### 3.5 Technical explanation

```py
class TodayV2TechniqueExplanation(CamelModel):
    technique: str
    label: str
    what_it_is: str
    why_it_matters_now: str
    timing: TodayV2HorizonTiming | None = None
    activation_ids: list[str]
```

Примеры content responsibility:

```text
Профекция — символический годовой цикл, который выделяет одну жизненную область
и её управляющую планету. В вашем текущем году...

Фирдар — длинная последовательность периодов, показывающая, какие планетарные
темы находятся на переднем плане. Ваш текущий период действует с ... по ...
```

Нельзя выдавать dictionary definition без personal meaning/date linkage.

### 3.6 Manifestation

```py
class TodayV2Manifestation(CamelModel):
    id: str
    title: str
    body: str
    condition: str | None = None
    sphere_keys: list[str]
    provenance: TodayV2Provenance
```

`condition` обязателен, если body описывает неизвестный real-life scenario.

### 3.7 Actions

```py
class TodayV2HorizonActions(CamelModel):
    heading: str
    valid_until: str
    valid_until_label: str
    do: list[TodayV2GroundedItem]
    avoid: list[TodayV2GroundedItem]
```

Card-specific requirements:

- long: 1-2 `do`, 1-2 `avoid` про то, что перестраивать;
- medium: 2-3 `do`, 1-3 `avoid` про эксперимент/границы на window;
- fast: ровно один primary `do`, минимум один `avoid`, время окончания peak;
- все action items provenance-backed;
- no duplicated action text между horizons;
- no contradiction с 12-sphere verdicts.

### 3.8 Horizon item

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
    likely_spheres: list[str]
    manifestations: list[TodayV2Manifestation]
    strength: TodayV2GroundedItem | None = None
    risk: TodayV2GroundedItem | None = None
    actions: TodayV2HorizonActions
    technique_explanations: list[TodayV2TechniqueExplanation]
    activation_ids: list[str]
```

`likely_spheres` содержит только canonical keys existing 12-sphere navigator.

### 3.9 Dynamic intro and block

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
    items: list[TodayV2Horizon]
    warnings: list[str] = Field(default_factory=list)
```

Добавить additive optional поле:

```py
class TodayV2Block(CamelModel):
    ...
    horizons: TodayV2HorizonsBlock | None = None
```

No payload/schema major bump для additive optional field. При реальном rollout
обновить content/cache identity отдельно.

### 3.10 Cross-object validator

`TodayV2Block` validator обязан доказать:

- items ordered exactly `long`, `medium`, `fast`;
- IDs unique;
- every horizon activation ID существует в `activation_evidence`;
- every nested provenance activation ID существует;
- every sphere key существует в `score_breakdown`/canonical sphere registry;
- timing machine values совпадают с referenced evidence или documented
  aggregate intersection/union policy;
- intro IDs являются subset union horizon IDs;
- no empty headline/summary/action strings;
- no duplicate normalized action strings;
- no raw profile values in provenance IDs.

## 4. Why contract changes become rare

Новая техника не создаёт новое поле. Она является новым element:

```json
{
  "technique": "solar_return",
  "activationIds": ["..."],
  "...": "..."
}
```

Classification/presentation metadata добавляется в versioned canon. Contract
меняется только при принципиально новом типе пользовательской возможности.

Запрещено добавлять fields вроде:

```text
plutoTransitText
firdarAdvice
monthlyProfectionLabel
```

## 5. Versioned horizon canon

Создать:

```text
grace/canon/horizon_selection.v1.yml
grace/canon/horizon_language.ru.v1.yml
grace/canon/horizon_actions.ru.v1.yml
grace/canon/personal_patterns.ru.v1.yml
```

### 5.1 Selection canon owns

- duration bands;
- technique preferred horizons;
- planet speed groups;
- min strength/impact;
- convergence bonuses;
- family diversity bonus;
- same-target/same-sphere/theme overlap weights;
- deterministic tie-breakers;
- fallback eligibility;
- maximum candidate counts.

### 5.2 Language canon owns

- technique human labels;
- short definitions;
- timing state labels;
- intro templates keyed by coherence pattern/theme;
- tone labels;
- safe conditional sentence forms.

### 5.3 Action canon owns

- action templates by horizon/theme/tone/sphere;
- avoid templates;
- forbidden combinations;
- conditionality requirement;
- safety class.

### 5.4 Personal pattern canon owns

- allowlisted natal fact pattern IDs;
- strength/risk text keys;
- required chart evidence;
- confidence threshold;
- prohibited overclaim forms.

Every canon file validates at startup/test through typed schema. Invalid canon
fails tests/startup deterministically; no silent defaults.

Canon versions входят в Today audit/cache identity.

## 6. Timing classification

Create API service/module:

```text
apps/api/app/services/horizon_timing_service.py
```

It receives already validated ActivationEvidence; no ephemeris/math.

### 6.1 Duration calculation

- date-only range: inclusive calendar days in target timezone;
- instant range: seconds between UTC instants;
- malformed/mixed range: evidence ineligible and typed warning;
- target containment required;
- no current date from server clock: use requested target date/time.

### 6.2 Preferred duration bands

Initial canon intent:

```text
long:   >= 180 days, strong long-cycle technique or slow transit
medium: 45 .. 210 days preferred; current multi-week/month influence
fast:   <= 21 days, fast transit/short trigger
```

Overlaps deliberate and resolved by technique preference/coherence. Thresholds
live in canon, not scattered constants.

### 6.3 Timing state

Deterministic state derives from target vs raw timing:

- before active_from -> upcoming;
- early window before exact -> building;
- within exact tolerance -> exact;
- after exact and close -> peaked;
- after exact but still substantial -> fading;
- period without exact -> active/background according to technique/horizon.

Exact tolerances taken from evidence/debug or canon. Frontend does not recompute.

## 7. Candidate impact and coherent story selection

Create:

```text
apps/api/app/services/horizon_selection_service.py
```

### 7.1 Candidate features

For every eligible evidence derive typed internal candidate:

- activation ID;
- horizon eligibility/preference;
- duration;
- strength;
- polarity;
- technique/family;
- source/target;
- mapped spheres;
- score contribution;
- target convergence count;
- family diversity;
- timing completeness;
- exact proximity;
- theme keys.

### 7.2 Impact score

Formula must be documented and canon-driven. It may combine:

```text
activation strength
sphere contribution/rank
target convergence
independent family bonus
timing relevance
same-story overlap
```

No random/LMM ranking. Stable tie-break:

```text
impact desc
timing completeness desc
strength desc
technique priority
activation ID lexicographic
```

### 7.3 Triple selection

Algorithm:

1. Rank valid long anchors.
2. For each long anchor rank medium candidates by story overlap.
3. For each pair rank fast candidates by overlap/trigger relevance.
4. Score complete triples.
5. Select deterministic best triple.
6. Prefer independent technique families, but never sacrifice real timing or
   minimum impact merely to increase family count.

Story overlap hierarchy:

```text
same target
same canonical theme
shared top sphere
same target planet/house
explicit score contribution linkage
```

### 7.4 Honesty fallback

Нельзя force-select weak/unrelated evidence ради красивой тройки.

If no acceptable triple:

- `horizons=None` during rollout;
- existing legacy frontend presentation remains fallback;
- typed internal warning/audit reason;
- no production error;
- no invented medium/fast timing.

Before release, representative coverage gate must show sufficient real triple
availability. Threshold не ослаблять молча.

### 7.5 Coverage corpus

Создать test-only deterministic corpus:

- Basil request/date and nearby boundary dates;
- at least 5 synthetic birth profiles with valid locations/timezones;
- at least 12 target dates spanning a year;
- leap-day/birthday/timezone boundaries;
- no real user IDs/auth/profile data.

Acceptance target:

```text
>= 95% corpus cases: valid complete long/medium/fast triple
100% selected triples: complete timing and provenance
0 forced weak candidates below canon threshold
```

Если coverage ниже, callback должен показать missing horizon reasons; coder не
меняет thresholds без architect review.

## 8. Personal fact pack

Create internal typed models/service:

```text
apps/api/app/schemas/personal_fact_pack.py
apps/api/app/services/personal_fact_pack_service.py
```

Fact pack не является public wire целиком; public payload содержит только
grounded output and opaque fact IDs.

### 8.1 Allowed sources

- selected activation evidence;
- ScoringV2 contributions/ranked spheres;
- existing cached `NatalContextData` only;
- versioned personal pattern canon;
- explicit allowlisted profile fields.

### 8.2 Prohibited sources

- guessed life events;
- previous LLM text;
- raw frontend fixture;
- unstored conversation/context;
- inferred occupation/relationship/finances;
- debug strings as personal facts;
- mutable server clock.

### 8.3 Typed internal fact

Conceptually:

```py
class PersonalFact:
    id: str
    kind: Literal["strength", "risk", "profile", "natal", "sphere"]
    statement_key: str
    confidence: float
    activation_ids: tuple[str, ...]
    natal_source_ids: tuple[str, ...]
    profile_source_ids: tuple[str, ...]
    sphere_keys: tuple[str, ...]
```

`id` stable and contains no raw values.

### 8.4 Natal strength/risk rules

Fact may be emitted only when:

- exact chart configuration exists in `NatalContextData`;
- corresponding allowlisted canon rule exists;
- confidence/strength threshold met;
- text does not overstate determinism;
- current horizon has thematic linkage to fact.

It is not enough that a generic planet is prominent.

### 8.5 Profile allowlist

Initial safe allowlist:

- user first name only for optional address, never provenance text;
- target/current timezone for date formatting;
- explicitly stored current/birth location only for calculation, not narrative;
- other profile fields only after separate product field exists and user supplied
  it intentionally.

Gender does not authorize stereotypes or relationship assumptions.

## 9. Deterministic guidance generation

Create:

```text
apps/api/app/services/horizon_guidance_service.py
```

It must produce a complete valid `TodayV2HorizonsBlock` without LLM.

### 9.1 Long horizon — what to rebuild

Required content:

- main life theme;
- real period dates;
- current state label such as `Фон уже действует`;
- one linked personal strength when available;
- one linked risk when available;
- 1-2 structural actions;
- 1-2 avoid actions;
- probable spheres;
- technical definitions for actual long techniques.

### 9.2 Medium horizon — what to try

Required content:

- real window;
- exact peak if present;
- state such as `Набирает силу`;
- 2-3 concrete reversible experiments;
- 1-3 avoid actions;
- probable spheres;
- explicit validity deadline;
- no drastic irreversible decision suggested from astrology alone.

### 9.3 Fast horizon — what to do today

Required content:

- short window;
- exact peak and whether passed/upcoming;
- one concrete step;
- one thing to postpone;
- when emotional/attention peak eases;
- no claim that emotion/event definitely occurs.

### 9.4 Example quality target

For a control/responsibility story, acceptable structure:

```text
Что это может значить именно для вас

Вы умеете выдерживать ответственность и сохранять порядок под давлением.
Но в ситуации неопределённости можете пытаться вернуть устойчивость через ещё
больший контроль.

Что попробовать до 18 июля

- Выписать обязанности, которые действительно ваши, и те, которые вы
  продолжаете выполнять по привычке.
- Если сейчас обсуждается роль или объём ответственности, обозначить одну
  конкретную границу: объём, деньги или условия договорённости.
- Изменить один элемент системы и проверить результат, не перестраивая всё.

Чего сейчас лучше не делать

- принимать крупное решение в эмоциональный пик;
- ставить ультиматум;
- брать новую ответственность только ради ощущения контроля.
```

Эта copy не hardcode для Basil. Она собирается только при соответствующих facts.

## 10. Tone aggregation

Create deterministic tone service/helper.

Inputs:

- selected activation polarities;
- weighted contributions;
- strength;
- convergence;
- sphere verdict consistency.

Output:

```text
supportive
neutral
tense
mixed
```

Rules live in canon and are unit-tested at boundaries.

Human labels:

```text
supportive -> Поддерживающий фон
neutral    -> Нейтральный фон
tense      -> Напряжённый фон
mixed      -> Смешанный фон
```

Frontend color/style uses enum, not text inspection.

## 11. Optional LLM refinement

LLM may improve Russian wording only after deterministic block exists.

### 11.1 Immutable facts

LLM cannot change:

- horizon IDs/order;
- activation/fact/sphere IDs;
- raw timing;
- timing state;
- tone;
- action intent/safety class;
- technique selection;
- conditional flags from unknown context.

It may rewrite only allowlisted text fields within semantic constraints.

### 11.2 Input minimization

Send:

- opaque IDs;
- deterministic statements;
- safe canon definitions;
- timing labels;
- allowed/forbidden claim list.

Do not send:

- raw Telegram initData;
- user ID;
- phone/email;
- exact coordinates;
- first/last name unless explicitly needed (initial implementation: do not send);
- session/auth data;
- unrestricted natal chart dump.

### 11.3 Structured response

Response validates against a dedicated Pydantic schema containing IDs and
rewritten text only. Reject:

- unknown/missing IDs;
- changed counts/order;
- new dates/numbers not present in input;
- unsupported profession/relationship/financial/medical claims;
- unconditional unknown context;
- missing provenance;
- astrology fatalism/certainty;
- contradictions with deterministic actions/sphere verdicts;
- empty/overlong copy.

### 11.4 Fallback

Provider timeout/error/invalid output:

- Today request succeeds;
- deterministic block returned;
- `guidance_mode="deterministic"`;
- safe structured rejection event;
- no raw prompt/response/PII in logs.

Valid refinement:

```text
guidance_mode="llm_refined"
```

No partial mixture: either full validated rewrite applied atomically or complete
deterministic block.

## 12. Claim validator

Extend/create:

```text
apps/api/app/services/horizon_claim_validator.py
```

It validates deterministic and LLM output.

Required checks:

- every claim has allowed kind/provenance;
- referenced IDs exist;
- all explicit dates originate from timing/profile input;
- unconditional real-life nouns are allowlisted;
- conditional context marker present when required;
- no forbidden high-stakes imperative;
- no guaranteed/fatalistic language;
- actions do not conflict across horizons;
- actions do not conflict with ConcreteAdvice verdict;
- strength/risk fact is thematically linked to horizon;
- technique explanation corresponds to actual selected technique.

Failure of deterministic generator is a programming error and must fail tests.
Failure of LLM output causes deterministic fallback.

## 13. API integration

### 13.1 Service flow

Refactor `SemanticV2Service` into orchestration; do not turn it into another
thousand-line service.

Recommended flow:

```text
ActivationLayer + ScoringV2Result + NatalContextData + profile allowlist
  -> HorizonTimingService
  -> HorizonSelectionService
  -> PersonalFactPackService
  -> HorizonGuidanceService deterministic
  -> optional LLM refinement
  -> HorizonClaimValidator
  -> TodayV2HorizonsBlock
  -> SemanticV2Service assembles TodayV2Block
```

### 13.2 Reuse existing data

`TodayService` already loads profile, natal context, activation layer and
scoring. Pass existing objects; do not:

- call sidecar again;
- query profile again;
- rebuild natal chart;
- recompute scoring;
- parse frontend fixture.

Add spy/call-count integration tests.

### 13.3 Cache identity

Cache must include/derive from:

- calculation version;
- activation layer version;
- scoring version;
- horizon selection canon version;
- horizon language/action/pattern canon versions;
- horizon guidance implementation version;
- prompt version when LLM path enabled;
- content version;
- profile hash;
- target date/timezone.

Bump `TODAY_CONTENT_VERSION` and the appropriate cache identity when real
horizons begin populating. Do not change calculation/scoring versions for copy.

Cached payload validates through `TodayPayload` before return.

### 13.4 Feature rollout

Use existing V2 flags. If a new specific flag is necessary, name explicitly,
default false, add settings/env docs/tests. Do not reuse dev fixture query as flag.

No DB migration unless cache schema physically requires it; JSON payload change
alone does not justify migration.

## 14. Logging

Register exact events before use in both registry locations where applicable.

Suggested events:

```text
today.horizons_selected
today.horizons_unavailable
today.guidance_built
today.guidance_refined
today.guidance_rejected
```

Every log meta includes exact `slice/module/block/correlation_id` per AGENTS.

Allowed fields:

- horizon IDs;
- technique families;
- counts;
- opaque activation IDs;
- version strings;
- fallback/rejection code;
- duration/latency.

Forbidden:

- raw narrative;
- raw profile/natal facts;
- exact birth/current coordinates;
- Telegram data/tokens/cookies;
- provider raw response.

Logger failures never break user flow.

## 15. Contract generation and compatibility

После Pydantic addition:

```bash
pnpm contracts:sync
```

Expected classification:

```text
additive compatible
```

Generated:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

Frontend imports public type/runtime barrels. Запрещено ручное Zod/TS
redeclaration новых wire shapes.

Add runtime tests:

- valid complete horizons parses;
- wrong item order rejected by API validator;
- missing provenance rejected;
- invalid tone/state rejected;
- timing contradiction rejected;
- unknown additive field remains rolling-deploy tolerant at frontend boundary;
- legacy `horizons=null/absent` parses.

## 16. Frontend migration

### 16.1 Consumer-first

Frontend first learns to render optional backend block. Existing
`selectWhyTimeHorizons(v2)` remains only as temporary legacy fallback when
`v2.horizons == null`.

When backend block exists, frontend must not call legacy selection for displayed
cards. Add spy/unit proof.

### 16.2 Components

Expected changes/new modules:

```text
components/today/why-expanded.tsx
components/today/why-time-horizon-card.tsx
components/today/horizon-actions.tsx
components/today/horizon-technique-disclosure.tsx
lib/presentation/today-v2.ts
lib/adapters/today-payload.ts
```

Keep components reasonably sized; extract repeated timing/provenance presentation.

### 16.3 Visual structure

Section:

```text
Почему это именно про меня

[dynamic eyebrow]
[dynamic headline]
[dynamic body]

[Долгий цикл · tone badge]
real range + state
plain meaning
strength/risk
where it may show
what to rebuild / avoid
[Как это рассчитано ▾]

[Текущий период · tone badge]
window + peak + state
what to try / avoid
[Как это рассчитано ▾]

[Быстрый trigger · tone badge]
short window + peak status
one step / postpone
[Как это рассчитано ▾]
```

Technical terms never dominate collapsed card.

### 16.4 12-sphere navigator

Preserve all 12 spheres as quick navigator.

Every sphere row remains clickable and visibly displays:

```text
Поддержка / Ровно / Внимание / Отложить
```

Horizon likely-sphere chips/buttons:

- use canonical sphere key;
- select corresponding navigator item;
- scroll/focus selected details accessibly;
- never invent a sphere label locally;
- preserve existing sphere verdict/tone, not horizon tone.

### 16.5 Semantic/test contract

Required stable selectors:

```text
data-testid="why-horizons"
data-state="ready|empty|error"

data-testid="why-horizon"
data-horizon="long|medium|fast"
data-status="supportive|neutral|tense|mixed"
data-timing-state="..."

data-testid="why-horizon-timing"
data-testid="why-horizon-strength"
data-testid="why-horizon-risk"
data-testid="why-horizon-actions"
data-testid="why-horizon-avoid"
data-testid="why-horizon-sphere"
data-testid="why-horizon-technical-toggle"
data-testid="why-horizon-technical-content"
```

Disclosure:

- real button;
- `aria-expanded`;
- `aria-controls`;
- associated region ID;
- keyboard operable;
- icon-only controls have `aria-label`.

Tone/status must be visible text, not color only.

### 16.6 Error/fallback

- `horizons=null`: legacy renderer during one migration version;
- malformed response: fetch boundary Zod rejects and existing error state, not
  partial unsafe render;
- individual optional strength/risk absent: omit its subsection without empty
  heading;
- empty actions invalid at API, never patched by frontend.

## 17. Preview and fixtures

### 17.1 Production data proof on 3003

Final preview must run on port `3003` and use real API/dev auth, not runtime
fixture:

```text
http://127.0.0.1:3003/day/2026-07-08?why=1
```

No `fixture=...` in the acceptance URL.

Canonical API remains port 8000; sidecar 18091. Do not start manual uvicorn.

### 17.2 Fixture role

Existing:

```text
/day/2026-07-08?fixture=three-horizon-timing&why=1
```

may remain dev/test visual harness, but:

- product modules do not import fixture data;
- production build tree-shakes/dev-guards it;
- real acceptance does not use it;
- Playwright route fixtures live in test harness;
- fixture contract is regenerated/validated from canonical JSON.

## 18. Backend tests

### 18.1 Timing/classification

- instant/date duration;
- boundary inclusivity;
- every timing state boundary;
- malformed/missing timing exclusion;
- preferred/fallback bands;
- target clock determinism;
- timezone/date-only behavior.

### 18.2 Selection

- coherent triple beats three stronger unrelated facts within documented weights;
- same-target/theme/sphere bonuses;
- family diversity;
- stable tie-break;
- low-impact evidence excluded;
- no valid triple -> null + reason;
- output order exactly long/medium/fast;
- repeated build byte-identical;
- corpus coverage gate.

### 18.3 Fact pack

- valid natal strength/risk emitted only on exact rule match;
- weak/unlinked natal fact omitted;
- unknown profile context conditional;
- profession/relationship/finance/medical assumption absent;
- opaque stable fact IDs;
- no PII in serialized/log packet.

### 18.4 Guidance

- three different stories yield different intro content;
- horizon-specific action counts/types;
- actions carry provenance;
- no duplicate/contradiction;
- every technique explanation actual;
- profection/firdar human explanation includes current personal meaning and dates;
- deterministic fallback complete without LLM.

### 18.5 LLM/validator

- valid rewrite accepted atomically;
- invented job rejected;
- invented partner/debt/event rejected;
- new date rejected;
- changed ID/tone/timing/action intent rejected;
- missing conditional marker rejected;
- provider failure deterministic fallback;
- no raw response/log leak.

### 18.6 Today integration

- real sidecar layer -> real horizons;
- no second sidecar/natal/scoring call;
- cache hit preserves payload;
- cache invalidates on horizon/content/canon/profile version;
- legacy flags/fallback correct;
- API model/generation roundtrip;
- audit versions included.

## 19. Frontend tests

### Unit/component

- generated type used;
- backend items rendered in exact order;
- legacy selector not called when horizons present;
- dynamic intro rendered;
- tones and visible labels;
- timing states/ranges/peak labels;
- actions/avoid sections;
- optional strength/risk behavior;
- technical disclosure a11y;
- sphere navigation and selected details;
- `data-testid/data-status/data-horizon/data-timing-state` contract;
- no raw `Transit_`/`Natal_` prefixes;
- no frontend astrology calculation/import.

### Browser/visual

Mobile 390px and representative desktop:

- all three cards;
- one technical disclosure opened;
- Work sphere selected from horizon link;
- long content without overflow;
- tone distinguishable by text and color;
- screenshot artifacts in wave docs.

Visual baselines should mask only genuinely dynamic text; structural status/timing
must remain asserted.

## 20. Real E2E

Required no-interception chain:

```text
Telegram HMAC initData
  -> /api/auth/telegram
  -> real /api/day/2026-07-08
  -> real sidecar 18091
  -> real API horizons
  -> frontend render
```

No `page.route('/api/**')`, no fixture query, no demo-data import.

Assertions:

- API `v2.horizons.schemaVersion == today-horizons.v1`;
- exactly three ordered items;
- timing/provenance valid;
- frontend testids/statuses match payload;
- technical disclosure works;
- 12 spheres remain;
- production auth unchanged.

## 21. Performance budgets

Measure separately:

```text
sidecar calculation
horizon selection/fact/guidance deterministic
LLM refinement (non-blocking/fallback policy)
full API day cache miss
cache hit
frontend build/render smoke
```

Targets:

- accepted S2.W1 sidecar p95 remains < 2000 ms;
- deterministic API horizon pipeline p95 < 100 ms excluding sidecar/LLM/DB;
- selection must not be quadratic over unbounded activations; bound candidate
  lists before triple combination;
- cached day does not call sidecar/LLM;
- LLM failure/timeout does not make payload unavailable.

Report 3 warmups + 20 measured runs for deterministic horizon service and full
representative in-process path where feasible.

## 22. Waves

## B1 — Additive public contract and consumer skeleton

### Scope

- Pydantic horizon models/validators;
- generated OpenAPI/TS/Zod;
- frontend optional rendering shell using supplied contract fixture;
- no production backend population;
- legacy fallback preserved;
- contract/runtime/component tests.

### Gates

```bash
pnpm contracts:sync
pnpm contracts:check
npx vitest run __tests__/contracts
npx vitest run __tests__/components/TodayScreen.v2-downstream.test.tsx
npx tsc --noEmit
cd apps/api && .venv/bin/python -m pytest tests/test_activation_contracts.py tests/test_today_v2_payload.py -q
git diff --check
```

### Callback

```text
READY_STAGE_B1_HORIZON_CONTRACT
compatibility: ADDITIVE
generated_types: PASS
generated_zod: PASS
validator_matrix: PASS
legacy_fallback: PASS
production_population: NONE
commit: NOT_YET
push: NOT_YET
```

## B2 — Deterministic selection and personal fact pack

### Scope

- canon schemas/files;
- timing classifier;
- selection service;
- coverage corpus;
- personal fact pack;
- deterministic guidance;
- claim validator;
- no LLM yet;
- focused/full API tests.

### Gates

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_coverage.py \
  tests/test_personal_fact_pack_service.py \
  tests/test_horizon_guidance_service.py \
  tests/test_horizon_claim_validator.py -q
.venv/bin/python -m pytest tests -q
git diff --check
```

### Callback

```text
READY_STAGE_B2_DETERMINISTIC_HORIZONS
coverage: <percent/cases>
coherence: PASS <goldens>
personal_facts: PASS
unsupported_claims: ZERO
guidance_without_llm: PASS
api_full: <result>
benchmark: <result>
commit: NOT_YET
push: NOT_YET
```

## B3 — API population, cache and optional LLM refinement

### Scope

- TodayService/SemanticV2 integration;
- reuse existing objects/call-count proof;
- optional LLM rewriter;
- strict rejection/fallback;
- logs/registry;
- cache/content/canon identity;
- real API payload tests.

### Gates

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_today_v2_payload.py \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_horizon_llm_refinement.py \
  tests/test_pipeline_invariants.py -q
.venv/bin/python -m pytest tests -q
cd ../..
pnpm contracts:check
python scripts/check_logging_guardrails.py
git diff --check
```

Required real JSON excerpt redacts user identity and shows:

- intro;
- 3 horizon IDs/tones/timing;
- sample provenance IDs;
- actions/avoid;
- guidance mode;
- audit/cache versions.

### Callback

```text
READY_STAGE_B3_REAL_API_HORIZONS
real_payload: PASS
reuse_call_counts: PASS
cache_identity: PASS
llm_valid: PASS
llm_rejection_fallback: PASS
pii_log_audit: PASS
api_full: <result>
commit: NOT_YET
push: NOT_YET
```

## B4 — Real frontend and preview 3003

### Scope

- render backend-owned block;
- legacy fallback only on null;
- all human-first content/actions/technical disclosures;
- clickable sphere links;
- a11y/test contract;
- real API preview on 3003;
- fixture retained only test/dev.

### Gates

```bash
npx vitest run __tests__/components __tests__/lib/presentation __tests__/contracts
npx tsc --noEmit
E2E_BASE_URL=http://127.0.0.1:3003 \
  npx playwright test <new-real-horizon-preview-specs> --project=mobile
NEXT_DIST_DIR=.next-stage-b4-proof pnpm build
git diff --check
curl -fsS -o /dev/null -w '%{http_code}\n' \
  'http://127.0.0.1:3003/day/2026-07-08?why=1'
```

Acceptance URL cannot contain `fixture=`.

### Visual evidence

- full mobile section;
- long card technical disclosure open;
- medium actions visible;
- fast peak status visible;
- sphere clicked/expanded;
- desktop layout.

### Callback

```text
READY_STAGE_B4_REAL_FRONTEND
real_url: http://127.0.0.1:3003/day/2026-07-08?why=1
fixture_dependency: NO
backend_horizons_rendered: PASS
legacy_selector_bypassed: PASS
accessibility: PASS
screenshots: <paths>
vitest: <result>
playwright: <result>
build: PASS
commit: NOT_YET
push: NOT_YET
```

## B5 — Full end-to-end release candidate

### Scope

- all review corrections;
- full tests/build;
- real Telegram HMAC E2E;
- performance/security/contract audit;
- clean feature branch candidate;
- no main/deploy yet.

### Gates

```bash
pnpm install --frozen-lockfile
pnpm contracts:sync
pnpm contracts:check
npx vitest run
npx tsc --noEmit
(
  cd apps/solarsage
  venv/bin/python -m pytest tests -q
)
(
  cd apps/api
  .venv/bin/python -m pytest tests -q
)
E2E_BASE_URL=http://127.0.0.1:3003 npx playwright test <real-no-interception-spec>
NEXT_DIST_DIR=.next-stage-b5-rc pnpm build
pnpm guardrails:prod
pnpm guardrails:contracts
python scripts/check_logging_guardrails.py
git diff --check
git status --short
git diff --cached --stat
```

### Callback

```text
READY_STAGE_B_FOR_MAIN_RELEASE
branch: <branch>
head: <sha>
origin_feature: <sha after accepted commits>
real_three_horizons: PASS
grounded_claims: PASS
unsupported_claims: ZERO
real_api_preview: PASS
telegram_real_e2e: PASS
contract_compat: PASS
sidecar_full: <result>
api_full: <result>
frontend_full: <result>
playwright: <result>
performance: <results>
build: PASS
security/log audit: PASS
worktree: CLEAN
```

После architect acceptance перейти только по отдельной команде к existing
`90_MAIN_RELEASE_DEPLOY_TZ.md` с amendments из Stage A package installation.

## 23. Commit discipline

No commit/push before architect acceptance each wave.

Suggested commits:

```text
feat(today): add grounded three-horizon response contract
feat(today): select coherent personal horizons deterministically
feat(today): build grounded horizon guidance and safe refinement
feat(today): render backend-owned personal horizons
test(today): prove real horizon pipeline end to end
```

Generated artifacts committed with owning Pydantic change.

## 24. Final production release

Final outcome is not feature-branch preview. After B5 acceptance:

1. Execute reviewed main preflight.
2. Merge feature branch into `main` without force/reset.
3. Push `origin/main` and prove SHA equality.
4. Build/install same shared contract wheel in both Python venvs.
5. Run migrations only if actual migration exists.
6. Build Next release candidate in isolated dist.
7. Restart in safe order:
   - sidecar;
   - API;
   - frontend;
   - nginx only if config changed (expected: no).
8. Verify canonical ports 18091/8000/3002/80/443.
9. Run real Telegram HMAC production E2E without interception/fixture.
10. Verify production Today payload/UI and logs.
11. Preserve rollback SHA/build/wheel/env backup.

No manual uvicorn, no API on 8001, no `USE_FIXTURES`, no production runtime
mock.

## 25. Definition of done

Program is complete only when authoritative evidence proves:

```text
real sidecar timings
  -> shared Python contract validation
  -> real API coherent horizon selection
  -> grounded personal fact/action provenance
  -> generated public contract
  -> frontend backend-owned rendering
  -> real auth/API E2E
  -> full test/build/security/performance gates
  -> accepted commits in origin/main
  -> canonical systemd production deploy
  -> production smoke and rollback proof
```

Красивый fixture, локальный 3003, passed focused tests или feature branch push
по отдельности не являются завершением задачи.
