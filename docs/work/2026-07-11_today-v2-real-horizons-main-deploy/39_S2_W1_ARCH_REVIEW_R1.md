# S2.W1 Architect Review R1 — real timing corrections and acceptance closure

Дата: 2026-07-11
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Base HEAD, который обязан остаться неизменным до отдельного разрешения:
`1f8fc1e2e0e7ddcb96706a1934f65eb5ea4f20e4`
Исходное implementation ТЗ:
`36_S2_W1_REAL_TIMING_IMPLEMENTATION_TZ.md`
Статус review: **REJECTED — corrections required before commit/push**.

## 0. Режим работы

1. Исправлять только незакоммиченный diff S2.W1.
2. Не начинать shared-contract migration, horizons, actions, API copy или frontend.
3. Запрещены `git commit`, `git push`, merge/rebase, switch/checkout другой ветки.
4. Не stage файлы до отдельной команды архитектора.
5. Не изменять и не удалять unrelated paths:
   - `.grace/`;
   - `artifacts/design/`;
   - `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`;
   - `grace.db`;
   - `skills/`.
6. Сохранить уже реализованные версии:
   - `ss-calc-1.2.0`;
   - `al-1.1`;
   - `ss-scoring-2.0` без изменений.
7. Полностью прочитать этот review и исходное ТЗ. Если указания конфликтуют,
   этот review уточняет исходное ТЗ только в перечисленных ниже местах.

## 1. Blocking correctness defect: ложный transit branch debug

### 1.1 Факт

В `activation_builder.py` успешный debug сейчас строится через условие вида:

```py
value == value
```

Оно всегда истинно. В результате каждый transit записывает:

```text
selected_branch = plus
selected_exact_longitude = target + aspect
```

даже когда solver фактически выбрал `minus` branch.

Независимая проверка уже воспроизвела реальный случай:

```text
activation: t2n__SUN__TRINE__MERCURY
solver-selected branch: minus
actual selected longitude: approximately 105.7046
current debug longitude: approximately 345.704604
```

Это не косметика. Debug является evidence/audit trace и не имеет права лгать о
математической ветви, на которой рассчитаны exact/window timestamps.

### 1.2 Обязательное исправление

Расширить внутренний immutable result:

```py
@dataclass(frozen=True)
class TransitTimingResult:
    active_from_utc: str
    exact_at_utc: str | None
    active_until_utc: str
    occurrence_index: int | None
    exact_hits_in_window: tuple[str, ...]
    phase: TransitPhase
    applying: bool
    selected_branch: Literal["plus", "minus"]
    selected_exact_longitude: float
    warning_code: str | None = None
```

`TransitTimingSolver.solve()` обязан вернуть ровно `selected_branch` и
`selected_lon`, которые он использовал для residual/root solving.

Builder обязан проецировать значения без повторного выбора ветви:

```py
"selected_branch": timing_result.selected_branch,
"selected_exact_longitude": round(
    timing_result.selected_exact_longitude,
    6,
),
```

Запрещено повторять branch-selection formula в builder.

### 1.3 Обязательные тесты

Добавить unit/integration proofs минимум для двух направлений:

1. synthetic/controlled `plus` case;
2. synthetic или real `minus` case.

Для каждого доказать:

```text
debug selected_branch == solver result selected_branch
debug selected_exact_longitude == solver selected longitude within 1e-6 degree
abs(signed_delta(source longitude at exact_at, selected longitude)) <= tolerance
```

Включить regression assertion на реальный minus-case или столь же сильный
детерминированный controlled case. Тест не должен просто проверять enum membership.

## 2. Remove misleading/dead debug implementation

### 2.1 Unused local object

В конце solver создаётся `debug_timing`, но объект не возвращается и не
используется. Удалить его. Один источник debug values — поля result, которые
builder явно проецирует в public `debug.timing`.

Удалить временные комментарии вроде:

```text
wait, we can just compute it
let's just make it simple
Wait, since result is frozen...
```

Product code не должен содержать transcript/thinking notes.

### 2.2 `applying_probe_days`

На successful solver path не было старого `+0.1 day` probe. Поэтому success
debug не должен утверждать:

```py
"applying_probe_days": 0.1
```

Правило:

- success solver: ключ отсутствует;
- typed failure fallback, где probe реально выполнялся: ключ может быть `0.1`;
- тест должен доказать это различие.

### 2.3 Near-miss warning semantics

`no_exact_hit_in_window` — успешный математический near-miss result, не
`TransitTimingError`.

Требуется:

- boundaries остаются заполненными;
- `exact_at=None`;
- `debug.timing.warning_code == "no_exact_hit_in_window"`;
- не добавлять этот code в layer `warnings`, если solver не бросал typed error;
- typed failure по-прежнему добавляет deterministic layer warning
  `transit_timing:<activation_id>:<code>`.

