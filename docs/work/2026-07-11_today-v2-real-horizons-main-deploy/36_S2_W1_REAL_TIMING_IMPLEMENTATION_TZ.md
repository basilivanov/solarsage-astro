# S2.W1 Implementation TZ — real timing truth in sidecar

Дата: 2026-07-11  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Ожидаемый base HEAD: `1f8fc1e2e0e7ddcb96706a1934f65eb5ea4f20e4`  
Master: `20_STAGE_2_REAL_HORIZONS_TZ.md`, секция `S2.W1`  
Статус: implementation task for coder; architect review required before commit.

## 0. Режим работы и жёсткие ограничения

1. Работать только в текущей preview-ветке.
2. Product code реализует coder. Architect после callback независимо читает diff,
   запускает гейты и выдаёт отдельное разрешение на commit/push.
3. В этом задании запрещены:
   - `git commit`;
   - `git push`;
   - merge/rebase/cherry-pick;
   - checkout/switch другой ветки;
   - любые изменения `main`;
   - restart systemd/nginx/Docker;
   - ручной `uvicorn`;
   - изменение production/dev runtime на портах 8000/3002/3003/18091;
   - frontend/UI/horizon copy/fixture implementation;
   - добавление зависимостей;
   - линейное вычисление срока через `orb / current_speed`;
   - массовая замена всех старых `al-1.0`/`ss-calc-1.1.0` в fixtures.
4. Не трогать и не удалять unrelated untracked paths:
   - `.grace/`;
   - `artifacts/design/`;
   - `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`;
   - `grace.db`;
   - `skills/`.
5. До начала проверить:

   ```bash
   git branch --show-current
   git rev-parse HEAD
   git status --short
   ```

   Если tracked worktree уже изменён не этой задачей — остановиться и сообщить.
6. Не начинать S2.W2. Итог этого turn — только готовый незакоммиченный S2.W1.

## 1. Результат волны

После этой волны sidecar обязан реально заполнять:

```text
ActivationEvidence.active_from
ActivationEvidence.exact_at
ActivationEvidence.active_until
```

для следующих техник:

| Technique | active_from | exact_at | active_until |
|---|---|---|---|
| `transit_to_natal` | начало текущего непрерывного orb-window, UTC | выбранное точное прохождение в этом window, UTC или null при подтверждённом near-miss | конец текущего непрерывного orb-window, UTC |
| `transit_to_angle` | то же | то же | то же |
| `transit_to_lot` | то же | то же | то же |
| `annual_profection` | текущий день рождения, local date | null | день перед следующим днём рождения, local date |
| `monthly_profection` | текущая недрейфующая месячная годовщина | null | день перед следующей годовщиной | 
| `firdar_major` | первый local date текущего major-периода | null | последний local date текущего major-периода |
| `firdar_minor` | первый local date текущего minor-периода | null | последний local date текущего minor-периода |
| `solar_return` | точный момент текущего, уже начавшегося return | тот же момент | 1 секунда перед следующим solar return |
| `lunar_return` | точный момент текущего return | тот же момент | 1 секунда перед следующим lunar return |

В этой волне timing остаётся `null` у:

- `transit_planet_in_house`;
- secondary progressions;
- solar arc;
- primary directions;
- eclipses;
- любых иных техник, для которых это ТЗ не задаёт проверенный solver.

Нельзя выдумывать даты для таких evidence.

## 2. Wire semantics

### 2.1 Instant fields

Для транзитов и returns:

```text
YYYY-MM-DDTHH:MM:SSZ
```

Требования:

- только UTC;
- суффикс строго `Z`, не `+00:00`;
- timezone-aware semantics;
- точность сериализации до секунды;
- одинаковый input даёт byte-identical строки.

### 2.2 Date-only fields

Для profection/firdar:

```text
YYYY-MM-DD
```

Это local calendar date в `target_tz`; конвертировать её в UTC midnight нельзя.

### 2.3 Границы

- `active_from` и `active_until` — включительные пользовательские границы.
- У instant-return периода следующий return является exclusive boundary;
  поэтому wire `active_until = next_return_jd - 1 second`.
- Для date-only периода end-exclusive date преобразуется в
  `active_until = end_exclusive - 1 day`.
- При полном timing должны выполняться:

  ```text
  active_from <= target <= active_until
  active_from <= exact_at <= active_until   # если exact_at не null
  ```

- Period evidence имеет `phase="period"`, `applying=None`.
- У transit evidence `phase`, `applying`, `exact_at` должны описывать одно и то
  же выбранное occurrence.

## 3. Версии и canonical contract

Поля уже были additive-promoted в S1.W3. Повторно добавлять/переименовывать их
нельзя. В S2.W1 меняются реальное calculation behavior и версии.

Установить одновременно:

```py
CALCULATION_VERSION = "ss-calc-1.2.0"
ACTIVATION_LAYER_VERSION = "al-1.1"
```

Обязательные runtime/default locations:

