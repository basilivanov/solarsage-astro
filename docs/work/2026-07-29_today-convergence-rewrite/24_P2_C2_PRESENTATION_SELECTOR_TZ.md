# P2-C2 TZ — deterministic convergence presentation selector

Дата: 2026-07-31
Статус: implementation packet
Зависит от: packets 18–23, commit `ef7446af`.

## 1. Цель

Закрыть pure presentation-часть W2 после
`ledger → groups → tone`:

- `convergence_today`, если есть C1 hero;
- `quiet_day` во всех остальных валидных случаях;
- один `main_event` для rare anchor без C1-пары;
- 0–3 честных импульса quiet-day;
- не более трёх presentation-сфер;
- точный selected event set для будущих wire/LLM/snapshot
  слоёв.

Это выбор уже рассчитанной истины. Packet не меняет W1
eligibility, groups, tone или wire schema.

## 2. Exact write scope

Разрешено менять только:

1. новый
   `apps/api/app/services/today_convergence_selection.py`;
2. новый
   `apps/api/tests/test_today_convergence_selection.py`;
3. `grace/verification-matrix.md`;
4. `grace/knowledge-graph.xml`;
5. этот packet — reviewer-owned, не редактировать.

Нужен иной файл — остановиться и доложить. Кодер не коммитит и
не пушит.

## 3. Public entrypoint и immutable result

Ввести frozen records без compatibility aliases:

- `CanonicalSelectedConvergence`: canonical group, public polarity
  (`supportive|tense|mixed`) и ровно два selected evidence event IDs;
- `CanonicalSelectedEvent`: canonical unit, one canonical product sphere,
  public polarity и `evidence_level=medium`; один тип для
  `main_event`/impulse;
- `CanonicalSelectionAudit`: candidate/selected counts, steady exclusions,
  sphere-cap exclusions;
- `CanonicalSelectionResult`: `state`, selected convergence tuple,
  optional main event, impulse tuple, sorted-unique selected unit IDs,
  presentation-order selected spheres и audit;
- `TodayConvergenceSelectionError`: typed invariant/programming error.

Entry point:

```python
select_canonical_presentation(
    ledger: CanonicalLedger,
    grouping: CanonicalGroupingResult,
    tone: CanonicalToneResult,
    target_date: date,
    timezone_name: str,
    canon: TodayConvergenceCanon | None = None,
) -> CanonicalSelectionResult
```

Все input records обязаны ссылаться на один ledger: IDs уникальны,
group members равны ledger units, а set `tone.group_tones.group_id`
точно равен set grouping IDs. Invalid IANA timezone, naive datetime,
foreign/missing/duplicate reference и malformed API — typed error.

## 4. Normative ranking

### 4.1 Units

Presentation unit rank:

1. `strength` descending;
2. aware `exact_at`, переведённый в `timezone_name`, local datetime
   ascending;
3. date-only/absent time после timed units;
4. `canonical_event_id` ascending.

Это concrete форма master D2: significance ↓ → local time ↑ → ID ↑.
Strength обязана быть finite 0..1. Unit presentation sphere — первая
её `product_spheres` по canonical sphere order; unmapped unit fail-closed на
boundary.

### 4.2 Groups

Group rank:

1. independent driver count descending;
2. `evidence_level`: high перед medium;
3. selected anchor strength descending;
4. primary sphere canonical order;
5. `group_id` ascending.

Для `convergence_today` первым всегда идёт best public-polarity
hero. Дальше можно добрать hero/medium groups по rank, но:

- всего не более 3 groups;
- union primary/secondary spheres не более 3;
- каждая secondary group добавляет минимум одну новую sphere;
- физическая group не дублируется.

Selected evidence pair:

- hero: exact `hero_anchor_id + hero_confirmation_id`;
- medium: `anchor_unit_id` + best-ranked member с другим
  `driver_key`;
- event IDs сортируются в semantic pair order anchor → confirmation,
  не алфавитно.

