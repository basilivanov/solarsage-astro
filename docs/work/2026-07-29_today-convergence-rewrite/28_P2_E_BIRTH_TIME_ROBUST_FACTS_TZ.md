# 28 — P2-E Birth-time robust facts

Статус: **controller packet / implementation-ready**

Исполнитель: Codex CLI, `gpt-5.6-luna`, effort `high`

Depends on: packets 18–27, frozen `grace/canon/today_convergence.v1.yml`

Цель: получить production `RawPhysicalFact` из activation-grid для `exact`,
`bucket`, `unknown`, не меняя frozen W1 и не импортируя analysis harness.

## 1. Локальная цель

Добавить одну чистую API-прослойку:

```text
BirthTimeResolution + ordered ActivationGridSample[]
  -> robust RawPhysicalFact[] + typed audit
```

Для `exact` используется единственный sample. Для `bucket/unknown` публичным
становится только один физический факт, который устойчив во всех канонических
контрольных точках. Sidecar должен обогатить transit-to-natal aspect debug
реальной скоростью натальной цели в градусах/час; это единственный новый
расчётный datum пакета и он нужен для frozen orb-margin.

## 2. Exact write scope

- `apps/solarsage/solarsage/services/calculation_core.py`
- один существующий или новый узкий sidecar test для target-speed debug
- новый `apps/api/app/services/today_birth_time_facts.py`
- новый `apps/api/tests/test_today_birth_time_facts.py`
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`

Если существующий sidecar test-файл не подходит по ownership, разрешён ровно
один новый `apps/solarsage/tests/test_activation_target_speed.py`.

## 3. Frozen / out of scope

- не менять canon YAML, formula/calculation/activation-layer versions;
- не менять shared/public activation schema: скорость остаётся внутренним
  числом в уже существующем `debug`;
- не менять wire contract, DB, TodayService, Calendar, snapshots, LLM, pregen,
  frontend;
- не импортировать ничего из `docs/.../analysis/` и не копировать таблицу
  средних скоростей оттуда;
- не добавлять noon fallback, N отдельных HTTP-вызовов, cache или parallelism;
- не вычислять сферы/группы/tone здесь: это уже владеют canonical-unit и pipeline;
- не коммитить и не push.

## 4. Sidecar target-speed contract

На общей production-границе `calculation_core.calculate_activation_layer`
для каждого `transit_to_natal` aspect activation добавить в `debug`:

```python
"target_speed_deg_per_hour": abs(float(natal_planet_speed_deg_per_day)) / 24.0
```

Требования:

- источник — фактическое поле `speed` ровно той натальной планеты, которая
  является target; никакого hard-coded/default значения;
- значение finite и `>= 0`; если исходная скорость отсутствует/не finite,
  ключ не публикуется, а API non-exact фильтр затем fail-closed;
- angle/lot/house activations этот ключ не получают;
- прочие поля activation и single/grid parity не меняются;
- builder вызывается ровно один раз с тем же подготовленным/reused
  `NatalCalculationContext`; прямой core-вызов без переданного context готовит
  его один раз и передаёт builder;
- добавить узкий test: direct core `transit_to_natal` evidence несёт правильный
  `abs(speed)/24`, а angle/lot evidence не притворяется planet-speed.

Это internal debug enrichment, а не изменение физической формулы или wire
schema, поэтому version bump в этом пакете запрещён.

## 5. API public types

Новый модуль экспортирует минимум:

```python
class TodayBirthTimeFactsError(ValueError): ...

@dataclass(frozen=True)
class BirthTimeFactsAudit:
    input_sample_count: int
    input_activation_count: int
    published_fact_count: int
    excluded_by_reason: tuple[tuple[str, int], ...]

@dataclass(frozen=True)
class BirthTimeFactsResult:
    facts: tuple[RawPhysicalFact, ...]
    audit: BirthTimeFactsAudit

