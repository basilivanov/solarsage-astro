---
id: doc-15-solarsage-v2-activation-audit-tz
status: planned
wave: W-SOLARSAGE-V2
created_at: 2026-07-08
source_docs:
  - docs/14_SolarSage_scoring_rewrite_TZ.md
  - docs/11_SolarSage_rewrite_TZ.md
source_audit:
  - artifacts/audit/2026-07-08/
owner: SolarSage
---

# ТЗ: SolarSage V2 — независимый аудит, activation layer, scoring v2 и explainable frontend

Версия: 1.0

Этот документ описывает не один фикс, а **полную дорожную карту внедрения SolarSage V2**: сначала независимый аудит и baseline, затем доверительные исправления текущего production, затем deterministic `activation_layer`, затем scoring v2, затем API/кэш/семантика/фронт, затем доказательная база и rollout.

Документ дополняет `docs/14_SolarSage_scoring_rewrite_TZ.md`. Doc-14 описывает целевой алгоритмический рерайт scoring. Этот документ раскладывает его по волнам, контрактам, файлам, артефактам, тестам, audit gates и frontend-поведению.

---

## 0. Executive summary

### 0.1. Текущее состояние после независимого аудита 2026-07-08

Аудит кейса Basil на `2026-07-08 12:00 Europe/Moscow` показал:

1. **Текущий production scoring воспроизводим.** Independent scoring oracle совпал с production по:
   - `day_status`;
   - всем `sphere_scores`;
   - `top_signals`;
   - допуск `0.00` на проверенном кейсе.

2. **Текущий день `supportive` объясним текущей логикой.**
   - positive score: `7.3468`;
   - negative score: `4.9252`;
   - ratio: `1.4917`;
   - threshold production: `positive > negative * 1.3 && positive >= 1.0`;
   - значит `supportive` корректен в рамках текущего scoring.

3. **Текущий production не является полноценным SolarSage V2 из doc-14.**
   - нет `derived.activation_layer`;
   - `TodayPayload.activation_evidence = null`;
   - `technique = null`, `technique_family = null`;
   - profection / firdar / solar return / solar arc / progressions / lot / angle / eclipse не участвуют в scoring;
   - convergence в аудируемом кейсе равен нулю;
   - версии payload остаются старые: `scoring_version=1`, `activation_layer_version=null`, `scoring_canon_version=null`.

4. Найдены trust-баги, которые надо закрыть до V2:
   - raw `retrograde=false` неверен для Mercury, Neptune, Pluto;
   - Moon phase `46%` расходится с oracle `43.792%`;
   - UI-label `Moon opposite Pluto` скрывает важное различие: это `Transit Moon opposite natal Pluto`, а не `Transit Moon opposite Transit Pluto`;
   - `WhyThisHappens` местами использует static natal house signals как day evidence;
   - практический совет может противоречить verdict строки, например relationships=`avoid`, но советовать relationship outreach.

### 0.2. Главный принцип внедрения

**Сначала audit harness и baseline. Потом V2. Не наоборот.**

Без baseline невозможно понять, изменилась картинка потому что V2 стал умнее, или потому что мы сломали текущую математику.

Правильная последовательность:

```text
W0: Independent audit harness + P0 trust fixes
W1: Contracts, canon, versioning skeleton
W2: Activation layer infrastructure
W3: Techniques implementation, по одной семье техник
W4: Scoring v2 + convergence + anti-dominance
W5: API/cache integration + dual-run
W6: Semantic/LLM evidence + frontend V2
W7: CI, golden snapshots, rollout gates
```

---

## 1. Goals / Non-goals

### 1.1. Goals

1. Создать воспроизводимый независимый audit harness:
   - production collector;
   - independent astronomical oracle;
   - independent scoring oracle;
   - golden snapshots;
   - audit report generator;
   - CI gates.

2. Закрыть P0 trust-баги текущего production:
   - retrograde flags;
   - Moon phase formula;
   - transit-to-natal labels;
   - separation of day evidence vs natal background;
   - advice consistency.

3. Реализовать deterministic `activation_layer` как отдельный слой между raw astrology и scoring:
   - `by_planet`;
   - `by_house`;
   - `by_lot`;
   - `by_angle`;
   - flat `activations[]`;
   - версии;
   - traceability.

4. Реализовать техники V2:
   - `transit_to_natal`;
   - `transit_to_angle`;
   - `transit_to_lot`;
   - `annual_profection`;
   - `monthly_profection`;
   - `firdar_major`;
   - `firdar_minor`;
   - `solar_return`;
   - `lunar_return`;
   - `solar_arc`;
   - `secondary_progression`;
   - `eclipse_window`.

5. Переписать convergence на основе independent technique families, а не на основе generic `AstroSignal.type`.

6. Обновить API contracts:
   - versioned meta;
   - activation evidence;
   - scoring breakdown;
   - explainability contracts;
   - cache invalidation rules.

7. Обновить frontend:
   - показывать не только итоговый verdict, но и «почему именно сегодня»;
   - различать transit-to-natal и transit-to-transit;
   - показывать technique chips;
   - не делать client-side astrology;
   - иметь debug/audit view для dev/admin.

8. Доказать корректность:
   - tests;
   - audit artifacts;
   - oracle comparison;
   - golden snapshot;
   - performance benchmark;
   - migration dual-run.

### 1.2. Non-goals

1. Не доказываем, что астрология «объективно работает».
2. Не меняем продуктовую философию текста без отдельного ТЗ.
3. Не переносим LLM в sidecar.
4. Не делаем frontend calculator.
5. Не добавляем Vedic/varga/ashtakavarga в этот scope.
6. Не ломаем текущий wire contract без compatibility layer.
7. Не включаем V2 для всех пользователей без dual-run и audit diff.

---

## 2. Термины

### 2.1. Raw astrology

Сырые расчёты:

- планеты;
- долготы;
- скорости;
- знаки;
- дома;
- аспекты;
- лоты;
- углы;
- возвращения;
- прогрессии;
- profection/firdar periods.

Raw astrology не должна принимать продуктовых решений.

### 2.2. AstroSignal

Нормализованный сигнал, пригодный для scoring. Сейчас используется в API. В V2 должен быть расширен или дополнен activation artifacts.

### 2.3. Activation

Один факт вида:

> такая-то техника на target date активирует такую-то планету / дом / лот / угол.

Примеры:

```text
annual_profection activates house 3
annual_profection activates Mercury as lord_of_year
transit_to_natal activates natal Pluto by Transit Moon opposition orb 1.04°
solar_return activates house 10 because SR Moon is in natal 10th
secondary_progression activates natal Mercury by progressed Moon square natal Mercury orb 0.7°
```

