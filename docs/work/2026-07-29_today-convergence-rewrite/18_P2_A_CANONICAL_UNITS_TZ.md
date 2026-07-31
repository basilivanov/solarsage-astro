# P2-A CONTROLLER PACKET — Production canon and canonical units

Phase / Wave: **P2 · W2-S1 deterministic convergence pipeline**

Modules: `M-TODAY-CONVERGENCE-CANON`, `M-TODAY-CONVERGENCE-UNITS`,
`M-TESTS`, `M-GRACE-PROJECT-ADAPTER`.

## Goal

Добавить первый production-only слой нового Today: строгую загрузку frozen W1
canon и чистое преобразование одного raw physical fact в canonical unit с
producer-independent event ID, fail-closed significance и трёхуровневой
eligibility. Наблюдаемый результат — один и тот же физический факт из
`activation` и `day_signal` получает byte-identical `evt_v1_…`, а неизвестный
factor/orb/event class остаётся в audit result, но не становится публичным
impulse/evidence/anchor.

Это локальный пакет. Он **не** реализует grouping, hero, presentation selection,
dayTone, snapshot или HTTP.

## Authoritative inputs

- `grace/canon/today_convergence.v1.yml` — frozen W1 convergence canon;
- `grace/canon/aspect_rules.v1.yml` — aspect weights и explicit max-orb;
- `00_MASTER_TZ.md` §4.1–4.5;
- `06_DEV_RELEASE_EXECUTION_PLAN_TZ.md` P2;
- frozen reference semantics в `analysis/convergence_canon.py` и
  `analysis/ablation_harness.py` — только reference, production import запрещён.

## Exact write scope

Кодер может создавать/изменять только:

1. `apps/api/app/services/today_convergence_canon.py` (new);
2. `apps/api/app/services/today_convergence_units.py` (new);
3. `apps/api/tests/test_today_convergence_canon.py` (new);
4. `apps/api/tests/test_today_convergence_units.py` (new);
5. `grace/verification-matrix.md`;
6. `grace/knowledge-graph.xml`.

Файл этого packet не редактировать. Нужен соседний файл — остановиться и
доложить, архитектор выпустит новый packet.

## Required implementation

### 1. Strict production canon

`today_convergence_canon.py` владеет immutable/typed представлением только тех
полей двух YAML, которые нужны W2. Loader принимает optional path/dir для
тестов, валидирует `schema_version=today_convergence.v1`,
`status=frozen_w1`, `formula_version=today-convergence-2`, уникальный canonical
sphere order, aspect/event-class thresholds, fast/rare rules, driver rules,
sphere maps и orb profile. Missing/malformed/unknown normative value — явный
`TodayConvergenceCanonError`, без default/fallback.

Production-модуль не импортирует `docs/work/**/analysis/*`, legacy
`day_valence.v1.yml`, `TodayPayload`, `TodayFocus` или старые product maps.

Публичные pure helpers canon должны покрывать как минимум:

- fail-closed factor → canonical product spheres (`unknown -> ()`, без `work`);
- aspect weight и source max-orb (`unknown -> None`, без `ORB_FALLBACK`);
- известность/значимость non-aspect `event_class`;
- fast-source, rare-source и hero-confirmation policy.

### 2. Raw fact and canonical unit boundary

`today_convergence_units.py` вводит frozen dataclasses (или эквивалентные
immutable typed records): raw physical fact, canonical unit и build result.
Canonical unit несёт поля frozen master §4.3.1:

`canonical_event_id`, `semantic_key`, `driver_key`, `technique_horizon`,
`event_class`, `source_key`, `target_key`, `target_type`, `target_salience`,
`aspect_type`, `orb`, `max_orb`, `orb_ratio`, `exact_at`, `phase`,
`active_from`, `active_until`, `data_quality`, `birth_time_mode`,
`birth_time_robustness`, strict mapped spheres, normalized polarity/strength,
`impulse_eligible`, `evidence_eligible`, `rare_anchor_eligible`,
`hero_confirmation_eligible`, `exclusion_reason`, plus sorted provenance IDs.