Добавить тест, различающий эти два канала.

## 3. Blocking acceptance gap: required sidecar tests отсутствуют

Нынешние synthetic solver tests полезны, но не закрывают обязательную
интеграционную матрицу исходного ТЗ. Нельзя заменять перечисленные проверки
ручным запуском или общим `175 passed`.

### 3.1 Real Swiss transit integration

В существующем подходящем test module (`test_activation_transits.py` и/или
новом focused integration module) добавить:

1. Basil request, target `2026-07-08`:
   - найти прежний Moon opposition Pluto activation ID;
   - timing fields non-null;
   - target лежит внутри inclusive window;
   - `phase`, `applying`, selected exact occurrence согласованы;
   - debug branch/residual правдивы.
2. Real Moon short-window proof.
3. Real slow-source proof для Pluto/Uranus/Neptune хотя бы одного source:
   - fixed real source longitude at target JD;
   - conjunction solver;
   - exact near target;
   - bounded window.
4. `transit_planet_in_house` timing остаётся полностью null.
5. Полная повторная сборка одного request даёт byte-identical:
   - activation order;
   - all timing strings;
   - phase/applying;
   - warnings;
   - timing debug.

### 3.2 Profections

Обновить `apps/solarsage/tests/test_profections.py` реальными wire assertions:

- Basil annual `2025-10-30 .. 2026-10-29`;
- Basil monthly `2026-06-30 .. 2026-07-29`;
- house и lord каждой техники имеют identical timing;
- target находится внутри inclusive range;
- birth `2000-02-29`, target `2026-02-28` даёт
  `2026-02-28 .. 2027-02-27`;
- leap-year target сохраняет `02-29`;
- Jan-31 monthly sequence не дрейфует через Feb к 28-му числу следующих
  месяцев;
- повторный request возвращает identical timing.

Существующие tests возраста/домов сохраняются; новые assertions не заменяют их.

### 3.3 Firdar

Обновить `apps/solarsage/tests/test_firdar.py`:

- direct test inverse fractional-age bounds helper;
- exact integer birthday boundary;
- fractional boundary использует ceil-to-first-active-local-date;
- Feb-29 birth interval;
- `cycle_index > 0`;
- Basil major `2019-10-30 .. 2029-10-29`;
- Basil minor `2025-07-18 .. 2026-12-21`;
- target containment major/minor;
- builder house/lord evidence нужного периода получают identical boundaries;
- существующий proof `calculate_firdar` called once остаётся зелёным.

### 3.4 Solar return

Обновить `apps/solarsage/tests/test_solar_return.py`:

- target до birthday использует предыдущий уже начавшийся return, не future;
- target после birthday использует return текущего года;
- `current_return <= target < next_return`;
- `active_from == exact_at`;
- `active_until` ровно одна секунда перед serialized next return boundary;
- все evidence одного solar return имеют identical timing;
- Feb-29 birth search не падает и выбирает корректный current/next pair;
- поиск next instant не строит второй полный chart: spy/call-count для
  positions/houses;
- existing longitude residual precision сохраняется.

### 3.5 Lunar return

Обновить `apps/solarsage/tests/test_lunar_return.py`:

- current/next crossing ordering;
- `active_from == exact_at`;
- `active_until` одна секунда перед next crossing;
- все evidence current lunar return имеют identical timing;
- next crossing helper не строит второй full chart;
- existing longitude residual precision сохраняется.

### 3.6 Request-scoped call budget

Добавить integration test на representative full request из исходного ТЗ.

Он должен доказать структурно, а не по wall-clock:

- создан один `TransitTimingSolver` на request;
- successful activations не вызывают `calculate_positions(target + 0.1)`;
- position-cache misses имеют разумный documented upper bound;
- один `(planet_id, rounded_jd)` не считается повторно;
- 100+ transit activations не создают 100+ full-chart probe calculations;
- next return boundary helpers не строят второй chart.

Upper bound разрешено выбрать после измерения, но оставить минимум 25% запаса
от наблюдаемого deterministic count и объяснить его в тесте.

## 4. API/contracts acceptance coverage

Сохранить уже добавленный timed byte-for-byte parity test и добавить/проверить:

1. API принимает sidecar `al-1.1`/`ss-calc-1.2.0`.
2. Instant `Z` timestamps проходят без изменения.
3. Date-only strings проходят без timezone conversion.
4. `id`, timing, phase, applying и debug branch сохраняются вместе.
5. Historical explicit `al-1.0` fixtures остаются backward-compatibility input.
6. Local API fallback оставляет timing null.
7. Current default/live version tests используют новые constants.
8. Generated OpenAPI/TS/Zod diff содержит только ожидаемое default/version
   изменение; timing fields не дублируются заново.