### 2.4. Activation layer

Deterministic artifact:

```text
raw natal + raw period + raw day
→ activation_layer
→ scoring v2
→ semantic layer
→ LLM text
```

Он должен быть кэшируемым, версионированным и audit-friendly.

### 2.5. Technique family

Группа техник, которые не должны считаться независимыми дважды.

Пример:

```yaml
technique_families:
  profection:
    - annual_profection
    - monthly_profection
  firdar:
    - firdar_major
    - firdar_minor
  progression:
    - secondary_progression
    - solar_arc
  transit:
    - transit_to_natal
    - transit_to_angle
    - transit_to_lot
```

Если annual и monthly profection обе указывают на Mercury, это может усилить evidence внутри семьи, но для convergence families это не две полностью независимые техники.

### 2.6. Convergence

Сходимость независимых technique families на одну планету/дом/лот/угол или сферу.

V2 scoring должен уметь отвечать:

```text
Почему documents сегодня green?
Потому что:
- transit family активирует Saturn через Transit Mars trine natal Saturn;
- profection family активирует 3 дом / Mercury;
- solar_return family активирует 3/9 axis;
- поэтому documents/communication получает convergence bonus.
```

---

## 3. Целевая архитектура

### 3.1. Высокоуровневый pipeline V2

```text
Frontend request /day/:date
  ↓
API TodayService
  ↓
NatalContextService
  - cached natal context
  - profile hash
  ↓
SolarSage sidecar
  - /v1/transits
  - /v1/activation-layer
  - optionally /v1/period-context
  ↓
NormalizationService
  - day signals
  - typed technique markers
  ↓
ActivationLayerService
  - validates/merges sidecar activations
  - builds API-native activation layer if needed
  ↓
ScoringServiceV2
  - base scores
  - activation contributions
  - convergence bonus
  - anti-dominance
  - day_status
  - top_signals
  - score breakdown
  ↓
SemanticServiceV2
  - deterministic why contexts
  - product row evidence
  - no contradictions
  ↓
LLMService
  - text only from evidence
  - claim guard
  ↓
TodayPayload V2
  ↓
Frontend
  - summary
  - spheres
  - concrete advice
  - why exactly today
  - technique evidence chips
  - dev audit drawer
```

### 3.2. Ownership boundaries

#### Sidecar owns

- Swiss Ephemeris calculations;
- planet positions;
- speeds and retrograde;
- houses and angles;
- lots;
- solar return chart;
- lunar return chart;
- solar arc positions;
- secondary progressions;
- eclipse proximity;
- exact aspect/orb computations that require ephemerides;
- raw activation extraction where calculations are astronomy-heavy.

#### API owns

- user/profile/cache access;
- normalization to product schemas;
- canon loading for product scoring;
- scoring v2;
- semantic layer;
- LLM prompting and validation;
- final TodayPayload;
- audit collection orchestration;
- version invalidation.

#### Frontend owns

- rendering;
- user-friendly labels;
- evidence chips;
- expand/collapse;
- debug display when enabled;
- no astrology calculation.

---

## 4. Wave W0 — Independent audit harness + P0 trust fixes

### 4.1. Цель

Закрепить текущий production как проверяемую baseline-точку до V2.

### 4.2. Что уже есть из audit report

Аудит добавил/описал:

```text
scripts/audit_today.py
scripts/audit_scoring_oracle.py
scripts/audit_astronomy_oracle.py
scripts/test_audit_scoring_oracle.py
artifacts/audit/2026-07-08/
```

Эти артефакты надо довести до постоянного dev-flow.

### 4.3. Required commands

Добавить Makefile-команды:

```makefile
.PHONY: audit-day
audit-day:
	apps/api/.venv/bin/python scripts/audit_today.py \
		--user-id $(USER_ID) \
		--date $(DATE) \
		--out artifacts/audit/$(DATE)
	apps/api/.venv/bin/python scripts/audit_scoring_oracle.py \
		--signal-trace artifacts/audit/$(DATE)/signal_trace.csv \
		--production artifacts/audit/$(DATE)/final_today_payload.json \
		--out artifacts/audit/$(DATE)/scoring_oracle_comparison.json
	apps/api/.venv/bin/python scripts/audit_astronomy_oracle.py \
		--audit-dir artifacts/audit/$(DATE) \
		--out artifacts/audit/$(DATE)/astronomy_oracle_summary.json
```

Вызов:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

### 4.4. Required audit artifact tree

```text
artifacts/audit/<date>/
  00_input_profile.json
  01_raw_natal_context.json
  02_raw_transits.json
  03_normalized_signals_all.json
  04_day_scored_signals_after_filter.csv
  05_signal_trace.csv
  06_scoring_intermediate_table.csv
  07_sphere_scores.csv
  08_top_signals.csv
  09_semantic_layer.json
  10_why_contexts.json
  11_final_today_payload.json
  12_scoring_oracle_comparison.json
  13_astronomy_oracle_summary.json
  14_claims_audit.md
  15_audit_summary.md
```

### 4.5. P0 trust fixes

#### 4.5.1. Retrograde flags

Files:

```text
apps/solarsage/solarsage/schemas/natal.py
apps/solarsage/solarsage/utils/ephemeris.py
apps/solarsage/solarsage/api/transits.py
apps/solarsage/solarsage/api/natal.py
apps/api/app/schemas/natal.py
```

Requirements:

- Planet response must include `speed_longitude` or equivalent speed field.
- `retrograde = speed_longitude < 0`.
- API must not mask missing retrograde as `false`.
- If sidecar omitted retrograde, API should either:
  - derive from speed, if speed exists;
  - or fail loudly in dev/test;
  - never silently default to false in audited paths.

Tests:

```text
apps/api/tests/test_astronomy_oracle.py::test_retrograde_flags_2026_07_08
apps/solarsage/tests/test_ephemeris_retrograde.py
```

Expected for 2026-07-08:

```text
Mercury retrograde = true
Neptune retrograde = true
Pluto retrograde = true
```

#### 4.5.2. Moon phase formula

File:

```text
apps/api/app/services/today_interpretation_service.py
```

Replace approximate triangular formula with illumination:

```text
illumination_pct = (1 - cos(radians(moon_lon - sun_lon))) / 2 * 100
```

Requirements:

- normalize angle to 0..360 before formula;
- output rounded consistently with UI needs;
- audit artifact stores exact raw value and displayed value.

Tests:

```text
apps/api/tests/test_astronomy_oracle.py::test_moon_phase_illumination_2026_07_08
```