Build boundary не бросает исключение на один плохой raw fact: возвращает typed
excluded result/reason, чтобы следующий ledger мог увеличить audit counters.
Programming/configuration errors canon при этом продолжают fail-fast.

### 3. Canonical identity

- ID format: `evt_v1_` + первые 32 lowercase hex символа SHA-256.
- Hash input — canonical JSON (`sort_keys=True`, compact separators, UTF-8) с
  identity version, нормализованными physical fields и event window
  (`active_from`, `exact_at`, `active_until`).
- Physical fields: normalized `technique`, `technique_family`, `source_key`,
  `target_key`, `target_type`, `aspect_type`, `event_class`, `house`.
- `Transit_`/`Natal_` стриппятся, planet/target keys uppercase, enum-like keys
  lowercase, aspect normalized consistently.
- Producer path, producer/factor IDs, technical themes, spheres, polarity,
  strength, salience и provenance **не входят** в identity.
- At least one event-window field обязателен. Aware datetime canonicalizes to
  UTC `Z`; date remains `YYYY-MM-DD`; naive datetime is excluded fail-closed.
- Mixed `date`/`datetime` window precision excluded fail-closed; для сравнимого
  окна обязательно `active_from <= exact_at <= active_until` по присутствующим
  границам. Плохой raw window никогда не выбрасывает uncaught `TypeError`.
- Изменение physical field или event window меняет ID; изменение producer или
  provenance не меняет ID.

### 4. Significance and eligibility

- Aspect: known aspect weight `>=0.55`, explicit known source `max_orb`, finite
  non-negative `orb`, `orb/max_orb <=0.5`. Missing/unknown/negative/NaN orb or
  unsupported source is excluded. Никакого `6.0` fallback.
- Non-aspect: только явно известный `event_class` из canon; `significant:false`
  и unknown class не проходят. Auto-pass запрещён.
- Missing/unknown target type, unmapped physical factor, invalid house where
  required, empty driver, invalid data quality or invalid event window exclude
  the unit from all public eligibility with stable reason code.
- Canonical target domain: `natal_planet | house | lot | angle | sphere`;
  producer value `planet` нормализуется в `natal_planet`. `phase` не является
  eligibility axis: сохраняется normalized non-empty string либо `None`, без
  придуманного закрытого enum. `data_quality` аналогично сохраняет non-empty
  normalized value; пустое или явное `invalid` fail-closed.
- Producer polarity domain: `supportive | tense | mixed | neutral`; unknown или
  empty fail-closed. `strength` и `target_salience` — finite `0..1` inclusive,
  вне диапазона/NaN fail-closed без clamp. `neutral` остаётся валидной unit
  polarity; её presentation semantics принадлежат следующему packet.
- `temporal_role=background` остаётся audit/context unit, но
  `impulse/evidence/rare/hero_confirmation=false`.
- Для `birth_time_mode=bucket|unknown` unit с
  `birth_time_robustness=time_sensitive` также остаётся audit unit, но все
  public eligibility flags false; exact+time_sensitive допустим.
- Eligibility nesting всегда соблюдается:
  `rare_anchor_eligible => evidence_eligible => impulse_eligible`.
- MOON/MERCURY/VENUS: significant public impulse/evidence, never rare and never
  hero confirmation.
- JUPITER/SATURN/URANUS/NEPTUNE/PLUTO significant transit aspects may be rare;
  SUN/MARS may confirm but are not rare anchors.
- `timelord_period_change` may be rare; `lunar_return` and
  `monthly_profection` remain significant evidence but never rare.
- `structural_lunar_event` есть в rare registry, но отсутствует в frozen
  `significance.event_class`: в этом packet он **не получает auto-pass** и
  fail-closed до отдельного machine-readable significance rule. Не выдавать
  потенциальный rare-class за фактически eligible unit.
