# S2.W1 Architect Review R2 — lazy transit grids and strict return invariants

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Base HEAD, который обязан остаться неизменным до отдельного разрешения:
`1f8fc1e2e0e7ddcb96706a1934f65eb5ea4f20e4`
Предыдущий review: `39_S2_W1_ARCH_REVIEW_R1.md`
Статус: **REJECTED — небольшой correction pass обязателен до acceptance**.

## 0. Режим и scope

1. Исправлять только текущий незакоммиченный S2.W1 diff.
2. Не начинать Stage A, Stage B, horizons/actions, frontend или shared package.
3. Запрещены `git add`, `git commit`, `git push`, merge/rebase/switch.
4. Не менять production/dev runtime, systemd, nginx, Docker и порты.
5. Не изменять unrelated paths:
   - `.grace/`;
   - `artifacts/design/`;
   - `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`;
   - `grace.db`;
   - `skills/`.
6. Не чинить в этой волне baseline failures API из секции 5.
7. Полностью прочитать `36`, `39`, `41` и этот файл. Этот review уточняет
   только перечисленные ниже пункты.

## 1. Что из R1 уже принято и не должно быть сломано

Независимый review подтвердил:

- truthful `plus`/`minus` branch projection;
- `selected_exact_longitude` приходит из immutable solver result;
- success path не публикует ложный `applying_probe_days`;
- near-miss остаётся successful result и не попадает в layer warnings;
- typed failure сохраняет activation и добавляет deterministic warning;
- реальные Moon и minus-branch proofs проходят;
- profection/firdar/solar/lunar golden timing сейчас проходит;
- sidecar full: `194 passed, 1 warning`;
- API focused: `121 passed`;
- contract Vitest: `128 passed`;
- TypeScript typecheck: PASS;
- contract generation дважды byte-identical;
- generated diff содержит только `al-1.0 -> al-1.1` default;
- index пуст, HEAD/origin не изменены.

Не переписывать уже работающую математику branch/root/window без необходимости.

## 2. Blocking architecture defect: grid заранее строится до max horizon

### 2.1 Факт

`TransitTimingSolver._get_grid()` сейчас при первом обращении безусловно строит
всю сетку планеты до максимального горизонта:

```py
while direction * (horizon_limit - jd) > 0:
    ...
    grid.append(...)
```

После этого `solve()` ищет первый outside sample уже в полностью построенном
массиве. Это не соответствует обязательному design из `36`, где сетка должна:

- начинаться от общего `target_jd`;
- останавливаться на первом outside sample конкретного текущего window;
- при следующем target той же планеты переиспользоваться;
- расширяться дальше только если уже накопленных samples недостаточно.

Независимое измерение текущего representative request:

```text
cache_misses = 29335
```

Wall-clock gate пока проходит, но request платит за десятилетия/годы
эфемерид, которые большинству active windows не нужны. Это особенно заметно
на Uranus/Neptune/Pluto и ухудшит concurrency sidecar.

### 2.2 Обязательная реализация

Сохранить один request-scoped grid на `(planet_id, direction)`, но сделать его
лениво расширяемым.

Допустимая структура:

```py
self.grids[(planet_id, direction)] = [target_position]
```

Для каждого `solve()` и каждого направления:

1. Просканировать уже существующие samples от target наружу.
2. Если для текущих `selected_lon/max_orb` первый outside уже есть — вернуть
   его index без новых Swiss calls.
3. Если outside ещё нет — добавлять ровно по одному adaptive sample с той же
   policy table.
4. После каждого нового sample сразу проверять outside для текущего window.
5. Остановиться сразу на первом outside.
6. Если достигнут planet max horizon — typed
   `boundary_not_bracketed_backward|forward`.
7. Если исчерпан общий cap сетки — typed
   `coarse_sample_budget_exhausted`.

Важно:

- grid step зависит только от position/speed и policy, поэтому общий grid
  остаётся валидным для всех targets/aspects одной source planet;