Expected:

```text
oracle ≈ 43.792%
production tolerance <= 0.5 percentage points
```

#### 4.5.3. Transit-to-natal labels

Requirement:

Every aspect evidence must explicitly state target frame:

```text
Transit Moon opposition natal Pluto
Transit Moon opposition Transit Pluto
Natal Moon opposition Natal Pluto
Progressed Moon square natal Mercury
Solar Arc Mars conjunct natal MC
```

Never show ambiguous `Moon opposition Pluto` in debug/evidence contexts.

UI may have short labels, but expanded evidence must show exact frame.

#### 4.5.4. Day evidence vs natal background

Files:

```text
apps/api/app/services/semantic_service.py
apps/api/app/services/today_service.py
apps/api/app/services/day_scoring_signals.py
```

Requirements:

- `build_why_contexts` must receive separately:

```python
all_signals: list[AstroSignal]
day_scored_signals: list[AstroSignal]
natal_background_signals: list[AstroSignal]
activation_layer: ActivationLayer | None
```

- Daily/manifestation contexts must use `day_scored_signals` and `activation_layer`.
- Natal background sections may use natal signals, but must label them as natal baseline, not current-day manifestation.

Tests:

```text
apps/api/tests/test_semantic_contexts.py::test_manifestation_zones_do_not_use_static_natal_houses_as_day_evidence
```

#### 4.5.5. Advice consistency guard

Files:

```text
apps/api/app/services/today_interpretation_service.py
apps/api/app/services/llm_service.py
apps/api/app/services/semantic_service.py
```

Rules:

- If row verdict is `avoid`, generated advice cannot recommend direct positive action in that same domain unless evidence includes a safe mitigation.
- If relationships=`avoid`, do not say `общайся с близкими для улучшения отношений`.
- Allowed version:

```text
Если нужно общаться с близкими — выбирай короткий, спокойный формат и не разбирай острые темы.
```

Tests:

```text
apps/api/tests/test_today_concrete_advice_consistency.py
```

### 4.6. W0 DoD

W0 done only if:

- `make audit-day USER_ID=... DATE=2026-07-08` succeeds locally;
- generated artifacts are deterministic except timestamps;
- scoring oracle equals production ±0.02;
- astronomy oracle passes retrograde and Moon phase;
- P0 trust tests pass;
- `docs/audits/README.md` explains how to run audit;
- no V2 activation logic was introduced yet.

---

## 5. Wave W1 — Contracts, canon, versioning skeleton

### 5.1. Цель

Подготовить typed contracts до реализации техник. Без этого V2 расползётся по ad-hoc dict.

### 5.2. New schemas

Create:

```text
apps/api/app/schemas/activation.py
apps/api/app/schemas/scoring_v2.py
apps/solarsage/solarsage/schemas/activation.py
```

### 5.3. Activation schema — API canonical

```python
from typing import Literal
from pydantic import BaseModel, Field

ActivationTargetType = Literal[
    "planet",
    "house",
    "lot",
    "angle",
    "sphere",
]

ActivationPolarity = Literal[
    "supportive",
    "tense",
    "mixed",
    "neutral",
]

ActivationPhase = Literal[
    "applying",
    "exact",
    "separating",
    "background",
    "period",
]

class ActivationEvidence(BaseModel):
    id: str
    technique: str
    technique_family: str
    target_type: ActivationTargetType
    target_key: str
    kind: str
    active: bool = True

    source_planet: str | None = None
    source_frame: str | None = None   # transit, natal, progressed, solar_arc, solar_return
    target_planet: str | None = None
    target_frame: str | None = None   # natal, transit, angle, lot

    aspect: str | None = None
    orb: float | None = None
    applying: bool | None = None
    exact_at: str | None = None
    phase: ActivationPhase = "background"

    house: int | None = None
    lot: str | None = None
    angle: str | None = None

    strength: float = Field(ge=0.0, le=1.0)
    polarity: ActivationPolarity = "neutral"
    weight_hint: float | None = None

    evidence: str
    debug: dict = Field(default_factory=dict)

class ActivationLayer(BaseModel):
    schema_version: str = "activation-layer.v1"
    activation_layer_version: str = "al-1.0"
    calculation_version: str
    target_date: str
    target_time: str
    target_tz: str
    house_system: str

    activations: list[ActivationEvidence]
    by_planet: dict[str, list[str]]
    by_house: dict[str, list[str]]
    by_lot: dict[str, list[str]]
    by_angle: dict[str, list[str]]

    warnings: list[str] = Field(default_factory=list)
```

Important:

- `by_planet` maps `MERCURY -> [activation_id, ...]`, not embedded duplicated objects.
- `activations[]` is the source of truth.
- Every activation must have stable `id`.
- `evidence` is deterministic, not LLM text.

### 5.4. Scoring V2 schema

```python
class SphereContribution(BaseModel):
    sphere: str
    source: Literal["base_signal", "activation", "convergence", "cap"]
    source_id: str
    amount: float
    before: float | None = None
    after: float | None = None
    evidence: str

class SphereScoreV2(BaseModel):
    key: str
    title: str
    base_score: float
    activation_score: float
    convergence_bonus: float
    raw_score: float
    final_score: float
    normalized_score: float | None = None
    dominance_capped: bool = False
    contributions: list[SphereContribution]

class ScoringV2Result(BaseModel):
    scoring_version: str = "ss-scoring-2.0"
    canon_versions: dict[str, str]
    day_status: str
    status_breakdown: dict
    sphere_scores: dict[str, SphereScoreV2]
    top_signals: list[dict]
    top_activations: list[ActivationEvidence]
    debug: dict
```

### 5.5. Canon files

Required canon structure:

```text
grace/canon/spheres.v1.yml
grace/canon/dignities.v1.yml
grace/canon/aspect_rules.v1.yml
grace/canon/activation_rules.v1.yml
grace/canon/scoring_v2.v1.yml
```

`activation_rules.v1.yml` must not be dead data. It must be loaded in production.

Example keys:

```yaml
schema_version: activation_rules.v1
technique_families:
  transit:
    members: [transit_to_natal, transit_to_angle, transit_to_lot]
    independence_weight: 1.0
  profection:
    members: [annual_profection, monthly_profection]
    independence_weight: 0.8
  firdar:
    members: [firdar_major, firdar_minor]
    independence_weight: 0.8
  return:
    members: [solar_return, lunar_return]
    independence_weight: 0.9
  progression:
    members: [secondary_progression, solar_arc]
    independence_weight: 1.0
  eclipse:
    members: [eclipse_window]
    independence_weight: 0.7

activation_strength:
  exact_orb_curve:
    0.0: 1.0
    0.5: 0.85
    1.0: 0.70
    2.0: 0.45
  period_base:
    annual_profection: 0.75
    monthly_profection: 0.45
    firdar_major: 0.65
    firdar_minor: 0.40
```

