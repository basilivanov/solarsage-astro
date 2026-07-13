# Stage 2.W3B3 R1 — prefetch lifecycle and strict boundary correction

Дата: `2026-07-13`

Branch: `preview/solarsage-v2-human-first-navigator-ux`

Accepted base / current HEAD:
`a0646a0b2d02f3a40c209a45286cb60d0d846a91`

Parent implementation specifications:

- `160_STAGE_2_W3B3_SEMANTIC_TODAY_INTEGRATION_MYPY_TZ.md`;
- `163_STAGE_2_W3B3_AUTHORIZATION_BASE_AND_GATE_AMENDMENT_TZ.md`.

Статус: **ARCHITECT REVIEW REJECTED CURRENT W3B3 CALLBACK — R1 AUTHORIZED, NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review agents и использование их результатов как evidence.

## 1. Why the current callback is not accepted

The current worktree has the useful W3B3 typing/schema changes, but the
architect review found three correctness violations that must be corrected
before acceptance.

### F1 — the semantic boundary was widened to fit an invalid test double

Doc 160 section 7.4 requires exactly:

```python
semantic_layer.model_dump()
```

The implementation instead accepts `dict` at runtime:

```python
semantic_layer if isinstance(semantic_layer, dict) else semantic_layer.model_dump()
```

`SemanticService.build_semantic_layer()` has the declared production return
type `SemanticLayer`. The `dict` comes only from a stale test double in
`test_day_no_birthday_fallback.py`. Product code must keep the strict service
boundary; the test must return the declared schema.

### F2 — `today.py` mutates the canonical class at import time

The current line:

```python
ContentAccessState.__doc__ = None
```

mutates the shared class imported from `schemas.access`, affects every
consumer's runtime introspection, and contradicts the module contract's
type-only/re-export role. It was added only to keep generated OpenAPI output
stable after unifying the two Python classes.

The correct fix is source-level: remove the schema-producing class docstring
from the canonical definition and preserve the same explanation as an ordinary
comment. Do not monkeypatch class metadata at import time.

### F3 — the full API suite did not validate the new prefetch implementation

The shared API test fixture sets:

```python
settings.app_env = "test"
```

The new condition therefore disables automatic prefetch throughout the full
suite. The reported `1406 passed / 4 skipped` does not execute the new
`async_sessionmaker(bind=self.db.bind, ...)` branch.

That branch is also not acceptable production composition:

- it derives a new factory from a request-scoped session;
- it does not preserve the canonical `SessionLocal` configuration;
- it changes the old concurrent prefetch to a sequential loop;
- the fire-and-forget task still has no strong owner reference.

Test-environment suppression is allowed as isolation, but only after the real
prefetch mechanism is production-safe and directly regression-tested.

## 2. Preserve accepted W3B3 work

Do not reset, restore, checkout, stash, rebase or rewrite the worktree.

Preserve unchanged:

- all accepted edits in `semantic_v2_service.py`;
- canonical default `ContentAccessState(state="full")`;
- validated `birth_date` / `birth_tz` guard and narrowed use;
- `TodayV2HorizonPipelineAudit` annotation;
- duplicate Today access class removal and public re-export identity;
- `START_BLOCK: TODAY_READ_MODELS` repair;
- every V2 selection, cache identity, horizon and fail-open/fail-loud rule.

## 3. Exact R1 edit allowlist

Edit only these five paths:

```text
apps/api/app/schemas/access.py
apps/api/app/schemas/today.py
apps/api/app/services/today_service.py
apps/api/tests/test_day_no_birthday_fallback.py
apps/api/tests/test_today_preview_transport.py
```

`apps/api/app/services/semantic_v2_service.py` remains modified from the
original W3B3 implementation but is byte-frozen during R1.

Expected final tracked diff against HEAD is exactly six paths:

```text
apps/api/app/schemas/access.py
apps/api/app/schemas/today.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_service.py
apps/api/tests/test_day_no_birthday_fallback.py
apps/api/tests/test_today_preview_transport.py
```

No staging, commit or push. Do not start W3C, final RC, main merge or deploy.

Frozen unrelated paths remain untouched/un-staged:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Architect docs, including this file and doc 163, remain untracked and
unmodified by the coder.

## 4. Canonical access schema without runtime mutation

### 4.1 `schemas/access.py`

The access model fields, aliases, literals, defaults, base class and JSON wire
schema are frozen.

Replace only the class docstring:

```python
class ContentAccessState(CamelModel):
    """Access state for a specific day (W-1.3 stub, W-ACCESS.1 real)."""
```

with an ordinary comment immediately above the class:

```python
# Access state for a specific day (W-1.3 stub, W-ACCESS.1 real).
class ContentAccessState(CamelModel):
```

