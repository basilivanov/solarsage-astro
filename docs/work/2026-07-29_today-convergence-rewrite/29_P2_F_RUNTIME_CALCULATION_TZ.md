# 29 — P2-F Runtime convergence calculation

Статус: **controller packet / implementation-ready**

Исполнитель: Codex CLI, `gpt-5.6-luna`, effort `high`

Depends on: packets 18–28, frozen W1 canon

## 1. Локальная цель

Добавить одну production orchestration boundary без DB/snapshot/wire/LLM:

```text
validated profile + target local date
  -> BirthTimeResolution
  -> one sidecar activation-grid request
  -> robust RawPhysicalFact records
  -> canonical convergence pipeline
  -> immutable built/unavailable calculation result
```

Это завершает W2 deterministic calculation path. Старый `TodayService`,
Calendar, кэш и публичный endpoint пока не переключаются.

## 2. Exact write scope

- новый `apps/api/app/services/today_convergence_runtime.py`
- новый `apps/api/tests/test_today_convergence_runtime.py`
- `grace/knowledge-graph.xml`
- `grace/verification-matrix.md`
- этот packet

## 3. Frozen / out of scope

- не менять canon, versions, activation contracts, units/ledger/groups/tone/
  selection/pipeline, birth-time resolver/facts, client и sidecar;
- не менять `TodayService`, Calendar, API routes, DB/models/migrations,
  snapshots, access, LLM, pregen, frontend;
- не импортировать legacy Today/scoring/normalization/analysis modules;
- не добавлять cache, retry, parallelism, fallback time/location или logging
  events: request/snapshot service W3 будет observability boundary;
- не коммитить и не push.

## 4. Public runtime contract

Новый модуль экспортирует минимум:

```python
class TodayConvergenceRuntimeError(ValueError): ...

@dataclass(frozen=True)
class TodayConvergenceCalculationBuilt:
    state: Literal["convergence_today", "quiet_day"]
    target_date: date
    target_timezone: str
    target_time: str
    birth_time: BirthTimeResolution
    calculation_version: str
    activation_layer_version: str
    facts_audit: BirthTimeFactsAudit
    pipeline: CanonicalPipelineBuilt

@dataclass(frozen=True)
class TodayConvergenceCalculationUnavailable:
    state: Literal["unavailable"]
    target_date: date
    failure_stage: Literal["profile", "activation_grid", "facts", "pipeline"]
    failure_reason: str
    target_timezone: str | None
    target_time: str
    birth_time: BirthTimeResolution | None
    facts_audit: BirthTimeFactsAudit | None
    pipeline: CanonicalPipelineUnavailable | None

TodayConvergenceCalculationResult = Built | Unavailable

async def calculate_today_convergence(
    profile: TodayConvergenceProfileLike,
    target_date: date,
    *,
    delta_trigger_semantic_keys: Sequence[str] | None = None,
    client: SolarSageClient | None = None,
) -> TodayConvergenceCalculationResult: ...
```

`TodayConvergenceProfileLike` — Protocol ровно по используемым полям:
`birthday`, `birth_time`, `birth_time_mode`, `birth_time_bucket`, `birth_lat`,
`birth_lon`, `birth_tz`, `current_lat`, `current_lon`, `current_tz`.

Built/Unavailable не имеют compatibility aliases и полностью frozen.
`failure_reason` — safe stable token с prefix `today_convergence_runtime:`;
сырой HTTP/error text, координаты, даты рождения и timezone profile туда не
попадают.

## 5. Profile and target validation

- `profile` должен удовлетворять прямому protocol shape; отсутствие атрибута
  не превращается в default;
- `target_date` — `date`, но не `datetime`;
- `birthday` — `date`, но не `datetime`;
- birth lat/lon finite numeric (bool запрещён) и в `[-90,90]` / `[-180,180]`;
- `birth_tz` — non-empty valid IANA zone;
- birth-time комбинацию валидирует только `resolve_profile_birth_time`;
- target timezone выбирается строго `current_tz -> birth_tz -> UTC`; выбранный
  ключ валидируется, invalid не падает дальше на UTC. Поскольку сам natal-input
  требует `birth_tz`, built calculation практически использует current или
  birth; профиль без birth timezone fail-closed до вызова sidecar;
- current location передаётся sidecar только если `current_lat`, `current_lon`,
  `current_tz` присутствуют все. Тогда координаты/zone валидируются так же.
  Полностью отсутствующий или частичный current-location набор не выдумывается
  и даёт `current_location=None` (это не ошибка расчёта).

Любой profile/target/birth-time boundary failure возвращает typed Unavailable
`failure_stage="profile"`, а не исключение и не HTTPException.

## 6. Canonical target moment and one sidecar call

Принятый W1 replay считает день в локальный полдень. В модуле одна явная
константа:

```python
CANONICAL_TARGET_TIME = "12:00"
```

Это **время прогнозируемого дня**, не fallback времени рождения. Оно никогда
не попадает в `birth_time`/control grid и не зависит от mode.

Вызвать `get_activation_layer_grid` ровно один раз:

- `birth_date=profile.birthday.isoformat()`;
- `birth_times=resolution.control_times`;
- реальные birth coords/tz;
- `target_date=target_date.isoformat()`;
- `target_time=CANONICAL_TARGET_TIME`;
- выбранный target timezone;
- `house_system="PLACIDUS"` (requested system; sidecar сам возвращает resolved);
- `techniques=None` — тот же полный deterministic activation set, на котором
  frozen W1 проходил replay; фильтрация происходит fail-closed ниже;
- validated current location либо `None`.

Никаких N-call fallback или повторов. Default client берётся один раз через
`get_solarsage_client`; injected client нужен для unit tests.

Ожидаемые transport/contract ошибки (`SolarSageClientError`, `httpx.HTTPError`)
становятся Unavailable `activation_grid`. Не ловить `Exception`: programming
errors должны падать в тестах.

## 7. Facts and pipeline composition

1. `build_birth_time_facts(resolution, samples)`.
2. Typed `TodayBirthTimeFactsError` -> Unavailable `facts`.
3. `run_canonical_today_pipeline(facts, target_date, target_timezone,
   delta_trigger_semantic_keys)`.
4. Pipeline unavailable -> runtime Unavailable `pipeline` с сохранёнными
   `facts_audit` и typed pipeline result.
5. Pipeline built -> runtime Built. `state` строго равен `pipeline.state`.

`calculation_version` и `activation_layer_version` берутся из первого
validated sample. Пустого grid быть не может после resolver/client contract.
Runtime не хранит raw evidence и не строит wire payload; canonical ledger/
selection уже находятся в `pipeline`, audit — в `facts_audit`.

Delta keys передаются без преобразования: canonical ledger сам строго валидирует
Sequence/semantic keys. Runtime не принимает голые planet names как особый
случай и не вычисляет yesterday.

## 8. Failure matrix

| Failure | Result |
|---|---|
| missing/malformed profile, invalid mode/time/tz/coords/date | unavailable/profile |
| expected sidecar HTTP/timeout/typed response error | unavailable/activation_grid |
| robust-facts boundary error | unavailable/facts |
| canonical pipeline typed unavailable | unavailable/pipeline |
| unexpected programmer error | propagates |

Unavailable сохраняет только уже безопасно построенные typed stages. Поля
после точки отказа равны `None`.

## 9. Required tests

1. exact/bucket/unknown: один client call, exact ordered body and control grids;
2. target noon не подставляется в birth controls; unknown отправляет canonical
   7 points, bucket — 3, exact — реальное profile time;
3. target timezone priority current -> birth; профиль без birth timezone и
   invalid selected zone fail-closed без client call (никакого фактического UTC
   fallback для неполного natal-input);
4. valid all-or-none current location; partial omitted; invalid complete set
   unavailable/profile;
5. missing attrs, malformed birthday/target date/coords/bool/NaN/mode combos
   unavailable/profile without exception text/PII;
6. `SolarSageClientError`, `httpx.TimeoutException`, `HTTPStatusError` map to
   activation_grid; arbitrary `RuntimeError` propagates;
7. facts builder receives the exact resolution and returned samples once;
8. built path preserves versions/audit/pipeline and state;
9. pipeline unavailable preserves audit and maps stage; typed facts failure maps
   facts stage;
10. delta semantic keys reach canonical pipeline unchanged and invalid
    collection behavior is not silently normalized;
11. function/result immutability and deterministic equality;
12. no imports from legacy Today/scoring/normalization/analysis and no
    executable `birth_time or "12:00"` pattern.

Mocks target only network and accepted stage functions. At least one test uses
real `build_birth_time_facts + run_canonical_today_pipeline` with typed synthetic
ActivationGridSample objects; нельзя замокать весь happy path.

## 10. GRACE and verification

Новый pure orchestration module: full AI_HEADER/module map/contracts/blocks,
`owned_tests`, `emitted_logs: none`. Добавить graph path:

```text
profile -> birth-time resolver -> activation-grid client
  -> robust facts -> canonical pipeline -> runtime calculation
```

Добавить UC P2-F в verification matrix. Runtime не регистрирует logging events:
он не request/persistence boundary и не должен логировать profile data.

Минимальные команды:

```bash
git diff --check
cd apps/api && PYTHONPATH=. /opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_runtime.py \
  tests/test_today_birth_time.py \
  tests/test_today_birth_time_facts.py \
  tests/test_solarsage_client.py \
  tests/test_today_convergence_pipeline.py -q
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check --no-cache \
  apps/api/app/services/today_convergence_runtime.py \
  apps/api/tests/test_today_convergence_runtime.py
python3 scripts/grace_lint.py apps/api/app/services/today_convergence_runtime.py
bash scripts/grace/check-markers.sh
```

## 11. Expected evidence

- exact files and short data flow;
- exact/bucket/unknown client-call assertions;
- targeted counts + Ruff/GRACE/markers/diff-check;
- confirmation: one sidecar call, no fallback/retry/legacy imports, no
  canon/schema/version/client/pipeline edits, no commit/push.
