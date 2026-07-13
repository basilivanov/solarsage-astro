# Stage 1.W1 ТЗ — pure request-scoped selection and cache foundation

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base HEAD/origin: `828c20df1e9de5282cd410720649d7efac414754`
Parents: `101`, `102`, accepted W0 `106`
Статус: **AUTHORIZED IMPLEMENTATION WAVE — NO COMMIT / NO PUSH**

## 0. Роль и результат

Ты кодер. Реализуй только чистый фундамент request-scoped выбора V1/V2.

W1 должен дать три вещи:

1. immutable request value `TodaySelectionContext` и чистый resolver;
2. explicit `force_v2=False` в scoring runtime без изменения default callers;
3. explicit selected scoring version для cache-read identity.

После W1 никакой реальный HTTP request ещё не получает preview V2, потому что
route, TodayService и frontend marker не входят в эту волну.

W1 не запускает и не перезапускает сервисы. Commit/push делает архитектор после
отдельного review.

## 1. Preflight

Обязательно проверить до правок:

~~~text
branch = preview/solarsage-v2-human-first-navigator-ux
HEAD = origin branch = 828c20df1e9de5282cd410720649d7efac414754
index empty
tracked worktree clean
3003 and 18092 absent
8000 and 18091 remain canonical/healthy
~~~

Допустимые оставшиеся untracked/frozen paths:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Если есть другой tracked diff или staged path — остановиться.

## 2. Exact implementation allowlist

Ровно четыре пути:

~~~text
apps/api/app/services/today_selection_context.py                 # NEW
apps/api/app/services/day_scoring_runtime_service.py             # MODIFY
apps/api/app/services/cache_key_service.py                        # MODIFY
apps/api/tests/test_today_selection_context.py                    # NEW
~~~

Никакие другие файлы не менять.

Особенно запрещены:

~~~text
apps/api/app/api/**
apps/api/app/services/today_service.py
apps/api/app/services/calendar_service.py
apps/api/app/core/config.py
apps/api/app/core/versions.py
apps/api/app/core/logging.py
apps/api/app/core/logging_events.py
apps/api/app/schemas/**
apps/api/app/db/**
apps/solarsage/**
frontend app/components/hooks/lib
packages/contracts/**
generated fixtures
systemd/env/main
~~~

Не создавать миграцию, header/transport guard, frontend marker или route hook.

## 3. Pure selection context module

Создать `apps/api/app/services/today_selection_context.py` с canonical GRACE:

- `AI_HEADER`;
- `START_MODULE_CONTRACT`;
- `START_MODULE_MAP`;
- named semantic blocks;
- function contract для resolver.

### 3.1 Closed source enum

Рекомендуемая точная форма:

~~~py
class TodaySelectionSource(StrEnum):
    GLOBAL_FLAGS = "global_flags"
    LOCAL_DEV_PREVIEW = "local_dev_preview"
~~~

Equivalent enum naming разрешён только если wire/string values остаются ровно:

~~~text
global_flags
local_dev_preview
~~~

Никаких произвольных source strings.

### 3.2 Immutable value

~~~py
@dataclass(frozen=True, slots=True)
class TodaySelectionContext:
    force_v2: bool
    source: TodaySelectionSource
~~~

Invariants:

- только два поля;
- нет user/profile/header/cookie/request/settings внутри;
- нет mutable default;
- нет `ContextVar`, thread-local, module-global current context или singleton;
- instance нельзя изменить после создания;
- value живёт только там, куда caller передал его явно.

### 3.3 Pure resolver

~~~py
def resolve_today_selection_context(
    *,
    global_v2_enabled: bool,
    preview_authorized: bool,
) -> TodaySelectionContext:
~~~

Точная truth table:

| preview_authorized | global_v2_enabled | force_v2 | source |
|---|---|---|---|
| false | false | false | global_flags |
| false | true | true | global_flags |
| true | false | true | local_dev_preview |
| true | true | true | local_dev_preview |

Preview authorization имеет source precedence. Resolver не читает и не меняет
`settings`.

## 4. Day scoring runtime extension

Обновить GRACE boundary существующего
`day_scoring_runtime_service.py`: добавить canonical module contract/map и
function contracts для публичных helper-функций. Не переписывать scoring logic
вне необходимого выбора.

### 4.1 Compatible helper signatures

~~~py
def should_compute_v2(*, force_v2: bool = False) -> bool

def selected_scoring_version_for_flags(
    *,
    force_v2: bool = False,
) -> int | str
~~~

Rules:

~~~text
selected V2 = force_v2 OR settings.solarsage_v2_enabled
compute V2  = selected V2 OR settings.solarsage_v2_dual_run
~~~

`force_v2=False` не может выключить глобально включённый V2.

Dual-run по-прежнему означает compute-only и не выбирает V2.

Default вызов без аргумента обязан быть behavior-compatible с текущими
TodayService и CalendarService callers.

### 4.2 Compute signature

Добавить keyword-only в конец:

~~~py
def compute(
    self,
    day_signals: list[AstroSignal],
    activation_layer: ActivationLayer | None = None,
    user_id: UUID | None = None,
    target_date: str | None = None,
    *,
    force_v2: bool = False,
) -> DualRunResult:
~~~

Внутри одного compute call один раз определить:

~~~py
v2_selected = bool(force_v2 or settings.solarsage_v2_enabled)
v2_dual_run = bool(settings.solarsage_v2_dual_run)
compute_v2 = v2_selected or v2_dual_run
~~~

Далее везде использовать эти local snapshots:

- whether V2 computes;
- diff `selected_version`;
- fail-loud vs shadow fail-open;
- final selected result/version.

Не перечитывать `settings.solarsage_v2_enabled` в разных ветках одного call.

### 4.3 Error policy

~~~text
v2_selected true + V2 error -> re-raise (fail loud)
v2_selected false + dual-run true + V2 error -> V1 selected, v2_error recorded
~~~

Request-scoped force обязан иметь ту же fail-loud semantics, что global V2.

Не добавлять новые logs/events. Не добавлять selection context, header values или
identity в существующие log payload.

## 5. Cache read identity override

В `cache_key_service.expected_cache_identity` добавить только compatible
optional authority:

~~~py
def expected_cache_identity(
    *,
    user_id: UUID,
    target_date: str,
    profile_hash: str,
    selected_scoring_version: int | str | None = None,
) -> TodayCacheKey:
~~~

Rules:

~~~text
selected_scoring_version is None
  -> current selected_scoring_version_for_flags() behavior unchanged

selected_scoring_version is provided
  -> use it exactly; do not reread global selection flags
~~~

Explicit legacy version должен остаться V1 даже при global V2 true. Explicit
current V2 version должен остаться V2 даже при global V2 false.

Не добавлять `force_v2` вторым selector в cache service. Selection происходит
один раз до cache boundary; cache получает уже выбранную version authority.

Не менять:

- `TodayCacheKey` fields;
- hash serialization/algorithm/length;
- canon map/hash;
- runtime identity resolver mapping;
- DB models/schema;
- existing default callers.

## 6. Read/write parity invariant

Для одной selected version эти два пути обязаны дать одинаковые identity fields
и `cache_key_hash`:

~~~text
READ:
expected_cache_identity(selected_scoring_version=selected)

WRITE:
resolve_today_runtime_identity(selected_scoring_version=selected)
-> build_today_cache_key(identity fields)
~~~

Доказать отдельно для V1 и V2 с одинаковыми:

~~~text
user_id
target_date
profile_hash
ACTIVATION_LAYER_VERSION
llm prompt default
canon versions
~~~

V1 и V2 hashes между собой обязаны различаться.

## 7. Focused test module

Создать один новый canonical GRACE test file:

~~~text
apps/api/tests/test_today_selection_context.py
~~~

Не модифицировать старые tests в этой волне. Full suite доказывает их backward
compatibility.

Минимум 24 реально исполняемых test cases после parametrization.

### 7.1 Pure context

Обязательно:

1. exact two enum values;
2. all four resolver truth-table rows;
3. preview source precedence when both true;
4. dataclass frozen mutation rejected;
5. slots/no accidental `__dict__` storage;
6. exact field set contains no request/user/header/profile/settings data;
7. resolver does not import/read/mutate global settings.

### 7.2 Helper truth tables

Обязательно:

8. selected helper default V1;
9. global enabled -> V2;
10. force true/global false -> V2;
11. force false/global true stays V2;
12. compute helper all eight boolean combinations of global enabled, dual-run,
    force;
13. dual-run alone computes but does not select V2.

### 7.3 Runtime behavior

Use monkeypatched deterministic fake V1/V2 scoring services; do not depend on
astrological scoring data for selection tests.

Обязательно:

14. default V1 does not call V2;
15. dual-run calls V2 but selects V1;
16. force V2 with globals off calls and selects V2;
17. global V2 still selects V2 with force false;
18. force-selected V2 error re-raises;
19. global-selected V2 error re-raises;
20. dual-run-only V2 error records error and returns V1;
21. global settings values unchanged after force success;
22. global settings values unchanged after force exception.

### 7.4 Independence/concurrency

Запустить два реально overlapping calls через `ThreadPoolExecutor` или
эквивалентный real concurrency barrier:

~~~text
call A force_v2=true  -> V2
call B force_v2=false -> V1
global flags false/false before, during and after
~~~

Fake services должны быть thread-safe. Доказать, что results и selected versions
не протекают между calls. Не использовать `ContextVar` как решение.

### 7.5 Cache authority/parity

Обязательно:

23. default `None` + global false -> V1 key;
24. default `None` + global true -> V2 key;
25. explicit V2 + global false -> V2 key;
26. explicit V1 + global true -> V1 key;
27. dual-run alone does not produce V2 cache identity;
28. frontend flag does not select family;
29. V1 read/write key fields and hash exact equal;
30. V2 read/write key fields and hash exact equal;
31. V1 and V2 hash differ;
32. current/legacy public runtime identity versions remain exact.

No `pass` placeholder tests. No raw sleeps for concurrency; use barrier/event.

## 8. Static/source guards

New tests or static gate must additionally verify:

~~~text
no ContextVar/thread-local/current_selection module global
no settings assignment/setattr in implementation
no route/frontend/TodayService/Calendar changes
no new log event/string
no DB/schema/migration changes
no second selector in cache service
force_v2 defaults false everywhere
~~~

Source guards are additional; they do not replace behavior tests.

## 9. Mandatory gates

Run from repo root.

### 9.1 Syntax/compile

~~~bash
apps/api/.venv/bin/python -m py_compile \
  apps/api/app/services/today_selection_context.py \
  apps/api/app/services/day_scoring_runtime_service.py \
  apps/api/app/services/cache_key_service.py \
  apps/api/tests/test_today_selection_context.py
~~~

### 9.2 Focused foundation

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_selection_context.py \
  apps/api/tests/test_scoring_v2_runtime_flags.py \
  apps/api/tests/test_today_service_v2_dual_run.py \
  apps/api/tests/test_calendar_v2_dual_run.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_today_meta_versions.py \
  -q
~~~

Все focused tests должны быть зелёными.

### 9.3 Existing request/cache regressions

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_horizons_contract.py \
  apps/api/tests/test_payload_v2_downstream_mapping.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_day_endpoints.py \
  -q
~~~

### 9.4 Full API authoritative root invocation

~~~bash
apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
~~~

Текущий accepted baseline содержит только эти шесть unrelated failures:

1. calendar duplicate-cache winning-row reread;
2. four stale `test_semantic_v2_service.py` calls missing scoring result;
3. one stale `test_today_v2_payload.py` selected-path expectation.

W1 не исправляет их и не должен добавлять новые failures. Зафиксировать точные
node IDs и counts. Любой дополнительный failure — W1 не готов.

### 9.5 Backend GRACE and diff

~~~bash
apps/api/.venv/bin/python scripts/grace_lint.py apps/api/app
git diff --check
~~~

Если backend GRACE имеет pre-existing baseline, доказать, что четыре W1 paths
проходят owned marker/contract inspection отдельно. Не менять unrelated files.

## 10. Final state

До callback:

~~~text
changed implementation paths = exact 4
index empty
commit not created
push not created
HEAD/origin unchanged at 828c20df...
3003/18092 absent
API/sidecar/frontend services and env unchanged
no route/frontend/TodayService/Calendar diff
next wave not started
~~~

## 11. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_1_W1
base_sha: 828c20df1e9de5282cd410720649d7efac414754
changed_paths: EXACT_4
selection_context: FROZEN_SLOTS_PURE
selection_sources: EXACT_global_flags_local_dev_preview
resolver_truth_table: PASS_4_OF_4
settings_mutation: ZERO
contextvar_or_request_global: ZERO
selected_helper_matrix: PASS
compute_helper_matrix: PASS_8_OF_8
runtime_default_compat: PASS
runtime_force_v2: PASS_SELECTED_CURRENT
runtime_force_error_policy: PASS_FAIL_LOUD
runtime_dual_error_policy: PASS_SHADOW_V1
concurrent_independence: PASS_REAL_OVERLAP
cache_explicit_authority: PASS
cache_v1_read_write_parity: PASS
cache_v2_read_write_parity: PASS
cache_v1_v2_hash_separation: PASS
focused_foundation: <exact count> PASS
request_cache_regression: <exact count> PASS
full_api_root: <counts>; EXACT_6_FROZEN_FAILURES_ONLY
backend_grace: <exact>
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
head_origin: 828c20df1e9de5282cd410720649d7efac414754_EQUAL
ports_3003_18092: ABSENT
unrelated_paths: UNTOUCHED
services_env_main: UNCHANGED
next_wave: NOT_STARTED
~~~

После callback остановиться.