def build_birth_time_facts(
    resolution: BirthTimeResolution,
    samples: Sequence[ActivationGridSample],
) -> BirthTimeFactsResult: ...
```

Имена внутренних helper'ов свободны. Public функция принимает только реальные
production types из packets 18, 26, 27. Ошибки boundary/invariant имеют stable
prefix `today_birth_time_facts:`. Malformed top-level arguments raise; отдельный
неустойчивый activation исключается в audit и не валит весь день.

## 6. Boundary validation

До агрегации проверить:

- `resolution` и каждый sample имеют точный production type;
- sample count и ordered `birth_time` 1:1 равны `resolution.control_times`;
- все layers относятся к одному `target_date`, `target_time`, `target_tz`,
  `house_system`, calculation/activation-layer version;
- activation IDs уникальны внутри одного layer;
- sample/activation collections не принимают `str`, mapping или generator как
  Sequence;
- `exact` имеет ровно один sample; `bucket/unknown` — canonical controls из
  resolver и positive `canonical_gap_hours`.

Никакой tolerant normalization порядка/времени.

## 7. Physical identity and cross-control merge

Identity одного activation строится только из стабильной физической семантики:

```text
technique, technique_family, kind,
source_planet, target_type, target_key,
aspect, house, lot, angle
```

Строки trim + case-normalize согласованно с canonical-unit boundary. В identity
не входят activation `id`, orb, strength, окна, phase, debug. Если один identity
встречается дважды внутри sample, этот identity целиком исключается как
`duplicate_identity`; произвольный winner запрещён.

Для non-exact факт публикуется только если:

1. ровно одна запись identity присутствует во **всех** control samples;
2. `active=true` во всех точках;
3. polarity одинакова во всех точках;
4. target не `house|angle|lot` и `house/angle/lot`-dependent payload отсутствует;
5. для family `firdar` значения `debug.is_day_birth` присутствуют, bool и
   одинаковы во всех точках; missing/flip исключается;
6. для aspect во всех точках есть finite `orb >= 0`, finite
   `debug.max_orb > 0`, finite `debug.target_speed_deg_per_hour >= 0`, причём
   `max_orb` и target-speed согласованы между точками (обычный tight
   float tolerance, не округление/подгонка);
7. frozen margin выполнен в каждой точке:

```text
orb / max_orb + target_speed_deg_per_hour * canonical_gap_hours / max_orb
    <= canon significance.orb_ratio_max (= 0.5)
