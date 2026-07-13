# Stage B2B — decomposition, ownership and invariant freeze

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Принятый B2A HEAD/origin: `cd27d1a8056eef92737e992c1b0998423331734b`
Parent scope: `50_STAGE_B_REAL_HORIZONS_ACTIONS_FRONTEND_TZ.md`, B2
Wave plan: `51_STAGE_B_AND_MAIN_RELEASE_WAVE_PLAN.md`
Статус: **ARCHITECTURE FREEZE FOR B2B EXECUTION**

## 0. Решение

B2B выполняется двумя отдельными implementation/review подволнами:

```text
B2B1
  versioned language/action/personal-pattern canons
  -> strict typed loaders and cross-canon validation
  -> deterministic personal fact pack
  -> deterministic machine tone

B2B2
  accepted B2A selection + accepted B2B1 facts/tone
  -> complete deterministic TodayV2HorizonsBlock
  -> claim validator
  -> deterministic synthetic coverage corpus
  -> <100 ms end-to-end deterministic horizon benchmark
```

Причина разделения: до генерации русского пользовательского текста необходимо
отдельно доказать, что каждый personal strength/risk действительно следует из
конкретной натальной конфигурации, связан с выбранной темой и не использует PII,
debug или прежний LLM-текст.

Кодер реализует. Архитектор пишет ТЗ и проводит самостоятельное ревью. Субагенты
не используются. Commit/push каждой подволны запрещён до отдельного architect
acceptance document.

## 1. B2B1 — content canons, fact pack and tone

### 1.1 Входит

- `horizon_language.ru.v1`;
- `horizon_actions.ru.v1`;
- `personal_patterns.ru.v1`;
- strict Pydantic schemas для всех трёх canon files;
- один fail-fast cached content-canon loader с cross-file validation;
- отдельная content-canon version map, пока не включённая в Today cache/audit;
- strict internal personal-fact models;
- deterministic extraction только из accepted B2A anchors, activation-linked
  scoring contributions и exact `NatalContextData` fields;
- finite allowlisted natal predicate DSL без `eval` и arbitrary expressions;
- deterministic per-horizon tone assessment from polarity, B2A features and an
  explicit product-sphere verdict map;
- focused unit tests, privacy sentinels and full API baseline comparison.

### 1.2 Не входит

- построение `TodayV2HorizonsBlock`;
- human timing labels formatting at runtime;
- actions/manifestations selection into public models;
- `HorizonClaimValidator`;
- coverage corpus;
- Today/Semantic/Calendar integration;
- public OpenAPI/TypeScript/Zod change;
- frontend/sidecar change;
- LLM;
- cache/content/version/log event changes;
- DB, migration, env, systemd, nginx or ports.

### 1.3 Acceptance boundary

B2B1 accepted только если:

```text
all three canon files strict-load and cross-validate
unknown/missing/extra canon data fails, no fallback
all selected personal facts have exact typed provenance
generic dominant/top_signal alone never creates strength/risk
three golden natal configurations produce different fact packs
weak, absent or thematically unlinked configurations produce no claim
serialized fact pack contains no raw evidence/debug/profile/natal values
tone boundary and contradiction matrix passes
public contracts and production behavior unchanged
```

Owning implementation ТЗ: `64_STAGE_B2B1_CONTENT_CANONS_FACT_PACK_TONE_TZ.md`.

## 2. B2B2 — deterministic guidance, validation and coverage

### 2.1 Входит

- `HorizonGuidanceService`, pure and deterministic;
- complete contract-valid `TodayV2HorizonsBlock` without LLM;
- dynamic theme intro rather than one universal phrase;
- real B2A timing values rendered into Russian labels using target timezone;
- technique explanations for every selected actual technique;
- horizon-specific actions/avoids from accepted action canon;
- manifestations and likely 12-sphere links;
- optional strength/risk only from accepted PersonalFactPack;
- deterministic claim validator over all output claims;
- cross-horizon intent conflict checks;
- compatibility checks against supplied 12-sphere verdict map;
- synthetic coverage corpus and benchmark.

### 2.2 Не входит

- Today/Semantic production population;
- second sidecar/profile/natal/scoring call;
- cache identity or content version bump;
- LLM refinement;
- frontend production rendering;
- real authenticated browser acceptance.