```text
apps/solarsage/solarsage/core/versions.py
apps/api/app/core/versions.py
apps/solarsage/solarsage/schemas/activation.py
apps/api/app/schemas/activation.py
apps/solarsage/solarsage/api/activation_layer.py
```

`SCORING_V2_VERSION` остаётся `ss-scoring-2.0`.

`schema_version` остаётся `activation-layer.v1`: wire shape additive и поля уже
существуют в schema.

После API default/version changes выполнить canonical regeneration. Разрешённый
generated diff:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
```

Важно: explicit historical fixtures с `al-1.0`/`ss-calc-1.1.0` являются
backward-compatibility inputs и не должны автоматически переписываться. Менять
literal следует только там, где тест проверяет текущий live/default runtime
identity. Не делать repository-wide replace.

## 4. Архитектурное разделение

### 4.1 Source of truth

```text
Pydantic API schemas
  -> deterministic OpenAPI
  -> generated TypeScript + generated Zod
```

Не добавлять ручные TS timing types и не менять Stage 1 pipeline.

### 4.2 Calculation ownership

```text
activation_builder.py
  orchestration only
  creates one request-scoped transit solver
  attaches returned timing to evidence

transit_timing.py
  all transit window/exact-hit numerical work
  Swiss Ephemeris single-planet position cache
  branch selection, coarse walk, refinement, phase consistency

firdar.py
  inverse of the existing birthday-interval age arithmetic
  major/minor inclusive date bounds

returns.py
  reusable exact return-instant helpers
  current/next return selection

ephemeris.py
  shared Julian Day -> canonical UTC-Z formatter
```

Нельзя помещать numerical root solving в frontend, API service или
`activation_builder.py`.

### 4.3 Performance ownership

На один `build_activation_layer(...)` создаётся ровно один request-scoped
`TransitTimingSolver`. Он переиспользуется для всех `transit_to_*` activations.

У solver должны быть два уровня reuse:

1. position cache: один `(source_planet, jd)` считается Swiss Ephemeris только
   один раз;
2. outward sample grid: для каждой `(source_planet, direction)` coarse samples
   начинаются от общего `target_jd`, зависят только от planet position/speed и
   постепенно расширяются. Все targets/aspects этой source planet читают одну
   и ту же сетку вместо независимых scans.

Это обязательное условие: representative full request сейчас содержит около
101 transit aspect activation. Сто отдельных несогласованных scans архитектурно
не принимаются.

## 5. Canonical UTC formatter

В `apps/solarsage/solarsage/utils/ephemeris.py` добавить публичную чистую
функцию с GRACE function contract:

```py
def julian_day_to_utc_iso(jd: float) -> str:
    ...  # YYYY-MM-DDTHH:MM:SSZ
```

Допустимая реализация без ручной calendar arithmetic:

```py
unix_seconds = (jd - 2440587.5) * 86400.0
dt = datetime.fromtimestamp(unix_seconds, tz=timezone.utc)
return dt.isoformat(timespec="seconds").replace("+00:00", "Z")
```

Требования:

- не создавать naive datetime;
- не оставлять `+00:00`;
- ошибка конвертации относительно JD < 1 секунды;
- `returns.py` и `transit_timing.py` используют эту функцию;
- старый `_jd_to_utc_iso` в `returns.py` удалить либо сделать тонким alias,
  но не держать две расходящиеся реализации.

Добавить unit test на известный JD и обязательный `endswith("Z")`.

## 6. Transit timing service

Создать:

```text
apps/solarsage/solarsage/services/transit_timing.py
```

Новый файл обязан иметь полный `AI_HEADER`, `START_MODULE_CONTRACT`,
`START_MODULE_MAP`, function contracts и semantic blocks согласно root
`AGENTS.md`.

### 6.1 Public data contract

Рекомендуемая точная форма; имена можно сохранить именно такими:

```py
from dataclasses import dataclass
from typing import Literal

TransitPhase = Literal["applying", "exact", "separating"]

@dataclass(frozen=True)
class TransitTimingResult:
    active_from_utc: str
    exact_at_utc: str | None
    active_until_utc: str
    occurrence_index: int | None
    exact_hits_in_window: tuple[str, ...]
    phase: TransitPhase
    applying: bool
    warning_code: str | None = None
```

Semantics:

- `exact_hits_in_window` строго отсортирован по UTC по возрастанию;
- `occurrence_index` — zero-based index выбранного `exact_at_utc` в этом tuple;
- если математически подтверждён near-miss без exact root:
  - boundaries сохраняются;
  - `exact_at_utc=None`;
  - `occurrence_index=None`;
  - `exact_hits_in_window=()`;
  - `warning_code="no_exact_hit_in_window"`.

### 6.2 Typed failures

Добавить typed exception, например:

```py
class TransitTimingError(RuntimeError):
    code: str