Do not change any field. This intentionally keeps generated OpenAPI/contracts
description-free without a runtime class mutation.

### 4.2 `schemas/today.py`

Use explicit public re-export aliases:

```python
from .access import ContentAccessReason as ContentAccessReason
from .access import ContentAccessState as ContentAccessState
```

Delete completely:

```python
ContentAccessState.__doc__ = None
```

Do not add any other assignment to `__doc__`, `__module__`, Pydantic config or
schema hooks. `TodayPayload.access` must continue to reference the same class
object as `app.schemas.access.ContentAccessState`.

## 5. Strict semantic-layer boundary

In `TodayService.get_today_payload`, replace the current compatibility
conditional with the exact doc-160 call:

```python
notes_text = await llm_service.generate_notes(
    scoring_result["day_status"],
    scoring_result["sphere_scores"],
    semantic_layer.model_dump(),
)
```

Do not widen `SemanticService`, `SemanticLayer`, `LLMService` or the LLM prompt.
Do not add `Any`, cast, ignore, `hasattr`, `isinstance`, fallback dict or a
serialization helper.

In `test_day_no_birthday_fallback.py`, replace the stale `{}` semantic-layer
return with a real valid `SemanticLayer` instance. Import the canonical schema
and use values consistent with that test's steady/empty scoring result:

```python
SemanticLayer(
    day_status="steady",
    day_theme="Спокойный день",
    sphere_themes=[],
    top_keywords=[],
)
```

The test remains about NatalContext/day-sidecar reuse. Do not weaken its
assertions and do not make product code support its old invalid mock.

## 6. Production-safe week prefetch

### 6.1 Canonical session factory

In `today_service.py`:

- remove the `async_sessionmaker` import;
- keep `AsyncSession`;
- import canonical `SessionLocal` from `app.db.session`;
- keep `settings` only for the explicit test-environment scheduling guard.

`_prefetch_week` must never read `self.db.bind`, construct its own
`async_sessionmaker`, or reuse `self.db` for child calculations.

For every one of the seven days, `_calc_one` must:

1. enter a fresh `async with SessionLocal() as session` context;
2. construct a child `TodayService` with that fresh session and the same
   `_horizon_integration_service`;
3. call `get_today_payload(user_id, day, None, skip_prefetch=True)`;
4. let the context close the fresh session on success or failure.

Keep the seven calculations concurrent with one `asyncio.gather(...)`, as in
the pre-W3B3 behavior. Do not serialize them with `for ... await`.

Keep all existing best-effort behavior:

- one failed day is logged and does not fail the request;
- no preview `selection_context` is propagated;
- child calls set `skip_prefetch=True`;
- no raw user/profile/auth facts are logged;
- the foreground response is not blocked by the week calculation.

Update the `_prefetch_week` docstring if touched: current events are warning
logs, not debug logs.

### 6.2 Strong ownership of the scheduled task

Add one private module-level set with an exact task type near the existing
module constants:

```python
_TODAY_PREFETCH_TASKS: set[asyncio.Task[None]] = set()
```

The foreground scheduling block must be:

```python
if not skip_prefetch and settings.app_env != "test":
    prefetch_task = asyncio.create_task(self._prefetch_week(user_id, target_date))
    _TODAY_PREFETCH_TASKS.add(prefetch_task)
    prefetch_task.add_done_callback(_TODAY_PREFETCH_TASKS.discard)
```

This is the standard strong-reference lifecycle pattern for in-process
best-effort asyncio tasks. Do not use `ensure_future`, a weak reference,
request/app mutable state, user ID in task names, or a global environment
mutation.

The `app_env != "test"` guard is now explicitly authorized only as automatic
test isolation. Dev and production behavior remains enabled. The mechanism
itself must be covered directly as described below.

Update truthful GRACE/module/function side-effect wording to mention the
best-effort background prefetch task and independent DB sessions. Do not invent
new log event names.

Keep `today_service.py` at or below 1000 physical lines. No unrelated cleanup
is allowed to create room; use compact truthful wording and remove only the
superseded prefetch code/comments.

## 7. Direct prefetch regression test

Upgrade the existing test:

```text
test_prefetch_week_never_propagates_preview_context
```

in `test_today_preview_transport.py`. Do not add a new test count.

The upgraded test must patch `today_service_module.SessionLocal` with a
deterministic async context-manager factory and directly await
`service._prefetch_week(...)`.

It must prove all of the following:

```text
exact child calls                         7
exact fresh SessionLocal contexts         7
all contexts entered                      yes
all contexts exited                       yes
all child service DB objects fresh        yes
original request DB object reused         no
child days                                today-3 through today+3 exactly
every child kwargs                        {"skip_prefetch": True}
selection_context propagated              no
```

Patch `TodayService.get_today_payload` at the class boundary so calls made by
the newly constructed child services are recorded. Do not keep the old
instance-only override, because that would not observe fresh child services.