- нельзя создавать отдельную grid на target longitude/aspect;
- нельзя удалять position cache;
- порядок samples строго монотонный;
- первый outside для конкретного aspect нельзя заменять более дальним outside
  после retrograde re-entry;
- публичные timing strings, branch selection и occurrence semantics не меняются.

### 2.3 Обязательные regression tests

Добавить direct test, который реально отличает lazy expansion от нынешнего
full-horizon precompute:

1. Synthetic slow source (`Pluto` либо `Neptune`) с узким nearby window.
2. Первый solve должен закончиться после малого числа provider calls, а не
   строить весь 20k/12k-day horizon.
3. Второй solve той же planet:
   - использует накопленный prefix;
   - расширяет его только если нужно;
   - не пересчитывает существующие `(planet_id, rounded_jd)`.
4. Проверить, что cached grid после первого solve заканчивается первым outside
   sample для этого window, а не horizon limit.

После реализации повторно измерить representative full request и задать новый
documented upper bound с минимум 25% headroom. Нельзя оставить bound `37000`,
если lazy design фактически уменьшил count.

## 3. Blocking correctness gap: next lunar crossing не гарантированно next

### 3.1 Факт

`find_next_lunar_return_jd()` проверяет только:

```py
jd > 0
residual <= 0.001
```

Но контракт и исходное ТЗ требуют строго:

```text
jd > after_jd
```

Epsilon снижает вероятность повторного crossing, но не является invariant
guard. Provider может вернуть ту же границу из-за своей численной tolerance.

### 3.2 Исправление

После `mooncross_ut` добавить явную проверку:

```py
if jd <= after_jd:
    raise ValueError(...stable deterministic message...)
```

Добавить unit test с monkeypatched `mooncross_ut`, который возвращает ровно
`after_jd`; helper обязан отказать, даже если longitude residual идеален.

В builder после получения current/next JD явно проверить для обоих return
типов:

```text
current_return_jd <= target_jd < next_return_jd
```

Нарушение — deterministic `ValueError`; не сериализовать ложное окно.

Добавить focused tests на эти guards. Реальные existing precision tests
сохранить.

## 4. Acceptance coverage, которое ещё не закрыто

### 4.1 Solar return: запрещённые prefix assertions

`test_solar_return_current_previous_before_birthday_and_same_year_after`
использует четыре `startswith(...)`. `39`, section 4, прямо запрещает ослаблять
timestamp assertions до date prefix.

Заменить их на:

- canonical full UTC-Z strings и/или numeric JD comparison с tolerance <= 1s;
- `current <= target < next` для pre- и post-birthday requests;
- `active_from == exact_at`;
- `active_until == parsed(next_return_utc_iso) - 1 second`.

Текущие deterministic Basil values, полученные независимым запуском:

```text
target 2026-07-08:
  current = 2025-10-30T14:24:27Z
  next    = 2026-10-30T20:17:07Z

target 2026-11-01:
  current = 2026-10-30T20:17:07Z
  next    = 2027-10-31T02:04:52Z
```

Если тест использует exact strings, использовать именно полные строки.

### 4.2 Feb-29 solar pair

Нынешний `test_feb29_solar_return_search_does_not_crash` проверяет только один
standalone chart. Исходный acceptance требует корректный current/next pair.

Добавить endpoint/builder proof для Feb-29 birth:

- current return не позже target;
- next return строго позже target;
- оба timestamp canonical `Z`;
- current/next соответствуют cheap helpers нужных лет;
- один full chart, next остаётся instant-only helper.

Не нужно hardcode выдуманные жизненные данные или UI copy.

### 4.3 Firdar boundary proof

Существующие exact-age tests проверяют lord switch, но не проверяют inverse
bounds helper на целой границе.

Добавить прямой test `calculate_firdar_period_bounds` для exact integer
birthday boundary:

- новый period `active_from` равен дню рождения;
- предыдущий inclusive end был бы предыдущим local date;
- target лежит в returned major/minor bounds.