```

Стабильные codes:

```text
unsupported_planet
target_outside_orb
boundary_not_bracketed_backward
boundary_not_bracketed_forward
coarse_sample_budget_exhausted
```

Не включать в warning nondeterministic Python exception repr.

`activation_builder` ловит только `TransitTimingError`. Неожиданные ошибки
программирования не swallowing и продолжают падать через существующий endpoint
error policy.

При typed failure:

- activation не удаляется;
- ID/orb/strength/polarity не меняются;
- три timing fields остаются `None`;
- добавить deterministic layer warning:

  ```text
  transit_timing:<activation_id>:<code>
  ```

- существующая ephemeris-based phase fallback допустима, но запрещено
  придумывать даты.

### 6.3 Position provider/cache

Production calculation:

```py
swe.calc_ut(jd, planet_id, swe.FLG_SWIEPH | swe.FLG_SPEED)
```

Не вызывать `calculate_positions(jd)` внутри solver: она считает все 10 планет
на каждый sample и разрушает performance budget.

Внутренняя immutable sample форма:

```py
@dataclass(frozen=True)
class TransitPosition:
    jd: float
    longitude: float
    speed_longitude: float
```

Кэш:

- canonicalize source name (`Moon`, `MOON` -> одна planet ID);
- key `(planet_id, round(jd, 10))`;
- longitude normalize в `[0, 360)`;
- provider/calculator injectable в constructor для deterministic synthetic tests;
- expose read-only `cache_hits`/`cache_misses` либо аналогичные counters для
  call-budget test, но не добавлять их в public wire contract.

### 6.4 Request-scoped solver API

```py
class TransitTimingSolver:
    def __init__(
        self,
        *,
        target_jd: float,
        position_cache: TransitPositionCache | None = None,
    ) -> None: ...

    def solve(
        self,
        *,
        source_planet: str,
        target_longitude: float,
        aspect_angle: float,
        max_orb: float,
    ) -> TransitTimingResult: ...
```

Не передавать user profile, house data или UI metadata в solver.

### 6.5 Signed angular math

Canonical helper:

```py
def signed_delta(lon: float, exact_lon: float) -> float:
    return ((lon - exact_lon + 180.0) % 360.0) - 180.0