```

Значение `0.5` не hard-code: взять из production canon loader. Canon в public
signature не добавлять; загрузить один раз на вызов. Не использовать среднюю
скорость и не подставлять fallback при missing metadata.

Stable reason tokens audit (минимум):

```text
missing_control
inactive_control
duplicate_identity
polarity_changed
birth_time_sensitive_target
sect_changed_or_unknown
orb_metadata_missing
orb_metadata_changed
orb_margin_exceeded
malformed_activation
```

Counts deterministic, сортировка reason лексикографическая. Один identity
считается исключённым один раз по первому правилу в указанном выше порядке.

## 8. ActivationEvidence -> RawPhysicalFact

Representative для exact — запись единственного sample. Для robust non-exact
— запись первого control sample, но:

- `orb = max(orb across controls)` (worst observed exactness);
- `strength = max(strength across controls)` — frozen replay parity;
- `provenance_ids` = sorted unique activation IDs всех control points;
- `birth_time_mode = resolution.mode`;
- `birth_time_robustness = "robust"`;
- `producer = "activation"`;
- `technical_spheres = ()`; сферы далее детерминированно маппит canon;
- `target_salience = 1.0` для mapped physical target;
- `source_key = source_planet`; если source отсутствует у timelord/return,
  оставить `None`, не выдумывать planet;
- `target_type`, `target_key`, `aspect_type`, `house`, `polarity`, `phase`
  переносятся семантически без display-текста.

Event-class mapping, и только он:

```text
firdar_major | firdar_minor              -> timelord_period_change
solar_return                             -> solar_return
lunar_return                             -> lunar_return
monthly_profection                       -> monthly_profection
transit_planet_in_house / planet_in_house-> house_ingress
aspect != null                           -> event_class None
всё остальное non-aspect                 -> event_class None
```

Последний случай намеренно будет fail-closed на canonical-unit boundary; здесь
не выдумывать новый canon class.

Temporal role до DayDelta:

- timezone-aware `exact_at` или `active_from`, попавший в layer target local
  date, либо `phase=exact` -> `anchor_today`;
- `phase=background|period` -> `background`;
- `phase=applying|separating` -> `supporting`;
- иначе `unrelated`.

DayDelta позже может повысить `supporting|unrelated` до `anchor_today` только по
semantic key через уже принятый canonical ledger; `background` остаётся
audit-only и не повышается.

Окна sidecar parse fail-closed: ISO date -> `date`, ISO datetime обязан быть
timezone-aware -> `datetime`; naive/invalid исключает identity как
`malformed_activation`. Для exact окна сохраняются. Для bucket/unknown все
datetime окна переводятся в `layer.target_tz` и coarse-grain до local `date`;
точные часы не должны попасть в `RawPhysicalFact`. Date остаётся date.

`data_quality="valid"`. Поле human-readable `evidence` и произвольный debug не
переходят в raw fact.

## 9. Determinism and mutation tests

API tests обязаны доказать:

1. exact: один sample -> все валидные active facts, exact timezone-aware timing
   сохранён, mode exact;
2. каждый из четырёх bucket resolution + unknown принимает canonical grid;
3. порядок фактов стабилен независимо от входного порядка activations внутри
   layer (sort by physical identity);
4. missing one control, duplicate identity, inactive, polarity flip, sect flip
   исключаются с точным audit count;
5. house/angle/lot hard excluded для non-exact, но exact не фильтруется этим
   robustness-правилом;
6. margin boundary: equality проходит, превышение на epsilon исключается;
7. missing/non-finite/changed speed or max_orb fail-closed; нулевая скорость
   допустима;
8. non-exact не содержит timezone datetime в output windows;
9. representative uses worst orb, max strength and all sorted provenance IDs;
10. malformed top-level grid raises stable typed error; malformed individual
    evidence даёт audit exclusion, не partial invented fields;
11. полученные facts реально проходят `build_canonical_ledger` для transit,
    firdar delta, return и дают ожидаемый fail-closed для unknown non-aspect;
12. source module не импортирует analysis harness и не содержит speed fallback.

Не делать snapshot/approval tests; обычные unit fixtures достаточны.

## 10. GRACE / verification

Новый API-модуль и существенно изменённый sidecar module сохраняют/уточняют
правдивые `AI_HEADER`, module/function contracts, blocks и `owned_tests`.
Runtime логов здесь нет: функция чистая, `emitted_logs: none`. Добавить одно
ребро grid -> robust facts -> canonical ledger в knowledge graph и строку gate
P2-E в verification matrix.

Минимальные команды исполнителя:

```bash
git diff --check
PYTHONPATH=apps/api:packages/py-contracts apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_birth_time_facts.py \
  apps/api/tests/test_today_birth_time.py \
  apps/api/tests/test_solarsage_client.py \
  apps/api/tests/test_today_convergence_units.py \
  apps/api/tests/test_today_convergence_ledger.py -q
PYTHONPATH=apps/solarsage:packages/py-contracts \
  apps/solarsage/venv/bin/python -m pytest \
  apps/solarsage/tests/test_activation_grid.py \
  <target-speed-test> -q
python3 scripts/grace_lint.py apps/api/app/services/today_birth_time_facts.py
python3 scripts/grace_lint.py apps/solarsage/solarsage/services/calculation_core.py
```

Также запустить Ruff по изменённым Python-файлам доступным API venv.

## 11. Expected evidence / escalation

В отчёте вернуть:

- exact file list;
- краткую семантику identity/margin/window-coarsening;
- targeted test counts;
- GRACE/Ruff/diff-check результаты;
- `git status --short`;
- подтверждение: canon/schema/versions не менялись, analysis imports отсутствуют,
  commit/push не выполнялись.

Остановиться и спросить архитектора, если реальная sidecar скорость не finite,
activation identity неоднозначна после перечисленных полей, либо для принятого
RawPhysicalFact требуется изменить frozen canon/shared schema/version.
