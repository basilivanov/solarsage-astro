# P2-C1 CONTROLLER PACKET — Frozen tone policy in production

Phase / Wave: **P2 · W2-S3 deterministic convergence pipeline**

Modules: `M-TODAY-CONVERGENCE-TONE`, `M-TODAY-CONVERGENCE-GROUPS`,
`M-TODAY-CONVERGENCE-LEDGER`, `M-TODAY-CONVERGENCE-CANON`, `M-TESTS`,
`M-GRACE-PROJECT-ADAPTER`.

## Goal

Перенести owner-approved `tone-candidate-0.1` из analysis reference в pure
production слой: отдельно считать unit polarity, weighted group polarity и
осторожный `day_tone` только по свежему non-fast evidence. Все коэффициенты и
truth-table поля читаются из frozen canon, а не дублируются скрытыми constants.

Packet не выбирает публичные карточки и не строит wire payload. Внутренний
`group_polarity=steady` разрешён frozen tone algorithm; wire polarity остаётся
отдельной presentation-задачей и этим packet не расширяется.

## Authoritative inputs

- `02_TONE_POLICY_AMENDMENT.md` — normative truth table и weighted balance;
- `grace/canon/today_convergence.v1.yml::tone_policy`;
- `analysis/tone_policy_candidate.py` — replay-verified executable reference;
- `00_MASTER_TZ.md` D3/D14, T2 и §4.6;
- принятые P2-A/B0/B1/B2 records;
- `06_DEV_RELEASE_EXECUTION_PLAN_TZ.md` P2.

## Exact write scope

Кодер может создавать/изменять только:

1. `apps/api/app/services/today_convergence_canon.py`;
2. `apps/api/tests/test_today_convergence_canon.py`;
3. `apps/api/app/services/today_convergence_tone.py` (new);
4. `apps/api/tests/test_today_convergence_tone.py` (new);
5. `grace/verification-matrix.md`;
6. `grace/knowledge-graph.xml`.

Файл этого packet не редактировать. Нужен иной файл — остановиться и доложить.

## Required implementation

### 1. Strict canon exposure

Расширить immutable `TodayConvergenceCanon` typed полями tone policy и строго
валидировать весь YAML block, минимум:

- `status=frozen_w1`, `version=tone-candidate-0.1`;
- exact layers и polarity/dayTone enums;
- `neutral_maps_to=steady`;
- role weights `anchor_today=1.0`, `supporting_context=0.5`,
  `background=0.0`, `mixed_split=0.5`;
- `independence=distinct_driver`, `min_side_weight=0.25`,
  `mixed_margin=0.25`;
- fresh predicate tokens, ongoing roles, fast source list;
- `high_confidence_strength=0.75`, tense/supportive independent thresholds=2,
  mixed requirement=true;
- exact audit field registry.

Mappings должны быть immutable. Malformed/missing/extra/wrong-type tone values
fail-fast через `TodayConvergenceCanonError` со stable reason token. Не менять
сам YAML и frozen значения.

### 2. Typed immutable tone result

Ввести frozen records:

- `CanonicalGroupTone`: group ID, polarity
  (`supportive|tense|mixed|steady`), supportive/tense scores, independent unit
  count, sorted driver keys и immutable polarity counts;
- `CanonicalToneScores`: fresh supportive/tense counts, high-confidence anchor
  flags, context supportive/tense counts;
- `CanonicalToneAudit`: selected unit polarity counts, context polarity counts,
  group polarity counts, tone scores, sorted tone trigger semantic keys,
  selected/context unit IDs и `legacy_any_selected_tense`;
- `CanonicalToneResult`: policy version, `day_tone`, group tone tuple и audit;
- `TodayConvergenceToneError` для programming misuse/invariant failures.

### 3. Public entrypoint and inputs

`compute_canonical_tone(...)` принимает:

- `CanonicalLedger`;
- соответствующий `CanonicalGroupingResult`;
- `target_date: date`;
- IANA `timezone_name`;
- `selected_unit_ids: Sequence[str]` — уже выбранные selector-слоем IDs только
  для audit/legacy diagnostic; day tone от selection не зависит;
- optional validated canon.

Selected IDs уникальны и обязаны ссылаться на public evidence ledger units;
group IDs/members обязаны ссылаться на тот же ledger. Invalid timezone,
duplicate/unknown selected ID, чужой group member или malformed API — typed
error. Default canon загружается strict loader.

### 4. Unit polarity and weights

- `supportive|tense|mixed` сохраняются; `neutral` → `steady`; иное значение —
  invariant error (P2-A уже fail-closed).
- background weight 0 и не входит в tone candidates.
- `anchor_today`: `strength × 1.0`;
- `supporting|unrelated`: `strength × supporting_context(0.5)`;
- strength ограничен 0..1 на defensive boundary;
- mixed делится между сторонами по `mixed_split=0.5`.

Для balance один `driver_key` считается один раз: выбирается максимальный tone
weight, tie-break по canonical event ID. Producer/raw duplicates не влияют.