```

Для aspect angle `A` и fixed target longitude `T` возможные exact branches:

```text
plus  = normalize(T + A)
minus = normalize(T - A)
```

Выбор branch на `target_jd`:

1. посчитать `abs(signed_delta(current_lon, plus))`;
2. посчитать то же для `minus`;
3. выбрать меньший;
4. deterministic tie -> `plus`;
5. для conjunction/opposition branches эквивалентны — canonical `plus`.

После выбора branch во всём текущем window использовать:

```text
residual(jd) = signed_delta(source_lon(jd), selected_exact_longitude)
inside(jd)   = abs(residual(jd)) <= max_orb + 1e-9
```

Внутри canonical orb <= 8° эта функция непрерывна и не имеет ложного
0°/360° jump.

Нельзя решать exact root через raw `angular_distance - aspect_angle` без
фиксации branch: на retrograde/multi-pass это создаёт неоднозначность.

### 6.6 Adaptive coarse grid

Использовать следующую обязательную policy table. Horizon указан на одно
направление от target; scan прекращается на первом outside sample.

| Planet | max horizon days | desired angular step | min step | max step |
|---|---:|---:|---:|---:|
| Moon | 5 | 0.50° | 5 min | 1 hour |
| Sun | 30 | 0.50° | 30 min | 6 hours |
| Mercury | 180 | 0.40° | 15 min | 6 hours |
| Venus | 300 | 0.40° | 30 min | 12 hours |
| Mars | 800 | 0.35° | 1 hour | 1 day |
| Jupiter | 1800 | 0.30° | 2 hours | 2 days |
| Saturn | 4000 | 0.25° | 4 hours | 4 days |
| Uranus | 8000 | 0.20° | 6 hours | 7 days |
| Neptune | 12000 | 0.15° | 8 hours | 10 days |
| Pluto | 20000 | 0.12° | 8 hours | 14 days |

Для каждого текущего sample:

```py
raw_days = desired_angular_step / max(abs(speed_longitude), speed_floor)
step_days = clamp(raw_days, min_step_days, max_step_days)
```

где `speed_floor = desired_angular_step / max_step_days`.

Дополнительно:

- hard cap `25_000` coarse samples на `(planet, direction)`;
- hard max horizon из таблицы;
- direction grids memoized и расширяются, а не строятся заново для каждого
  aspect target;
- backward JD строго убывают, forward JD строго возрастают;
- scan выбирает первый sampled outside относительно target, чтобы не перескочить
  к другому retrograde pass.

Таблицу не заменять одним одинаковым шагом для всех планет.

### 6.7 Boundary refinement

Найдя соседние samples `inside/outside`, уточнить crossing функции:

```text
f(jd) = abs(residual(jd)) - max_orb
```

bounded bisection:

- stop, когда bracket width <= 300 seconds;
- максимум 64 iterations;
- backward boundary вернуть inside-side endpoint (первая подтверждённая active
  точка с ошибкой <= 5 min);
- forward boundary вернуть inside-side endpoint (последняя подтверждённая active
  точка);
- обе строки сериализовать canonical UTC-Z formatter.

Так wire boundaries являются включительными и не выходят наружу orb-window.

### 6.8 Exact-hit enumeration

Внутри refined `[active_from_jd, active_until_jd]` собрать все coarse samples,
включая target и boundary endpoints, затем найти roots выбранного signed
`residual`.

Root candidates:

1. residual sign change между соседними samples;
2. sample с `abs(residual) <= 1e-5°`;
3. speed sign change: уточнить station time по `speed_longitude = 0`; если
   `abs(residual_at_station) <= 1e-5°`, считать tangent exact hit даже без
   residual sign change.

Для residual sign-change применять bounded bisection:

- максимум 64 iterations;
- stop при time bracket <= 60 seconds;
- вернуть midpoint;
- отсортировать roots;
- deduplicate hits, расстояние между которыми <= 120 seconds.

Near-miss, который вошёл в orb и развернулся до exact longitude, не является
ошибкой solver: вернуть полные boundaries, `exact_at=None` и typed warning code
`no_exact_hit_in_window`.

### 6.9 Occurrence selection и phase

Если roots есть:

1. выбрать root с минимальным `abs(root_jd - target_jd)`;
2. deterministic exact tie -> будущий root;
3. `occurrence_index` — его индекс в sorted roots;
4. если разница <= 60 seconds:
   - `phase="exact"`;
   - `applying=False`;
5. selected root позже target:
   - `phase="applying"`;
   - `applying=True`;
6. selected root раньше target:
   - `phase="separating"`;
   - `applying=False`.

Если roots нет, определить local direction по изменению `abs(residual)` на
ближайшем future probe из общей grid:

- уменьшается -> applying;
- иначе -> separating;
- `exact_at=None`.

Обязательные invariants:

```text
phase=applying   and exact_at != null -> exact_at >= target - 60 sec
phase=separating and exact_at != null -> exact_at <= target + 60 sec
phase=exact                          -> abs(exact_at-target) <= 60 sec
```

### 6.10 Debug projection

Не добавлять новые top-level wire fields. В существующий `debug` успешного
transit aspect добавить структурный объект:

```py
"timing": {
    "selected_branch": "plus" | "minus",
    "selected_exact_longitude": round(..., 6),
    "occurrence_index": int | None,
    "exact_hits_in_window": [...],
    "warning_code": str | None,
    "boundary_tolerance_seconds": 300,
    "exact_tolerance_seconds": 60,
}
```

Не помещать туда user data. Не дублировать cache содержимое.

## 7. Integration в activation builder

Файл:

```text
apps/solarsage/solarsage/services/activation_builder.py
```

### 7.1 Solver lifecycle

После вычисления `target_jd` создать один solver только если среди `active`
есть хотя бы одна из техник:

```text
transit_to_natal
transit_to_angle
transit_to_lot
```

Не создавать solver для profection-only/firdar-only request.

### 7.2 Transit aspect flow

Сохранить текущую логику:

- candidate detection;
- aspect name;
- current orb;
- strength;
- polarity;
- evidence string;
- stable activation ID;
- indexing;
- iteration order.

После выбора `best_aspect` вызвать request-scoped solver с:

```text
source_planet=tname
target_longitude=tlon_target
aspect_angle=ASPECT_ANGLES[best_aspect]
max_orb=max_orb
```

При success:

- phase/applying брать только из result;
- заполнить все три timing fields;
- добавить timing debug.

При typed failure:

- сохранить текущий ephemeris probe phase fallback;
- timing null;
- warning по формату из §6.2;
- debug `timing.warning_code`.

Нельзя для success продолжать делать существующий `calculate_positions` на
`target_jd + 0.1` для каждой activation. Это считает весь chart 100+ раз и
нарушает request-scoped solver design.

### 7.3 Builder helper

Расширить `_build_aspect_activation` параметрами:

```py
active_from: str | None
exact_at: str | None
active_until: str | None
```

и передавать их напрямую в `ActivationEvidence`.

### 7.4 Compatibility

- Transit IDs не меняются.
- Current orb/strength/polarity не меняются.
- `transit_planet_in_house` timing остаётся null.
- Layer warning order deterministic, совпадает с activation traversal order.
- Одинаковый request дважды даёт одинаковый activation order, timing и warnings.

## 8. Annual/monthly profection boundaries

Использовать уже существующие helpers в `activation_builder.py`:

```text
safe_replace_year
_add_months_with_clamp
```

Не создавать альтернативную month arithmetic.

### 8.1 Annual

Один раз вычислить:

```py
annual_start = safe_replace_year(birth_local, target_local.year)
if annual_start > target_local:
    annual_start = safe_replace_year(birth_local, target_local.year - 1)