### 5.6. Versioning requirements

`TodayMeta` must include:

```json
{
  "calculation_version": "ss-calc-1.1.0",
  "scoring_version": "ss-scoring-2.0",
  "activation_layer_version": "al-1.0",
  "canon_versions": {
    "spheres": "v1",
    "dignities": "v1",
    "aspect_rules": "v1",
    "activation_rules": "v1",
    "scoring_v2": "v1"
  },
  "audit_trace_id": "optional"
}
```

Cache invalidation:

| Change | Invalidate NatalContext | Invalidate ActivationLayer | Invalidate Semantic/Today |
|---|---:|---:|---:|
| birth profile | yes | yes | yes |
| calculation_version | yes | yes | yes |
| activation_layer_version | no | yes | yes |
| scoring_version | no | no | yes |
| canon spheres | no | no | yes |
| canon activation_rules | no | yes | yes |
| LLM prompt version | no | no | yes |

### 5.7. W1 DoD

- schemas exist;
- mypy/pyright or test import passes;
- canon loader validates JSONSchema/YAML;
- invalid canon fails loudly at service start in dev/test;
- meta version fields added without changing behavior;
- existing tests remain green;
- no V2 scoring behavior enabled yet.

---

## 6. Wave W2 — Activation layer infrastructure

### 6.1. Цель

Создать слой `ActivationLayerService`, который пока может собирать только существующие day signals, но уже выдаёт правильный контракт.

### 6.2. New files

```text
apps/api/app/services/activation_layer_service.py
apps/api/tests/test_activation_layer_contract.py
apps/api/tests/fixtures/activation_layer_minimal.json
apps/solarsage/solarsage/api/activation_layer.py
apps/solarsage/solarsage/services/activation_builder.py
apps/solarsage/tests/test_activation_layer_endpoint.py
```

### 6.3. API service responsibilities

`ActivationLayerService.build(...)`:

```python
class ActivationLayerService:
    def build(
        self,
        *,
        natal_context: dict,
        transits: dict,
        day_signals: list[AstroSignal],
        target_date: date,
        target_time: str,
        target_tz: str,
        house_system: str,
        sidecar_activation_layer: ActivationLayer | None = None,
    ) -> ActivationLayer:
        ...
```

Rules:

1. If sidecar returns activation layer, validate and use it.
2. If sidecar does not return it yet, build minimal activation layer from `day_signals`:
   - `transit_to_natal` for transit aspect to natal planet;
   - `transit_planet_in_house` for transit planet in natal house;
   - no fake profection/firdar.
3. Every output activation must have:
   - id;
   - technique;
   - family;
   - target;
   - strength;
   - evidence string;
   - debug info.

### 6.4. Minimal activation examples

```json
{
  "id": "act-transit-moon-opposition-natal-pluto-2026-07-08",
  "technique": "transit_to_natal",
  "technique_family": "transit",
  "target_type": "planet",
  "target_key": "PLUTO",
  "kind": "applying_aspect",
  "source_planet": "MOON",
  "source_frame": "transit",
  "target_planet": "PLUTO",
  "target_frame": "natal",
  "aspect": "opposition",
  "orb": 1.0454,
  "phase": "applying",
  "strength": 0.8693,
  "polarity": "tense",
  "evidence": "Transit Moon opposition natal Pluto, orb 1.0454°"
}
```

### 6.5. Sidecar endpoint contract

Endpoint:

```http
POST /v1/activation-layer
```

Request:

```json
{
  "birth": {
    "date": "1980-10-30",
    "time": "HH:MM",
    "tz": "Europe/Moscow",
    "lat": 0.0,
    "lon": 0.0
  },
  "target": {
    "date": "2026-07-08",
    "time": "12:00",
    "tz": "Europe/Moscow"
  },
  "house_system": "WHOLE_SIGN",
  "techniques": [
    "transit_to_natal",
    "transit_to_angle",
    "transit_to_lot",
    "annual_profection",
    "monthly_profection",
    "firdar_major",
    "firdar_minor",
    "solar_return",
    "lunar_return",
    "solar_arc",
    "secondary_progression",
    "eclipse_window"
  ]
}
```

Response:

```json
{
  "meta": {
    "calculation_version": "ss-calc-1.1.0",
    "activation_layer_version": "al-1.0",
    "house_system": "WHOLE_SIGN"
  },
  "activation_layer": {
    "schema_version": "activation-layer.v1",
    "activation_layer_version": "al-1.0",
    "target_date": "2026-07-08",
    "target_time": "12:00",
    "target_tz": "Europe/Moscow",
    "house_system": "WHOLE_SIGN",
    "activations": [],
    "by_planet": {},
    "by_house": {},
    "by_lot": {},
    "by_angle": {},
    "warnings": []
  }
}
```

### 6.6. W2 DoD

- activation layer exists in fresh TodayPayload internal pipeline;
- minimal transit activations generated;
- no fake unsupported techniques;
- audit artifacts include `activation_layer.json`;
- existing Basil 2026-07-08 baseline has expected transit activations;
- scoring output remains unchanged when V2 scoring disabled.

---

## 7. Wave W3 — Technique implementation

Wave W3 is split by technique family. Each family must be implemented, tested, audited, then merged. Do not implement all techniques in one giant commit.

---

### 7.1. W3.1 — Transit activations

#### Techniques

```text
transit_to_natal
transit_to_angle
transit_to_lot
transit_planet_in_house
```

#### Sidecar requirements

- Use Swiss Ephemeris positions.
- Use canonical aspect rules from `aspect_rules.v1.yml`.
- For each transit aspect:
  - compute orb;
  - compute applying/separating when possible;
  - compute exact_at when feasible;
  - compute strength;
  - classify polarity.

#### Lot requirements

Supported lots minimum:

```text
FORTUNE
SPIRIT
EROS
MARRIAGE
NECESSITY
VICTORY
NEMESIS
```

Lots must have:

```json
{
  "name": "FORTUNE",
  "longitude": 123.45,
  "house": 2,
  "formula": "day/night dependent formula id"
}
```

#### Angle requirements

Angles:

```text
ASC
DSC
MC
IC
```

Every angle activation must say frame:

```text
Transit Saturn trine natal MC
```

#### Tests