Сохранить fractional ceil, Feb-29 и cycle-index tests.

### 4.4 Static/GRACE cleanup в изменённых местах

Без расширения scope:

- переместить новые `dataclass`, `timedelta`, `ceil/floor`, `calendar`, `Date`
  imports в обычные module import sections;
- не оставлять новый `from datetime import timedelta` внутри profection branch;
- `TransitTimingSolver.solve` contract не должен говорить
  `side_effects: none (mutates ...)`; явно указать cache/grid mutation и Swiss
  calls on misses;
- return helper contracts должны честно указывать Swiss Ephemeris calls и
  `swe.set_ephe_path`;
- убрать/переименовать реально unused local `best_residual`;
- сохранить GRACE module maps актуальными.

## 5. API full suite: доказанный baseline red, не scope S2.W1

Независимый полный API run на текущем worktree:

```text
6 failed, 830 passed, 5 skipped
```

Те же самые шесть failures независимо воспроизведены в detached clean
worktree на base SHA `1f8fc1e2...`:

```text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
```

Следствие:

- это не regression текущего S2.W1 diff;
- в S2.W1 запрещено менять calendar/semantic/today implementation или эти
  старые tests ради зелёного отчёта;
- focused API gate обязан быть полностью зелёным;
- full API callback честно указывает `BASELINE_RED_IDENTICAL`;
- до финального merge/deploy будет отдельная scoped baseline-stabilization
  wave, потому что `main` release всё равно требует all-green.

Если после corrections набор/trace этих failures изменится или появится новый
failure — это regression и callback не принимается.

## 6. Обязательные gates после corrections

### 6.1 Sidecar focused/full

```bash
cd apps/solarsage
venv/bin/python -m pytest \
  tests/test_transit_timing.py \
  tests/test_activation_transits.py \
  tests/test_profections.py \
  tests/test_firdar.py \
  tests/test_solar_return.py \
  tests/test_lunar_return.py \
  tests/test_activation_layer_endpoint.py -q
venv/bin/python -m pytest tests/ -q
```

### 6.2 API focused/full

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

Expected full API result: те же 6 baseline failures и ни одного нового.

### 6.3 Contracts/static

Повторить protocol из `41`:

- double `pnpm contracts:generate`;
- identical three hashes;
- exact default-only generated diff;
- `npx vitest run __tests__/contracts`;
- `npx tsc --noEmit`;
- `git diff --check`;
- empty index;
- HEAD/origin feature всё ещё base SHA.

### 6.4 Benchmark

Повторить 3 warm-up + 20 measured runs в одном process.

Report:

- p50/p95/max;
- activation count;
- transit aspect count;
- cache misses/hits/unique keys;
- old vs new cache miss count;
- `p95 < 2000 ms`.

## 7. Callback

Вернуть:

```text
READY_S2_W1_REAL_TIMING_R2
branch: preview/solarsage-v2-human-first-navigator-ux
head: 1f8fc1e2e0e7ddcb96706a1934f65eb5ea4f20e4
origin_feature: 1f8fc1e2e0e7ddcb96706a1934f65eb5ea4f20e4
lazy_grid: PASS <direct test and first/second provider counts>
full_request_cache: old=29335 new=<count> bound=<count>
lunar_strict_next: PASS
solar_pre_post_exact: PASS <full UTC values>
solar_feb29_pair: PASS
firdar_integer_bounds: PASS
sidecar_focused: <result>
sidecar_full: <result>
api_focused: <result>
api_full: BASELINE_RED_IDENTICAL <6 fail, pass/skip counts>
contract_generation_idempotent: PASS <three hashes>
generated_diff: EXPECTED al-1.0 -> al-1.1 only
contract_tests: PASS
typecheck: PASS
benchmark: runs=20 p50=<ms> p95=<ms> max=<ms>
index: EMPTY
commit: NOT_YET
push: NOT_YET
```

После callback остановиться. Architect повторно читает exact diff и только
потом выдаёт acceptance/commit instruction.