Не ослаблять timestamp assertions до `startswith`/date prefix. Использовать
numeric UTC tolerance там, где Swiss/root solver допускает tolerance.

## 5. GRACE/static quality corrections

### 5.1 `transit_timing.py`

- удалить unused imports (`math`, `Any` и другие реально неиспользуемые);
- привести typing к современным builtin generics, если это не раздувает diff;
- добавить function contracts для нетривиальных public constructors/methods:
  `TransitTimingError`, `TransitPositionCache.get`, `TransitTimingSolver.solve`;
- module contract должен честно описывать Swiss Ephemeris side effect/cost, а не
  называть production calculation полностью pure;
- module map должен соответствовать фактическим public entrypoints/tests.

### 5.2 `firdar.py`

Добавить в module map:

```text
FirdarPeriodBounds
calculate_firdar_period_bounds
```

Добавить function contract helper, если его ещё нет или он неполный.

### 5.3 `returns.py`

Добавить в module map:

```text
find_solar_return_jd
find_next_lunar_return_jd
```

Удалить ставшие unused `datetime`, `timezone` и другие imports. Module contract
должен явно включать current/next instant helpers.

### 5.4 Builder imports/reuse

- не добавлять локальные повторяющиеся imports внутри каждой activation ветви,
  если dependency статична;
- не пересчитывать natal positions исключительно ради natal Sun longitude,
  если уже существующий request-scoped natal result содержит эту величину;
- не менять astronomy result ради микрооптимизации; reuse должен быть явным и
  покрытым тестом.

## 6. Mandatory benchmark

Выполнить исходный protocol без HTTP/systemd:

1. 3 warm-up runs;
2. 20 measured runs в одном Python process;
3. report p50, p95, max milliseconds;
4. activation count;
5. transit aspect activation count;
6. representative solver cache misses/call-budget result.

Acceptance:

```text
p95 < 2000 ms
```

Не добавлять временный benchmark script в product tree. Использовать heredoc
только для execution либо существующий audit/performance script; после команды
никакого временного файла не должно остаться.

## 7. Mandatory gates

### 7.1 Sidecar focused

```bash
cd apps/solarsage
python -m pytest \
  tests/test_transit_timing.py \
  tests/test_activation_transits.py \
  tests/test_profections.py \
  tests/test_firdar.py \
  tests/test_solar_return.py \
  tests/test_lunar_return.py \
  tests/test_activation_layer_endpoint.py -q
```

### 7.2 Sidecar full

```bash
cd apps/solarsage
python -m pytest tests/ -q
```

### 7.3 API focused and full

```bash
cd apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_activation_contracts.py \
  tests/test_activation_layer_contract.py \
  tests/test_activation_layer_transits.py \
  tests/test_activation_layer_profections.py \
  tests/test_activation_layer_firdar.py \
  tests/test_activation_layer_returns.py \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_pipeline_invariants.py -q
python -m pytest tests/ -q
```

### 7.4 Generated/web/static

```bash
pnpm contracts:check
npx vitest run __tests__/contracts
npx tsc --noEmit
git diff --check
git status --short
git diff --cached --stat
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
```

Требования:

- index empty;
- HEAD и origin feature остаются base SHA;
- никакого commit/push;
- no binary product paths;
- unrelated untracked paths сохранены.

## 8. Evidence callback

После всех исправлений вернуть в tmux:

```text
READY_S2_W1_REAL_TIMING_R1
branch: preview/solarsage-v2-human-first-navigator-ux
head: <sha>
origin_feature: <sha>
branch_debug_plus: PASS <test>
branch_debug_minus: PASS <test and selected longitude>
near_miss_channel: PASS
typed_failure_channel: PASS
real_moon: <id/timing/phase proof>
real_slow_planet: <proof>
profections: <Basil/Feb29/Jan31 proof>
firdar: <Basil/cycle/Feb29 proof>
solar_return: <pre/post birthday and next-bound proof>
lunar_return: <next-bound proof>
return_full_chart_reuse: PASS <call counts>
request_solver_reuse: PASS <call counts>
api_sidecar_parity: PASS
sidecar_focused: <total/time>
sidecar_full: <total/time>
api_focused: <total/time>
api_full: <total/time>
contract_tests: <result>
typecheck: PASS
benchmark: runs=20 p50=<ms> p95=<ms> max=<ms>
real_json_excerpts: <compact four-technique proof>
diff_paths: <exact task paths>
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

После callback остановиться. Architect независимо прочитает diff, повторит
гейты и только затем решит, разрешать ли commit/push.