```text
apps/solarsage/tests/test_activation_transits.py
apps/api/tests/test_activation_layer_transits.py
```

#### W3.1 DoD

- all transit activations are visible in `activation_layer.activations`;
- no ambiguity between natal/transit frames;
- audit oracle can independently verify longitudes/orbs;
- Basil 2026-07-08 Moon opposite natal Pluto appears as activation.

---

### 7.2. W3.2 — Profections

#### Techniques

```text
annual_profection
monthly_profection
```

#### Requirements

Annual profection:

- Determine profected house by age on target date.
- Use configured house system.
- Determine lord of year by sign ruler of profected house.
- Generate activations:

```text
house: profected_house
planet: lord_of_year
optional: natal planets in profected house
```

Monthly profection:

- Derive month step from birthday or configured monthly profection method.
- Generate activations:

```text
house: monthly_profected_house
planet: lord_of_month
```

#### Contract examples

```json
{
  "technique": "annual_profection",
  "technique_family": "profection",
  "target_type": "house",
  "target_key": "3",
  "kind": "profected_house",
  "strength": 0.75,
  "phase": "period",
  "evidence": "Annual profection activates house 3"
}
```

```json
{
  "technique": "annual_profection",
  "technique_family": "profection",
  "target_type": "planet",
  "target_key": "MERCURY",
  "kind": "lord_of_year",
  "strength": 0.75,
  "phase": "period",
  "evidence": "Mercury is lord of year for annual profection house 3"
}
```

#### Tests

```text
apps/solarsage/tests/test_profections.py
apps/api/tests/test_activation_layer_profections.py
```

Tests must cover:

- birthday boundary;
- timezone boundary;
- age calculation;
- sign ruler mapping;
- annual/monthly family de-duplication in convergence.

#### W3.2 DoD

- annual/monthly profection activations generated;
- debug output includes age and house calculation;
- convergence counts profection family once unless scoring config explicitly weights sub-signals;
- golden fixture stable.

---

### 7.3. W3.3 — Firdar

#### Techniques

```text
firdar_major
firdar_minor
```

#### Requirements

- Determine sect/day-night if firdar sequence depends on it.
- Determine major period planet.
- Determine minor subperiod planet.
- Generate planet activations:

```text
firdar_major → planet
firdar_minor → planet
```

#### Contract example

```json
{
  "technique": "firdar_major",
  "technique_family": "firdar",
  "target_type": "planet",
  "target_key": "VENUS",
  "kind": "major_period_lord",
  "strength": 0.65,
  "phase": "period",
  "evidence": "Venus is major firdar lord on 2026-07-08"
}
```

#### Tests

```text
apps/solarsage/tests/test_firdar.py
apps/api/tests/test_activation_layer_firdar.py
```

Must include known historical date fixtures with expected major/minor lords.

#### W3.3 DoD

- major/minor period computed;
- both activations present;
- family de-duped for convergence;
- audit report shows firdar contribution separately.

---

### 7.4. W3.4 — Solar return and lunar return

#### Techniques

```text
solar_return
lunar_return
```

#### Solar return requirements

- Find exact solar return time for target year.
- Build SR chart for current location if available, else configured location policy.
- Compute SR ASC/MC.
- Compute SR planets in natal houses and/or SR houses.
- Generate activations:

```text
SR Asc/MC to natal houses
SR planets in important houses
SR chart ruler
SR Moon house
```

#### Lunar return requirements

- Find most recent lunar return before target datetime.
- Build LR chart.
- Generate activations:

```text
LR Moon house
LR Asc/MC
LR angular planets
```

#### Location policy

Must be explicit:

```text
return_location_policy:
  default: current_location_if_known_else_birth_location
  audit_required: true
```

Audit artifact must include which location was used.

#### Tests

```text
apps/solarsage/tests/test_solar_return.py
apps/solarsage/tests/test_lunar_return.py
apps/api/tests/test_activation_layer_returns.py
```

#### W3.4 DoD

- SR/LR activations present;
- return chart timestamp stored;
- location policy visible;
- no hidden fallback.

---

### 7.5. W3.5 — Solar arc and secondary progressions

#### Techniques

```text
solar_arc
secondary_progression
```

#### Requirements

Solar arc:

- Compute solar arc delta.
- Apply to natal planets/angles.
- Detect aspects to natal planets/angles/lots within configured orb.

Secondary progressions:

- Compute progressed positions for target age/date.
- Detect aspects to natal planets/angles/lots within configured orb.

Minimum supported:

```text
Progressed Moon aspects
Progressed Sun sign/house transitions
Solar Arc planets to angles
Solar Arc planets to natal personal planets
```

#### Contract example

```json
{
  "technique": "secondary_progression",
  "technique_family": "progression",
  "target_type": "planet",
  "target_key": "MERCURY",
  "kind": "progressed_moon_aspect",
  "source_planet": "MOON",
  "source_frame": "progressed",
  "target_planet": "MERCURY",
  "target_frame": "natal",
  "aspect": "square",
  "orb": 0.72,
  "strength": 0.72,
  "polarity": "tense",
  "evidence": "Progressed Moon square natal Mercury, orb 0.72°"
}
```

#### Tests

```text
apps/solarsage/tests/test_solar_arc.py
apps/solarsage/tests/test_secondary_progressions.py
apps/api/tests/test_activation_layer_progressions.py
```

#### W3.5 DoD

- progressed and solar arc activations appear;
- audit oracle can reproduce at least Moon progression and solar arc delta;
- performance acceptable.

---

### 7.6. W3.6 — Eclipse window

#### Technique

```text
eclipse_window
```

#### Requirements

- Maintain eclipse table or compute eclipses.
- Identify nearest eclipse within configured date window.
- Activate natal planets/angles/lots within orb.

Config:

```yaml
eclipse_window:
  days_before: 14
  days_after: 14
  orb_to_natal: 3.0
  strength: 0.55
```

#### Tests

```text
apps/solarsage/tests/test_eclipse_window.py
apps/api/tests/test_activation_layer_eclipse.py
```

#### W3.6 DoD

- eclipse activation only when date and orb criteria pass;
- artifact stores eclipse date/type/degree;
- no broad always-on eclipse text.

---

## 8. Wave W4 — Scoring V2

### 8.1. Цель

Перевести scoring с current transit-only-ish model на V2:

```text
base day signals
+ activation layer contributions
+ convergence bonus
+ anti-dominance
+ explicit score breakdown
```

### 8.2. Files

```text
apps/api/app/services/scoring_service.py
apps/api/app/services/scoring_v2_service.py
apps/api/app/schemas/scoring_v2.py
apps/api/tests/test_scoring_v2_*.py
```