Pair members обязаны иметь public polarity; иначе secondary group
пропускается, а primary hero fail-closed.

## 5. State/main-event/impulses

### 5.1 Root state

- есть хотя одна `group.hero_eligible` → `convergence_today`;
- иначе → `quiet_day`, даже если medium groups есть;
- `unavailable` не создаётся selector'ом: typed failure позже
  проецируется orchestrator'ом в unavailable.

Hero state возвращает `main_event=None`, `impulses=()`.

### 5.2 Public polarity boundary

Wire разрешает только `supportive|tense|mixed`. Internal tone
`steady` нельзя выдавать за другую polarity:

- steady secondary group пропускается;
- steady unit не становится main event/impulse;
- если hero groups есть, но нет ни одной hero с public group
  polarity и public evidence pair, selector fail-closed
  `hero_without_public_polarity`.

Adapter replay следующего packet обязан измерить этот case; на frozen
corpus ожидается zero. Ни `steady→mixed`, ни смена calculation
state не допускаются.

### 5.3 Main event

Только в quiet:

- fresh `anchor_today`;
- `rare_anchor_eligible=true`;
- public unit polarity;
- best по unit rank;
- evidence level medium, потому что C1 не выполнен;
- максимум один.

Fresh = `anchor_today` или aware `exact_at` local date == target date;
date-only — exact equality. Naive datetime fail-closed.

### 5.4 Impulses

Только в quiet. Candidate pool для parity с frozen reference:

- если canonical groups есть — unique members всех groups;
- иначе — ledger units;
- только `impulse_eligible`, non-background, non-excluded, fresh,
  public polarity;
- duplicate semantic key схлопывается в best-ranked unit;
- main-event unit не дублируется как impulse;
- выбирать по rank до 3, пропуская candidate, который создаст
  четвёртую presentation sphere.

Fast Moon/Mercury/Venus остаются в impulses. Они не меняю hero и
day tone, что уже доказано upstream.

## 6. Determinism и ownership

- result и nested records frozen;
- output одинаков при permutation ledger/group inputs;
- selected unit IDs sorted unique; evidence pair order хранится отдельно;
- presentation sphere tuple — по первому appearance в selected blocks,
  не более 3;
- raw/background/unselected units остаются в audit upstream и не
  протекают в selection;
- ни compatibility properties, ни legacy imports, ни analysis imports.

## 7. Tests / acceptance

Обязательно доказать:

1. hero задаёт `convergence_today`; medium-only остаётся quiet;
2. first selected convergence — hero; secondary group добавляет новую
   sphere; caps 3 groups/3 spheres;
3. hero evidence pair exact anchor → confirmation; medium pair имеет
   distinct drivers;
4. mutation fixture 6: один rare anchor → `quiet_day + main_event`,
   не convergence;
5. legal `main_event + 3 impulses`, main unit не дублируется;
6. order strength ↓, IANA-local time ↑, ID ↑; input permutation stable;
7. Moon может быть impulse, steady не маппится в public polarity;
8. long-running supporting unit не становится импульсом сегодня;
9. fourth sphere candidate пропускается, а не обрезает group/unit;
10. steady-only hero fail-closed exact reason token;
11. naive datetime, invalid timezone, mismatched tone/group/ledger fail-closed;
12. frozen records и отсутствие compatibility aliases.

Команды:

```bash
cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_convergence_units.py \
  tests/test_today_convergence_ledger.py \
  tests/test_today_convergence_groups.py \
  tests/test_today_convergence_tone.py \
  tests/test_today_convergence_selection.py -q
cd ../..
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/today_convergence_selection.py \
  apps/api/tests/test_today_convergence_selection.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

## 8. Out of scope

- wire/Pydantic/generated contracts и event-time projection;
- adapter from legacy/raw Today factors;
- period context, personal flag, access/preview, snapshot/DB/API;
- LLM/pregen/frontend;
- W1 canon, group/tone coefficients;
- `unavailable` envelope creation;
- full corpus parity (следующий adapter/replay packet).