annual_next = safe_replace_year(birth_local, annual_start.year + 1)
annual_until = annual_next - timedelta(days=1)
```

Присвоить одинаковые values house и lord evidence:

```text
active_from = annual_start.isoformat()
exact_at = None
active_until = annual_until.isoformat()
```

### 8.2 Monthly

Использовать существующий `annual_year_start` и
`completed_month_steps` без изменения house calculation:

```py
monthly_start = _add_months_with_clamp(annual_year_start, completed_month_steps)
monthly_next = _add_months_with_clamp(annual_year_start, completed_month_steps + 1)
monthly_until = monthly_next - timedelta(days=1)
```

House и lord получают одинаковые boundaries.

Недрейфующий пример:

```text
annual start 2025-01-31
step 1       2025-02-28
step 2       2025-03-31   # не 2025-03-28
```

### 8.3 Required golden values

Basil request (`1980-10-30`, target `2026-07-08`):

```text
annual active_from  = 2025-10-30
annual active_until = 2026-10-29
monthly active_from = 2026-06-30
monthly active_until= 2026-07-29
```

Feb 29 policy остаётся существующим `feb28`:

```text
birth 2000-02-29, target 2026-02-28
annual active_from  = 2026-02-28
annual active_until = 2027-02-27
```

## 9. Firdar boundaries без conversion constant

Файл:

```text
apps/solarsage/solarsage/services/firdar.py
```

Добавить immutable result, например:

```py
@dataclass(frozen=True)
class FirdarPeriodBounds:
    major_active_from: Date
    major_active_until: Date
    minor_active_from: Date
    minor_active_until: Date
```

и public pure helper:

```py
def calculate_firdar_period_bounds(
    *,
    birth_local: Date,
    context: FirdarContext,
) -> FirdarPeriodBounds:
    ...
```

### 9.1 Inverse age arithmetic

Нельзя использовать `365`, `365.25`, `365.2425` или любой новый year-length
constant. Нужно инвертировать тот же birthday-interval mapping, который уже
использует `_age_years_decimal`.

Для absolute fractional age `age`:

```py
whole = floor(age + 1e-12)
fraction = age - whole
interval_start = _clamp_birthday(birth_local, birth_local.year + whole)
interval_end = _clamp_birthday(birth_local, birth_local.year + whole + 1)
interval_days = (interval_end - interval_start).days
offset_days = ceil(fraction * interval_days - 1e-12)
boundary_date = interval_start + timedelta(days=offset_days)
```

Это возвращает первый local date, на котором existing calculated age уже
достиг boundary.

Absolute ages:

```py
cycle_base = context.cycle_index * context.cycle_years
major_start_abs = cycle_base + context.major_start_age
major_end_abs   = cycle_base + context.major_end_age
minor_start_abs = cycle_base + context.minor_start_age
minor_end_abs   = cycle_base + context.minor_end_age
```

Inclusive ends:

```py
major_active_until = age_boundary_to_date(major_end_abs) - 1 day
minor_active_until = age_boundary_to_date(minor_end_abs) - 1 day
```

Validate helper invariant:

```text
major_from <= target_local <= major_until
minor_from <= target_local <= minor_until
```

Builder уже считает `calculate_firdar` один раз; рядом вычислить bounds один
раз и reuse для major/minor. Не делать второй canon load и второй context calc.

Required Basil night-chart golden:

```text
major SUN:
  active_from  = 2019-10-30
  active_until = 2029-10-29

minor SATURN:
  active_from  = 2025-07-18
  active_until = 2026-12-21
```

Оба evidence сохраняют `phase="period"`, `exact_at=None`.

## 10. Solar/lunar return windows

Файл:

```text
apps/solarsage/solarsage/services/returns.py
```

### 10.1 Refactor rules

- Сохранить существующие public signatures `calculate_solar_return` и
  `calculate_lunar_return` для compatibility tests.
- Вынести exact crossing в reusable helpers, чтобы next return не строил второй
  полный chart.
- Не считать next-return houses/planets: нужен только exact JD.
- Все timestamps формировать shared `julian_day_to_utc_iso`.

### 10.2 Solar helper

Добавить reusable helper по смыслу:

```py
def find_solar_return_jd(
    *,
    natal_sun_longitude: float,
    birth_month: int,
    birth_day: int,
    target_year: int,
) -> float:
    ...
```

Он владеет `swe.solcross_ut`, precision verification <= `0.001°` и безопасным
search-start для Feb 29 birth (Feb 28 clamp только для стартовой поисковой даты;
сам crossing остаётся астрономическим).

`calculate_solar_return` использует этот helper, а не дублирует crossing code.

Builder для target local year `Y`:

1. вычисляет cheap candidate JD для `Y`;
2. если candidate `> target_jd`, текущий return относится к `Y-1`;
3. иначе текущий return относится к `Y`;
4. строит полный SR chart только для выбранного current year;
5. next JD получает cheap helper для `current_year + 1`.

Это исправляет существующую ошибку, когда target до дня рождения получал
будущий solar return. Для Basil target `2026-07-08` current SR должен быть return
2025 года, next — 2026 года. Из-за корректной смены chart return activation IDs
для pre-birthday target могут измениться; это допустимая и обязательная
correctness change. Transit IDs при этом не меняются.

### 10.3 Lunar helper

Добавить reusable helper:

```py
def find_next_lunar_return_jd(
    *,
    natal_moon_longitude: float,
    after_jd: float,
) -> float:
    ...