The fake sessions must not open a real DB/network connection. The test must
remain deterministic under concurrent gather ordering: compare the dates as a
set or sorted sequence, not completion order.

Do not add sleeps, environment timing assumptions, production DB access or
private SQLAlchemy internals to this test.

## 8. Required static gates

Run Ruff on all six final tracked paths:

```bash
apps/api/.venv/bin/python -m ruff check \
  apps/api/app/schemas/access.py \
  apps/api/app/schemas/today.py \
  apps/api/app/services/semantic_v2_service.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_preview_transport.py
```

Run:

```bash
apps/api/.venv/bin/python scripts/test_grace_lint.py
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/schemas/access.py \
  apps/api/app/schemas/today.py \
  apps/api/app/services/semantic_v2_service.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_preview_transport.py
```

Require 13 GRACE self-tests and all six changed paths clean.

Run cold MyPy exactly as doc 160. Require:

```text
global diagnostics                  80
global failing paths                11
all W3B/R1 production paths          0
new or migrated diagnostics          0
legacy diagnostics                  80 unchanged
```

No MyPy cache may be used as the acceptance result.

## 9. Required behavioral gates

### 9.1 Focused boundary/prefetch tests

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_preview_transport.py \
  -q
```

Require the exact existing count after collection; no new test was authorized.

### 9.2 Original W3B3 targeted suite

Run the exact ten-file command from doc 160. Require:

```text
226 passed
```

### 9.3 Full API suite

```bash
cd apps/api
PYTHONPATH=. .venv/bin/python -m pytest tests/ -q
```

Require exactly:

```text
1406 passed
4 skipped
0 failed
0 errors
```

Additionally reject the run if output contains any of:

```text
event loop is closed
ResourceClosedError
PytestUnhandledThreadExceptionWarning
Task was destroyed but it is pending
coroutine was never awaited
```

Do not suppress these strings via warning filters or logging changes.

## 10. Contract and identity gates

Run the identity proof from doc 163, plus:

```python
assert TodayState.__doc__ is None
```

Source guards must prove:

```text
ContentAccessState.__doc__ assignment             absent
self.db.bind in today_service prefetch             absent
async_sessionmaker in today_service                absent
asyncio.ensure_future in today_service             absent
canonical SessionLocal in today_service            present
private strong task set                            present
semantic-layer generate_notes argument             exact model_dump()
```

Run unchanged:

```bash
pnpm contracts:check
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/test_contract_registry.py -q
pnpm test:frontend-guard
```

Require no generated tracked diff, Python contracts `44 passed`, and frontend
guard PASS.

## 11. Worktree/runtime gates

Require:

- `git diff --check` zero;
- index empty;
- final tracked diff exact six paths from section 3;
- no modification in frozen unrelated paths;
- branch/HEAD still `a0646a0...` and tracking/remote feature unchanged;
- `main` / `origin/main` unchanged;
- no runtime service restart/reload;
- ports `3003`, `8001`, `18092` absent;
- canonical production ports/services untouched.

## 12. Required callback and stop

Return exactly this evidence shape, then stop:

```text
READY_STAGE_2_W3B3_R1_ARCH_REVIEW
base_head: a0646a0b2d02f3a40c209a45286cb60d0d846a91
final_tracked_scope: EXACT_6_FILES
semantic_boundary: STRICT_MODEL_DUMP
semantic_test_double: CANONICAL_SEMANTIC_LAYER
content_access_source: SINGLE_CANONICAL_CLASS
content_access_runtime_metadata_mutation: ABSENT
content_access_identity: SAME_OBJECT
content_access_wire: UNCHANGED
prefetch_session_source: CANONICAL_SESSION_LOCAL
prefetch_request_session_reuse: ABSENT
prefetch_concurrency: SEVEN_FRESH_SESSIONS_GATHER
prefetch_selection_context: ABSENT
prefetch_task_owner: STRONG_SET_UNTIL_DONE
prefetch_test_env_autostart: DISABLED
prefetch_direct_regression: PASS_7_ENTERED_7_EXITED
today_service_lines: N_LE_1000
mypy_feature_after: PASS_ZERO
mypy_total_after: 80_DIAGNOSTICS_11_LEGACY_PATHS
ruff: PASS_ZERO_6
grace_selftests: 13_PASS
authorized_grace: PASS_6
focused_tests: N_PASS
targeted_tests: 10_FILES_226_PASS
api_full: 1406_PASS_4_SKIP_ZERO_LIFECYCLE_WARNINGS
contracts_check_compat_fixture: PASS_NO_DRIFT
py_contracts: 44_PASS
frontend_guard: PASS
git_diff_check: PASS_ZERO
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Do not commit or push. Wait for architect review.