Recommendation:

- keep current `ScoringService` as v1 compatibility;
- implement `ScoringV2Service` separately;
- dual-run v1/v2 before switching production.

### 8.3. Base score

Base score remains from day signals and/or natal baseline, but must be explicit:

```text
base_score = current signal-derived score before activation bonus
```

No hidden score mutation.

### 8.4. Activation contribution

For each activation:

```text
activation_contribution = activation.strength
  * technique_family_weight
  * target_weight_in_sphere
  * polarity_modifier
```

Where:

- `technique_family_weight` comes from `activation_rules.v1.yml`;
- `target_weight_in_sphere` comes from `spheres.v1.yml`;
- polarity can affect tension/ease but not silently remove evidence.

### 8.5. Convergence bonus

Convergence must be based on unique technique families.

Pseudo:

```python
for sphere in spheres:
    activated_families = set()
    activated_targets = []

    for activation in activation_layer.activations:
        if activation target maps to sphere:
            activated_families.add(activation.technique_family)
            activated_targets.append(activation)

    n = len(activated_families)
    bonus = convergence_curve(n) * sphere_convergence_weight
```

Do not count:

- annual and monthly profection as two independent families;
- multiple transit aspects from same family as multiple independent families for convergence;
- duplicate same activation twice.

### 8.6. Convergence curve

Config:

```yaml
convergence_curve:
  0: 0.00
  1: 0.00
  2: 0.40
  3: 0.65
  4: 0.80
  5: 0.90
```

### 8.7. Anti-dominance

Rules:

```text
if sphere.final_score > dominance_cap * sum_all_positive_scores:
    sphere.final_score = dominance_cap * sum_all_positive_scores
    sphere.dominance_capped = true
    add contribution source=cap
```

Required output:

```json
{
  "dominance_capped": true,
  "contributions": [
    {
      "source": "cap",
      "amount": -1.23,
      "evidence": "Dominance cap applied: sphere exceeded 65% of total salience"
    }
  ]
}
```

### 8.8. Day status V2

Current status uses aspect polarity. V2 should use a transparent status breakdown:

```json
{
  "day_status": "supportive",
  "status_breakdown": {
    "positive_aspect_score": 7.3468,
    "negative_aspect_score": 4.9252,
    "activation_support_score": 2.1,
    "activation_tension_score": 1.4,
    "ratio": 1.49,
    "rule": "supportive_if_support_score_gt_tension_1_3"
  }
}
```

Do not let activation layer flip status without visible breakdown.

### 8.9. Scoring V2 tests

Required tests:

```text
apps/api/tests/test_scoring_v2_convergence.py
apps/api/tests/test_scoring_v2_antidominance.py
apps/api/tests/test_scoring_v2_thresholds.py
apps/api/tests/test_scoring_v2_family_dedup.py
apps/api/tests/test_scoring_v2_breakdown_contract.py
apps/api/tests/test_basil_2026_07_08_v2_golden.py
```

Specific fixtures:

1. Mercury/profection/Saturn transit:
   - pre-bonus `thinking_speech_learning = X`;
   - post-bonus >= `1.4 * X`;
   - post-bonus <= `2.0 * X`.

2. Five activations on one sphere:
   - cap applies;
   - `dominance_capped = true`;
   - contribution records cap.

3. Family dedup:
   - annual + monthly profection both on Mercury;
   - family count = 1 for convergence.

4. Different families:
   - profection + firdar + transit all on Mercury;
   - family count = 3;
   - convergence curve value = 0.65.

### 8.10. W4 DoD

- v2 scoring implemented separately or safely feature-flagged;
- v1 output unchanged when flag off;
- v2 output includes full breakdown;
- all tests pass;
- audit artifacts show diff v1 vs v2;
- no LLM text changed yet unless W6 enabled.

---

## 9. Wave W5 — API integration, cache, dual-run rollout

### 9.1. Цель

Включить V2 в `TodayService` безопасно через dual-run and feature flags.

### 9.2. Feature flags

Add config:

```text
SOLARSAGE_V2_ENABLED=false
SOLARSAGE_V2_DUAL_RUN=true
SOLARSAGE_V2_FRONTEND_ENABLED=false
SOLARSAGE_AUDIT_ARTIFACTS_ENABLED=false
```

Behavior:

| Flag | Behavior |
|---|---|
| V2_ENABLED=false | production returns v1 |
| V2_DUAL_RUN=true | compute v1 and v2, return v1, log diff |
| V2_ENABLED=true | return v2 |
| V2_FRONTEND_ENABLED=true | frontend receives/render V2 fields |

### 9.3. TodayService changes

Files:

```text
apps/api/app/services/today_service.py
apps/api/app/services/natal_context_service.py
apps/api/app/db/models.py
```

Pipeline:

```python
natal_context = await NatalContextService(...)
transits = await client.get_transits(...)
signals = normalization_service.normalize_day(...)
day_signals = filter_day_scored_signals(signals)
activation_layer = await activation_layer_service.build(...)

if settings.SOLARSAGE_V2_DUAL_RUN:
    v1 = scoring_service.score_day(day_signals)
    v2 = scoring_v2_service.score_day(day_signals, activation_layer)
    log_score_diff(v1, v2)
    scoring_result = v1 unless V2_ENABLED else v2
```

### 9.4. Cache keys

Today cache key must include:

```text
user_id
target_date
profile_hash
calculation_version
activation_layer_version
scoring_version
canon_versions_hash
llm_prompt_version
frontend_payload_version
```

### 9.5. Diff logging

When dual-run enabled, log:

```json
{
  "event": "scoring.v2_diff",
  "user_id": "...",
  "date": "2026-07-08",
  "v1_day_status": "supportive",
  "v2_day_status": "supportive",
  "sphere_diffs": {
    "relationships_partnership": {
      "v1": 0.89,
      "v2": 1.45,
      "delta": 0.56,
      "top_new_evidence": ["annual_profection", "solar_return"]
    }
  }
}
```

### 9.6. W5 DoD

- V2 can dual-run without changing user output;
- cache invalidation verified;
- audit artifacts include v1/v2 diff;
- no performance regression beyond accepted thresholds;
- rollback is env flag only.

---

## 10. Wave W6 — Semantic layer, LLM guard, frontend V2

### 10.1. Цель

Пользователь должен видеть не просто «день поддерживающий», а объяснимую картину:

```text
что активировано
какими техниками
почему именно сегодня
что это меняет в работе/деньгах/отношениях/теле/общении
какие действия безопасны
```