### 2.3 Acceptance boundary

```text
three substantially different stories -> three different intros/copy
long/medium/fast action counts exactly satisfy B1 contract
all output IDs/provenance/date/technique references validate
unsupported real-life claims: zero
deterministic generator passes claim validator atomically
coverage >=95% on agreed synthetic corpus
100% selected triples have complete timing/provenance
0 candidates below accepted B2A thresholds
deterministic selection+facts+tone+guidance+validation p95 <100 ms
public production population remains absent until B3
```

Owning implementation ТЗ будет написано только после architect acceptance B2B1.

## 3. Frozen data ownership

### 3.1 Selection facts

B2A `SelectedHorizonTriple` is immutable input. B2B may not:

- change anchor identity;
- replace a weak/missing horizon;
- recompute selection with different thresholds;
- use a non-selected activation as hidden primary evidence;
- use `ActivationEvidence.evidence` or `.debug` as personal prose.

### 3.2 Natal facts

Initial v1 strength/risk matching may inspect only:

```text
NatalContextData.planets: name, sign, house
NatalContextData.aspects: planet_a, planet_b, aspect_type, orb
```

It may not use as sufficient evidence:

```text
dominants
top_signals
sphere_scores
elements_balance
modalities_balance
planet longitude/degree
house cusp longitude/degree
special points
```

These fields remain available for future separately reviewed rules, but are not
authorized personal-pattern evidence in v1. In particular, a generic prominent
Saturn, Moon or Pluto is not a talent/risk statement.

### 3.3 Scoring facts

Only `SphereContribution` rows with:

```text
source == activation
source_id == selected anchor activation_id
finite non-zero amount
```

may ground selected sphere facts. `ScoringV2Result.debug`, human `evidence`
strings, convergence debug and unrelated base signals are prohibited.

### 3.4 Profile facts

B2B1 does not need or accept the ORM `UserProfile` and emits no profile claim.
Target timezone already exists in `ActivationLayer` and is used later for
timing formatting. First name may be added by B3 only as an optional form of
address, never as provenance. Gender, city, coordinates and birth date/time do
not authorize narrative claims.

## 4. Frozen personalization semantics

Every personal fact has:

```text
stable opaque fact id without raw values
kind
statement key from language canon
confidence in 0..1
canonical linked horizon ids
linked theme keys
selected activation ids
natal source ids and/or profile source ids
product sphere keys
```

Strength/risk is emitted only when all conditions hold:

1. every canon predicate matches exact cached natal fields;
2. computed confidence meets the canon rule threshold;
3. rule theme intersects at least one selected anchor theme;
4. rule sphere set intersects that anchor product-sphere set;
5. all source IDs are generic structural IDs, not raw values;
6. statement key exists and its declared kind matches the fact kind.

Absence of a match is normal. The service omits the personal strength/risk; it
does not substitute generic flattering or alarming text.

## 5. Frozen tone semantics

Tone is not inferred from Russian text and is not the existing 12-sphere
verdict. It is an independent per-horizon enum:

```text
supportive | neutral | tense | mixed
```

Inputs are limited to:

- selected anchor polarity;
- accepted B2A strength/contribution/convergence/impact features;
- explicit product-sphere verdicts supplied by the caller.

Missing sphere verdicts are neutral evidence, not guessed. Directly opposing
material activation and sphere evidence produces `mixed`, not whichever side
wins by one rounding unit. All weights/thresholds live in language canon.

## 6. Contract and release boundary

B2B internal schemas are not added to public schema barrels or contract
registry. B2B1/B2B2 must produce:

```text
pnpm contracts:check -> no generated/public diff
TodayV2Block.horizons production population -> still absent
get_canon_versions() -> unchanged until B3 cache/audit integration
```

The three new canon versions are exposed only by a dedicated internal helper.
B3 will explicitly add accepted versions to cache/audit identity.

## 7. Review lifecycle

For each B2B subwave:

```text
architect implementation TZ
  -> coder implements without commit/push
  -> coder callback in tmux
  -> architect reads every diff and reruns gates
  -> one or more correction TZs if required
  -> architect acceptance + exact scoped commit/push TZ
  -> coder commit/push
  -> architect verifies origin SHA and clean tracked tree
```

Known unrelated untracked paths remain untouched:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```