```

Использовать `swe.mooncross_ut(natal_lon, after_jd + epsilon, flags)` и проверить:

- result > `after_jd`;
- longitude residual <= `0.001°`.

Current lunar return продолжает определяться существующим
`calculate_lunar_return` как latest crossing `<= target_jd`.

### 10.4 Evidence timing

Для всех activations одного return chart:

```py
current_iso = julian_day_to_utc_iso(current_return_jd)
next_iso = julian_day_to_utc_iso(next_return_jd)
until_iso = julian_day_to_utc_iso(next_return_jd - 1.0 / 86400.0)

active_from = current_iso
exact_at = current_iso
active_until = until_iso
phase = "period"
applying = None
```

Debug common base дополнить:

```text
next_return_jd
next_return_utc_iso
active_until_utc
```

Required invariant:

```text
current_return_jd <= target_jd < next_return_jd
```

## 11. Pydantic/API preservation

Поля уже есть в обеих schemas. Не менять aliases и optionality.

API local fallback (`ActivationLayerService._build_from_day_signals`) не имеет
достаточных данных для реального solver, поэтому обязан продолжить отдавать:

```text
active_from = null
exact_at = null
active_until = null
```

Нельзя копировать timing из raw signal и нельзя синтезировать его в API.

Sidecar dict path:

```text
SolarSage client JSON
  -> ActivationLayerService.build(sidecar_activation_layer=dict)
  -> API ActivationLayer.model_validate
  -> values unchanged
```

Добавить parity test: ID и все три timing строки до/после validation равны
byte-for-byte.

## 12. Required tests — sidecar

### 12.1 Schema/version

Обновить/add:

- full timing round trip;
- default `activation_layer_version == "al-1.1"`;
- endpoint meta/layer versions `ss-calc-1.2.0`, `al-1.1`;
- date-only strings не преобразуются;
- UTC timing strings заканчиваются `Z`.

### 12.2 New solver unit file

Создать:

```text
apps/solarsage/tests/test_transit_timing.py
```

Использовать injectable synthetic position provider. Обязательные cases:

1. **Direct linear pass**
   - известные exact/boundary times;
   - exact error <= 60 sec;
   - boundaries <= 300 sec.
2. **0°/360° wrap**
   - longitude проходит `359 -> 0 -> 1`;
   - exact root не теряется.
3. **Retrograde triple pass in one contiguous window**
   - synthetic residual можно задать
     `g(x)=0.25*(x+2)*x*(x-2)` degrees;
   - speed `g'(x)=0.25*(3*x*x-4)`;
   - orb/window подобрать так, чтобы roots `-2, 0, +2 days` были внутри одного
     contiguous window;
   - `exact_hits_in_window` содержит ровно три sorted hits;
   - occurrence selection deterministic.
4. **Tangent exact at station**
   - residual касается нуля без sign change;
   - speed sign-change path находит exact.
5. **Near-miss at station**
   - window есть, root нет;
   - boundaries populated;
   - exact null;
   - warning `no_exact_hit_in_window`.
6. **Boundary not bracketed**
   - bounded provider остаётся inside до horizon;
   - typed error code правильный;
   - нет infinite loop.
7. **Cache reuse**
   - несколько targets одной planet читают общую outward grid;
   - provider call count существенно меньше суммы независимых scans;
   - один exact `(planet,jd)` не вызывается дважды.
8. **Determinism**
   - два solver runs дают одинаковые result strings/list/order.

### 12.3 Real Swiss integration

Добавить реальные integration assertions:

- Basil Moon opposition Pluto на `2026-07-08`:
  - transit ID прежний;
  - timing fields non-null;
  - target находится внутри boundaries;
  - phase/timestamp invariant;
- Moon short window;
- Pluto/Uranus/Neptune slow window хотя бы для одного real source;
- planet-in-house timing остаётся null.

Slow-window test не должен hardcode конкретный пользовательский natal fact:
можно взять actual source longitude в target JD и вызвать conjunction solver к
этому fixed longitude, после чего проверить exact near target и bounded window.

### 12.4 Profections

Обновить `test_profections.py`:

- Basil golden из §8.3;
- house/lord boundaries identical;
- Feb29 -> Feb28 policy;
- leap target preserves Feb29;
- Jan31 non-drifting monthly clamp;
- target date всегда внутри inclusive range;
- deterministic identical output.

### 12.5 Firdar

Обновить `test_firdar.py`:

- inverse fractional-age helper;
- exact integer birthday boundary;
- fractional boundary uses ceil-to-first-active-date;
- Feb29 birth interval;
- cycle index > 0;
- Basil golden из §9;
- major/minor target containment;
- existing `calculate_firdar called once` test остаётся зелёным;
- canon loaded once behavior не ухудшается.