### 10.2. TodayPayload V2 contract

Add optional V2 fields without breaking old frontend:

```json
{
  "meta": {
    "payload_version": "today.v2",
    "calculation_version": "ss-calc-1.1.0",
    "scoring_version": "ss-scoring-2.0",
    "activation_layer_version": "al-1.0",
    "canon_versions": {},
    "cached": false
  },
  "dayStatus": "supportive",
  "headline": "...",
  "sphereScores": [],
  "topFlags": [],
  "daySummary": {},
  "concreteAdvice": [],
  "v2": {
    "activationSummary": {
      "headline": "Сегодня сходятся 3 независимые техники на теме общения и решений",
      "topActivatedTargets": [
        {
          "targetType": "planet",
          "targetKey": "MERCURY",
          "label": "Меркурий",
          "familyCount": 3,
          "techniques": ["annual_profection", "transit_to_natal", "secondary_progression"],
          "spheres": ["thinking_speech_learning", "documents"]
        }
      ]
    },
    "activationEvidence": [],
    "scoreBreakdown": {},
    "whyToday": [],
    "audit": {
      "traceId": "...",
      "available": false
    }
  }
}
```

### 10.3. Frontend cards

#### 10.3.1. Day summary card

Show:

```text
Поддерживающий день
День возможностей
Главная сходимость: Меркурий / 3 дом / документы и общение
```

If no convergence:

```text
День в основном определяется текущими транзитами, без сильной сходимости долгих техник.
```

#### 10.3.2. Concrete advice rows

Each row must show:

```text
Работа       caution   evidence chips
Деньги       caution   evidence chips
Документы    good      evidence chips
Отношения    avoid     evidence chips
Спорт        neutral   evidence chips
Общение      avoid     evidence chips
```

Each row must have expanded evidence:

```text
Почему:
- Transit Mars trine natal Saturn, orb 2.06°
- Annual profection activates 3 house
- Solar return Mercury in 10 house

Как это влияет:
- documents score: base 1.10 + activation 0.80 + convergence 0.40 = 2.30
```

#### 10.3.3. Why exactly today

New block:

```text
Почему именно сегодня

Не один аспект, а сходимость:
1. Профекция года активирует 3 дом.
2. Транзитный Марс делает тригон к натальному Сатурну.
3. Прогрессивная Луна подходит к Меркурию.

Поэтому тема документов/слов/решений сегодня не фоновая.
```

#### 10.3.4. Technique chips

Chips:

```text
Транзит
Профекция
Фирдар
Solar Return
Прогрессия
Solar Arc
Лот
Угол
Затмение
```

Rules:

- user-friendly by default;
- exact technical evidence in expanded view;
- no raw scary numbers unless expanded/dev.

#### 10.3.5. Dev audit drawer

Only in dev/admin mode:

```text
Audit trace
- payload version
- scoring version
- activation version
- canon versions
- v1/v2 diff
- top activations
- raw score breakdown
```

### 10.4. Frontend files

```text
lib/contracts/today.ts
lib/adapters/today-payload.ts
components/today/today-screen.tsx
components/today/day-summary-card.tsx
components/today/concrete-day-advice.tsx
components/today/why-expanded.tsx
components/today/activation-evidence-card.tsx
components/today/technique-chip.tsx
components/today/dev-audit-drawer.tsx
```

### 10.5. LLM prompt rules

LLM must receive evidence packet:

```json
{
  "day_status": "supportive",
  "status_breakdown": {},
  "top_activations": [],
  "sphere_scores": {},
  "concrete_rows": [],
  "forbidden_claims": [],
  "required_distinctions": [
    "distinguish transit-to-natal from transit-to-transit"
  ]
}
```

LLM must not:

- invent techniques not in activation layer;
- say `today activates 5th house` if only natal background has 5th house;
- recommend action that contradicts row verdict;
- hide transit/natal frame in expanded evidence;
- mention exact scores to normal users unless product wants it.

### 10.6. Claim validator

Add deterministic post-check:

```text
apps/api/app/services/llm_claim_validator.py
```

Rules:

- Extract domain claims from generated text.
- Check against evidence packet.
- If unsupported, replace with safer fallback.
- If contradiction, either rewrite or use deterministic template.

Minimum hard guards:

```text
relationships avoid -> no direct relationship improvement advice
money avoid -> no invest/spend recommendation
body avoid -> no intense sport recommendation
communication avoid -> no hard negotiation recommendation
```

### 10.7. W6 DoD

- frontend renders V2 fields when available;
- old payload still renders;
- UI distinguishes transit/natal in expanded evidence;
- why exactly today block uses activation layer;
- no frontend astrology calculation;
- LLM unsupported claims test passes;
- screenshots added to visual tests.

---

## 11. Wave W7 — CI, golden snapshots, performance, rollout gates

### 11.1. Golden snapshots

Required fixtures:

```text
apps/api/tests/fixtures/golden/basil_2026_07_08_v1.json
apps/api/tests/fixtures/golden/basil_2026_07_08_v2.json
apps/api/tests/fixtures/golden/mercury_convergence_case_v2.json
apps/api/tests/fixtures/golden/antidominance_case_v2.json
```

Golden tests:

```text
apps/api/tests/test_golden_basil_2026_07_08.py
apps/api/tests/test_golden_v2_convergence.py
```

### 11.2. CI gates

Add CI job:

```text
audit-baseline
  - pytest apps/api/tests/test_audit_*.py
  - pytest apps/api/tests/test_golden_*.py
  - make audit-day USER_ID=<fixture-user> DATE=2026-07-08
  - compare artifacts with expected tolerances
```

Do not store private user data in public CI. Use anonymized fixture profile.

### 11.3. Tolerances

| Check | Tolerance |
|---|---:|
| planetary longitude | <= 0.01° |
| aspect orb | <= 0.02° |
| Moon phase | <= 0.5 percentage points |
| sphere score | <= 0.02 |
| top signal order | exact unless tie |
| day_status | exact |
| activation count | exact for golden fixtures |

### 11.4. Performance budgets

| Endpoint | Allowed regression |
|---|---:|
| `/v1/transits` | +20% max |
| `/v1/activation-layer` | p95 < 1500ms initially |
| API `/day` cached | no meaningful regression |
| API `/day` fresh V2 | p95 target < 5s without LLM, excluding external LLM |

### 11.5. Rollout gates

V2 can be enabled only if:

- W0-W6 DoD complete;
- v1/v2 dual-run for at least N internal test days;
- no unexplained status flips;
- all flips have activation evidence;
- frontend old/new compatibility tested;
- rollback tested.