- `driver_key`: timelord uses normalized technique family; otherwise a known
  physical source key. Producer IDs are forbidden.

Reason codes are stable machine tokens (enum/Literal or validated constants),
not prose. Include at least distinct codes for unmapped, event class, aspect,
orb, event window, driver, background and data quality.

## Frozen / out of scope

- Не менять frozen YAML, W1 formula/fingerprint или analysis artifacts.
- Не менять existing `canon_service.py`, `day_factor_ledger.py`,
  `today_focus_builder.py`, schemas/generated contracts или routers.
- Не адаптировать legacy ledger в этом packet; adapter будет отдельным P2
  packet после принятия pure boundary.
- Не реализовывать grouping/independence count/hero/main_event/impulses,
  sphere projection группы, polarity aggregation, dayTone, birth-time sampling,
  DayDelta integration, persistence, LLM, HTTP или frontend.
- Не ослаблять и не удалять существующие тесты.

## Must preserve

- Frozen W1 semantics и `formula_version=today-convergence-2`.
- Unknown mapping никогда не превращается в `work`.
- Canonical ID устраняет producer duplicates, но не заявляет independence.
- Background ни при каких входах не становится eligible.
- Новый W2 path не импортирует legacy Today wire roots.
- Все новые/существенно изменённые файлы имеют полный GRACE header,
  MODULE_CONTRACT, MODULE_MAP, paired START/END_BLOCK, owned_tests и function
  contracts для нетривиальных public entrypoints.
- Pure слой не пишет runtime logs: `emitted_logs: none` честно отражён в GRACE.

## Tests / acceptance

Тесты обязаны доказать:

1. strict loader принимает repository canon и отвергает malformed копии;
2. exact sphere/aspect/orb/event-class values берутся из YAML, не продублированы
   скрытыми fallback constants;
3. activation/day-signal producer parity ID и strip-prefix parity;
4. изменение каждого physical identity axis/window меняет ID, изменение
   provenance/non-identity fields — нет;
5. aspect threshold boundary, orb ratio boundary и fail-closed unknown/missing/
   negative/non-finite orb/source/aspect;
6. event-class whitelist, house null, unmapped factor и invalid window/data
   quality fail closed с ожидаемыми reason codes;
7. fast/slow/SUN-MARS/time-lord/lunar-return/monthly-profection eligibility
   truth table, structural-lunar fail-closed gap и nesting invariant;
8. background всегда исключён из public eligibility;
9. bucket/unknown time-sensitive всегда исключён из public eligibility;
10. records immutable и результат deterministic при перестановке provenance.

## GRACE sync

- В `knowledge-graph.xml` зарегистрировать два новых backend service module ID
  с точными paths и зависимостью units → canon.
- В `verification-matrix.md` добавить отдельный
  `UC-TODAY-CONVERGENCE-W2-UNITS` с focused test command и перечисленными gates.
  W1 строку не переписывать и не выдавать этот packet за полный W2-S1.

## Verification commands

Основной targeted gate:

```bash
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_convergence_units.py -q
```

Также обязательно:

```bash
cd /tmp/solarsage-convergence-impl
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/today_convergence_canon.py \
  apps/api/app/services/today_convergence_units.py \
  apps/api/tests/test_today_convergence_canon.py \
  apps/api/tests/test_today_convergence_units.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

## Expected evidence

В отчёте: точный список изменённых файлов; количество focused tests; по одному
примеру producer-parity ID и fail-closed reason; результаты ruff, grace_lint,
marker gate и diff-check; `git status --short`.

## Escalation and no-commit rule

Если для корректности нужен файл вне exact write scope, frozen правило не имеет
однозначного machine-readable значения или reference расходится с canon —
**остановиться**, ничего не угадывать и доложить архитектору.

**Ничего не коммить и не пушить — коммит и push делает ревьюер.**