### 12.6 Returns

Обновить `test_solar_return.py`, `test_lunar_return.py`:

- shared formatter outputs `Z`;
- current <= target < next;
- active_from == exact_at;
- active_until exactly one second before next serialized second boundary;
- все evidence одного return имеют identical timing;
- pre-birthday solar target выбирает previous/current return, не future;
- post-birthday target выбирает same-year return;
- Feb29 solar birth search не падает;
- next lunar crossing verified;
- existing longitude precision <= 0.001° сохраняется;
- next instant не строит второй full chart: spy/call-count test на
  `calculate_positions`/house calculation.

### 12.7 Full build performance/call budget

Representative request:

```text
birth 1980-10-30 19:50 Europe/Moscow
lat 67.9394 lon 32.8144
target 2026-07-08 12:00 Europe/Moscow
house system PLACIDUS
techniques default/all
```

Добавить test на bounded call count request-scoped cache. Не фиксировать ровно
одно число, зависящее от root iterations, но доказать:

- один solver на request;
- cache miss count bounded;
- нет `calculate_positions` probe на каждый transit activation;
- 101 аспект не создаёт 101 полных chart calculations.

## 13. Required tests — API/contracts

Обновить/add focused tests:

```text
apps/api/tests/test_activation_contracts.py
apps/api/tests/test_activation_layer_transits.py
apps/api/tests/test_activation_layer_profections.py
apps/api/tests/test_activation_layer_firdar.py
apps/api/tests/test_activation_layer_returns.py
apps/api/tests/test_today_meta_versions.py
apps/api/tests/test_pipeline_invariants.py
```

Обязательные proofs:

1. API model принимает timed `al-1.1` sidecar layer.
2. `active_from`/`exact_at`/`active_until` сохраняются byte-for-byte.
3. Activation ID сохраняется вместе с timing.
4. Date-only period timing сохраняется без timezone conversion.
5. Local fallback оставляет все timing null.
6. API/sidecar version literals совпадают и равны новым значениям.
7. Cache identity использует новые constants.
8. Legacy/V1 payload tests остаются legacy и не загрязняются
   `ss-calc-1.2.0`.
9. Explicit old `al-1.0` fixture по-прежнему валидируется, если тест проверяет
   backward compatibility.
10. Generated OpenAPI/TS/Zod содержат `activeFrom`, `exactAt`, `activeUntil` и
    default `al-1.1`.

Не переписывать старые audit fixtures только ради нового literal. Для нового
timing parity proof создать отдельный `al-1.1` input либо точечно обновить тест,
который действительно моделирует live sidecar.

## 14. GRACE и структурная поддерживаемость

1. Новый `transit_timing.py` — полный GRACE header/map/contracts.
2. Существенно изменённые module maps обновить только в рамках этой feature.
3. У новых non-trivial public helpers — `START_FUNCTION_CONTRACT`.
4. Calculation service остаётся pure; новые runtime logs не требуются.
5. `warnings` — существующий public calculation channel, не логировать raw
   profile/birth data.
6. Не импортировать отсутствующий `GraceLogger`.

## 15. Разрешённые product paths

Основной allowlist:

```text
apps/solarsage/solarsage/core/versions.py
apps/solarsage/solarsage/schemas/activation.py
apps/solarsage/solarsage/api/activation_layer.py
apps/solarsage/solarsage/utils/ephemeris.py
apps/solarsage/solarsage/services/activation_builder.py
apps/solarsage/solarsage/services/transit_timing.py          # new
apps/solarsage/solarsage/services/firdar.py
apps/solarsage/solarsage/services/returns.py
apps/api/app/core/versions.py
apps/api/app/schemas/activation.py
packages/contracts/openapi.json                              # generated
packages/contracts/_generated.ts                             # generated
packages/contracts/_generated.zod.ts                         # generated
```

Разрешены соответствующие test files из §§12–13.

Если для correctness требуется иной product path — не расширять scope молча;
остановиться и указать exact path/reason в callback.

## 16. Запрещённые изменения по scope

Не менять:

- `apps/api/app/schemas/today.py` horizon contract — это S2.W2;
- semantic/horizon/personal action services;
- LLM prompts/copy;
- React components/CSS;
- dev fixture route/payload;
- `grace/canon/aspect_rules.v1.yml`;
- `grace/canon/firdar.v1.yml`;
- scoring weights/version;
- auth/API routes;
- database schema/migrations;
- service ports/systemd/nginx;
- Stage 1 canonical JSON fixture values, кроме случая, когда deterministic
  contract tool сам доказывает обязательный generated/default drift; такой diff
  отдельно объяснить до принятия.

## 17. Execution sequence