---

## 12. Migration plan

### 12.1. Phase A — Baseline locked

- Run W0.
- Fix P0 trust bugs.
- Store audit artifacts for fixture user/date.
- Do not change scoring semantics.

### 12.2. Phase B — Contracts merged

- Merge schemas and version fields.
- Feature flags off.
- Payload compatible.

### 12.3. Phase C — Activation layer minimal

- Transit activations only.
- Scoring still v1.
- Audit artifacts include activation layer.

### 12.4. Phase D — Techniques incremental

Order:

```text
1. transit_to_natal/angle/lot
2. annual/monthly profection
3. firdar
4. solar return/lunar return
5. solar arc/secondary progression
6. eclipse window
```

After each technique:

```text
run tests
run audit-day
inspect diff
update golden only with reviewer note
```

### 12.5. Phase E — Scoring V2 dual-run

- V2 computed but not returned.
- Diff logged.
- Audit compares v1/v2.

### 12.6. Phase F — Frontend V2 hidden/dev

- Render V2 in dev mode.
- Product review.
- No public exposure.

### 12.7. Phase G — Internal rollout

- Enable V2 for internal users.
- Monitor diffs and feedback.

### 12.8. Phase H — Production rollout

- Enable by percentage or user cohort.
- Keep rollback flag.

---

## 13. Agent task templates

### 13.1. W0 task

```text
Effort: high

Implement W0 from docs/15_SolarSage_v2_activation_audit_TZ.md.
Do not implement activation_layer beyond existing audit artifact support.
Do not change scoring semantics except P0 trust fixes.

Deliver:
- make audit-day
- docs/audits/README.md
- retrograde fix
- Moon phase fix
- transit-to-natal label fix
- why_contexts day/natal separation
- advice consistency guard
- tests listed in W0

Before coding, output plan with exact files.
After coding, run tests and include audit output summary.
```

### 13.2. W1-W2 task

```text
Effort: high

Implement W1-W2 contracts and minimal activation layer from docs/15.
Feature flag V2 off.
Scoring output must remain unchanged.

Deliver:
- activation schemas
- scoring v2 schemas
- canon validation skeleton
- ActivationLayerService
- minimal transit activation layer from existing day signals
- audit artifact activation_layer.json
- tests
```

### 13.3. W3 technique task template

```text
Effort: xhigh for first technique in each family, high for follow-up fixes

Implement only <TECHNIQUE> from docs/15 W3.
Do not implement other techniques.
Add sidecar calculation, API activation mapping, tests, and audit diff.

Deliver:
- sidecar function
- endpoint exposure
- ActivationEvidence output
- oracle/golden fixture
- docs update if assumptions discovered
```

### 13.4. W4 scoring task

```text
Effort: xhigh

Implement ScoringServiceV2 from docs/15 W4.
Keep ScoringService v1 intact.
Add dual-run diff but do not return V2 unless flag enabled.

Deliver:
- scoring v2 service
- convergence by technique families
- anti-dominance with explicit contribution
- score breakdown contract
- tests for convergence, family dedup, threshold, anti-dominance
- Basil v2 golden snapshot
```

### 13.5. W6 frontend task

```text
Effort: high

Implement frontend V2 rendering from docs/15 W6.
No client-side astrology.
Backward compatible with old TodayPayload.

Deliver:
- contracts
- adapter
- activation evidence card
- technique chips
- why exactly today block
- dev audit drawer
- visual tests/screenshots
```

---

## 14. Acceptance checklist for full SolarSage V2

Full V2 accepted only when all are true:

### Audit

- [ ] `make audit-day` works.
- [ ] independent astronomy oracle passes.
- [ ] independent scoring oracle passes for v1 baseline and v2 fixtures.
- [ ] audit report generated.
- [ ] golden snapshots stable.

### Contracts

- [ ] `ActivationLayer` schema stable.
- [ ] `ScoringV2Result` schema stable.
- [ ] `TodayPayload.v2` optional fields stable.
- [ ] version meta present.
- [ ] cache invalidation respects versions.

### Techniques

- [ ] transit_to_natal.
- [ ] transit_to_angle.
- [ ] transit_to_lot.
- [ ] annual_profection.
- [ ] monthly_profection.
- [ ] firdar_major.
- [ ] firdar_minor.
- [ ] solar_return.
- [ ] lunar_return.
- [ ] solar_arc.
- [ ] secondary_progression.
- [ ] eclipse_window.

### Scoring

- [ ] convergence uses technique families.
- [ ] annual/monthly profection deduped as family.
- [ ] anti-dominance emits `dominance_capped`.
- [ ] score breakdown explains every score movement.
- [ ] no hidden magic constants outside canon.

### Semantics / LLM

- [ ] day evidence separated from natal background.
- [ ] LLM claims grounded in evidence packet.
- [ ] contradiction guard works.
- [ ] transit/natal frame distinction preserved.

### Frontend

- [ ] old payload renders.
- [ ] V2 payload renders.
- [ ] technique chips shown.
- [ ] why exactly today shown.
- [ ] expanded evidence shows exact frame/orb/technique.
- [ ] dev audit drawer available.

### Rollout

- [ ] dual-run completed.
- [ ] status flips reviewed.
- [ ] rollback flag tested.
- [ ] performance budget met.

---

## 15. Final product expectation after V2

After V2 the user should not just see:

```text
Поддерживающий день.
Документы — хорошо.
Отношения — осторожно.
```

The user should see:

```text
Поддерживающий день.
Главная тема: документы, решения и аккуратное общение.
Почему именно сегодня:
- текущий транзит активирует натальный Сатурн;
- профекция подсвечивает дом коммуникаций;
- прогрессивная техника усиливает Меркурий;
- поэтому документы зелёные, но общение требует точности.

Отношения: избегать острых тем.
Причина: Transit Moon opposition natal Pluto.
Безопасное действие: короткий спокойный контакт без выяснения отношений.
```

And in dev/audit mode:

```text
base score: 1.42
activation score: 0.85
convergence bonus: 0.40
final score: 2.67
families: transit, profection, progression
activations: act-..., act-..., act-...
```

This is the difference between:

```text
transit forecast with nice text
```

and:

```text
explainable multi-technique personal astrology engine
```

---

## 16. Hard rule

No SolarSage V2 scoring is allowed to ship without:

1. independent audit harness;
2. activation layer artifact;
3. score breakdown;
4. versioned cache keys;
5. frontend evidence rendering;
6. rollback flag;
7. golden snapshot.

If one of these is missing, the feature may be merged behind a flag, but must not become default production behavior.