### 5. Group polarity

Для каждой canonical group считать balance только её non-background members:

- обе стороны ниже `min_side_weight` → `steady`;
- обе достигли threshold → `mixed`, если разница ≤
  `max(mixed_margin, total × mixed_margin)`, иначе доминирующая сторона;
- достигла одна сторона → она;
- scores round до 6 знаков, порядок group tones по group ID.

Этот internal `steady` нужен audit/day model и **не меняет** public wire enum
этим packet.

### 6. Fresh predicate and day tone

Fresh unit, если:

1. `temporal_role=anchor_today`; или
2. `exact_at`, переведённый из aware datetime в `timezone_name`, попадает в
   `target_date` (для date value — exact date equality).

String-prefix/UTC-date comparison запрещён. Naive datetime — invariant error.
Supporting exact-today считается fresh, но остаётся с weight 0.5. Ongoing
supporting/background вне fresh остаётся context.

После deterministic distinct-driver dedup fresh units:

- Moon/Mercury/Venus удаляются из day-level trigger pool, но остаются group и
  detail evidence;
- high-confidence hero anchor соответствующей polarity и strength ≥0.75
  создаёт meaningful side;
- либо side требует ≥2 independent fresh units;
- fresh pure supportive + fresh pure tense с каждой weighted side ≥0.25 →
  `mixed` до одиночных tense/supportive branches;
- mixed fresh unit один не создаёт tone; при наличии другого independent
  non-fast unit он добавляет по одной стороне, буквально как frozen reference;
- затем priority: mixed pair → tense → supportive → steady.

Tone trigger keys — semantic keys distinct-driver fresh non-fast pool.

### 7. Audit semantics

- selected `unit_polarity_counts` и `legacy_any_selected_tense` считаются
  **только** по `selected_unit_ids`;
- context counts/IDs — public non-background evidence, которое не fresh;
- group counts — по всем canonical groups;
- day tone не зависит от количества raw/background/selected units;
- output byte-equivalent при перестановке ledger/group input, если selected
  order одинаков; internal tuples/counters immutable и sorted.

## Frozen / out of scope

- Не менять YAML/canon values, eligibility/grouping/hero/spheres.
- Не выбирать groups/impulses/mainEvent и не создавать presentation state.
- Не преобразовывать internal steady group polarity в public wire polarity.
- Не реализовывать adapter/replay/snapshot/DB/API/LLM/pregen/frontend.
- Не импортировать analysis module в production и не копировать thresholds в
  tone module constants.
- Не вводить frequency quota или live-validity claims.

## Tests / acceptance

Тесты обязаны доказать:

1. strict loader принимает frozen block и отклоняет по одной мутации каждого
   класса полей/extra key;
2. neutral→steady, mixed split и role weights совпадают с canon;
3. same-driver выбирается один раз детерминированно;
4. group supportive/tense/mixed/steady branches и margin работают;
5. background не влияет, ongoing supporting попадает только в context;
6. exact_at учитывает IANA timezone/date boundary, supporting exact-today fresh;
7. один fast или один mixed unit оставляет day steady;
8. high-confidence hero tense/supportive anchor создаёт tone;
9. два independent fresh tense/supportive создают соответствующий tone;
10. fresh supportive+tense weighted pair → mixed и не «тяжёлый»;
11. selected counts/legacy flag не смотрят на невыбранный tense;
12. tone triggers, context IDs, group order и permutation deterministic;
13. invalid timezone/date/selected/group reference → typed error;
14. P2-A/B0/B1/B2 focused suites остаются зелёными.

## GRACE sync

- Register `M-TODAY-CONVERGENCE-TONE` и edges к groups/ledger/canon.
- Update canon module contract/map for tone exposure.
- Add `UC-TODAY-CONVERGENCE-W2-TONE` с timezone/fresh, weighted balance и
  tense-inflation regression gates. Не выдавать packet за selector/wire.

## Verification commands

```bash
cd apps/api && /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_convergence_units.py \
  tests/test_today_convergence_ledger.py \
  tests/test_today_convergence_groups.py \
  tests/test_today_convergence_tone.py -q

cd /tmp/solarsage-convergence-impl
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/today_convergence_canon.py \
  apps/api/app/services/today_convergence_tone.py \
  apps/api/tests/test_today_convergence_canon.py \
  apps/api/tests/test_today_convergence_tone.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

## Expected evidence

Exact changed paths; focused count; one timezone-boundary example; one
supportive+tense mixed example; one long-running tense context example; selected
legacy diagnostic example; malformed canon and reference integrity evidence;
Ruff/GRACE/markers/diff/status.

## Escalation and no-commit rule

Если approved YAML и `tone_policy_candidate.py` расходятся либо public wire
требует немедленно публиковать internal `steady` group polarity — остановиться
и доложить. Не менять W1 и wire silently.

**Ничего не коммить и не пушить — коммит и push делает ревьюер.**