1. Preflight branch/HEAD/status.
2. Добавить shared UTC formatter + focused test.
3. Реализовать `transit_timing.py` сначала с synthetic unit tests.
4. Интегрировать один request-scoped solver в builder.
5. Реализовать profection timing.
6. Реализовать firdar inverse bounds.
7. Refactor return exact helpers и current/next timing.
8. Обновить versions/defaults.
9. Добавить API preservation/version tests.
10. Запустить focused gates.
11. Запустить full sidecar/API gates.
12. Regenerate contracts и проверить drift.
13. Измерить benchmark.
14. Проверить diff/status; вернуть callback; остановиться без commit/push.

## 18. Обязательные gates

### 18.1 Sidecar focused

Из repository root с правильным package path:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/solarsage \
  apps/solarsage/venv/bin/python -m pytest \
  apps/solarsage/tests/test_transit_timing.py \
  apps/solarsage/tests/test_activation_schema.py \
  apps/solarsage/tests/test_activation_layer_endpoint.py \
  apps/solarsage/tests/test_activation_transits.py \
  apps/solarsage/tests/test_profections.py \
  apps/solarsage/tests/test_firdar.py \
  apps/solarsage/tests/test_solar_return.py \
  apps/solarsage/tests/test_lunar_return.py -q
```

### 18.2 Sidecar full

```bash
PYTHONPATH=/opt/solarsage-astro/apps/solarsage \
  apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q
```

### 18.3 API focused

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
  tests/test_pipeline_invariants.py -q
```

### 18.4 API full

```bash
cd apps/api
source .venv/bin/activate
python -m pytest tests/ -q
```

### 18.5 Contract/frontend type gates

Из repository root:

```bash
pnpm contracts:generate
pnpm contracts:check
npx tsc --noEmit
npx vitest run \
  __tests__/contracts/generated-runtime.test.ts \
  __tests__/contracts/today-v2-contract.test.ts
```

Если имя второго existing contract test отличается, выбрать существующие
Stage 1 generated/runtime contract tests и перечислить exact command в callback.

### 18.6 Static/diff gates

```bash
git diff --check
git diff --stat
git status --short
git diff --name-only
git diff --numstat | awk '$1 == "-" || $2 == "-" { print }'
```

Последняя команда должна не показать binary product files.

## 19. Benchmark protocol

Не запускать через HTTP/systemd. Измерить pure in-process
`build_activation_layer` на representative request из §12.7:

1. 3 warm-up runs;
2. 20 measured runs в одном process;
3. report p50, p95, max milliseconds;
4. report activation count и transit aspect count;
5. report solver position-cache misses для одного representative run либо
   отдельный deterministic call-budget test result.

Acceptance target:

```text
p95 < 2000 ms on this host
```

Baseline до S2.W1 на этом host:

```text
p50 ≈ 90 ms
max  ≈ 106 ms
activations = 147
transit aspect activations = 101
```

Если p95 >= 2000 ms, callback `READY` запрещён. Сначала профилировать:

- повторные `calculate_positions`;
- отсутствие shared outward grids;
- duplicate `(planet,jd)` cache misses;
- построение next return full chart;
- слишком мелкий fixed grid для slow planets.

## 20. Обязательное evidence перед callback

Показать compact real JSON excerpts минимум для четырёх evidence:

1. один real transit aspect;
2. annual или monthly profection;
3. firdar major/minor;
4. solar или lunar return.

В excerpt должны быть:

```text
id
technique
phase
applying
active_from
exact_at
active_until
debug.timing или return boundary debug
```

Для transit отдельно показать:

```text
active_from <= target <= active_until
exact hit count
occurrence_index
```

Также показать:

- API round-trip before/after strings;
- versions;
- benchmark;
- full test totals;
- `git diff --name-only`;
- `git status --short`;
- commit/push отсутствуют.

## 21. Callback

После выполнения вернуть в tmux ровно этот заголовок и заполненный отчёт:

```text
READY_S2_W1_REAL_TIMING
branch: preview/solarsage-v2-human-first-navigator-ux
base_head: 1f8fc1e2e0e7ddcb96706a1934f65eb5ea4f20e4
versions: ss-calc-1.2.0; al-1.1; ss-scoring-2.0 unchanged
transit_solver: <architecture summary>
transit_accuracy: exact <= <n>s; boundaries <= <n>s
retrograde_triple: PASS <proof>
wrap: PASS
near_miss: PASS
cache_reuse: <proof/call counts>
period_boundaries: <Basil + leap/month clamp proof>
firdar_boundaries: <proof>
returns_current_next: <proof>
api_sidecar_parity: PASS
fallback_null_timing: PASS
generated_contracts: PASS
sidecar_focused: <tests>
sidecar_full: <tests>
api_focused: <tests>
api_full: <tests>
ts_contract_tests: <tests>
benchmark: p50=<ms>; p95=<ms>; max=<ms>; runs=20
diff_paths: <list>
binary_product_paths: 0
unrelated_paths_modified: 0
commit: NOT_YET
push: NOT_YET
```

После callback остановиться и ждать architect review. Не исправлять что-либо
дальше и не commit/push без нового точного задания.
