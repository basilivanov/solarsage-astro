# Stage 2.W3B3 R1A — exact stale semantic mock and gate-command amendment

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`a0646a0b2d02f3a40c209a45286cb60d0d846a91`

Parent: `164_STAGE_2_W3B3_R1_PREFETCH_AND_BOUNDARY_CORRECTION_TZ.md`.

Статус: **R1A AUTHORIZED — READ AFTER DOC 164, NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review agents и использование их результатов as evidence.

## 1. Purpose and precedence

Strict `semantic_layer.model_dump()` correctly exposed one additional stale
test double outside doc-164 allowlist. This amendment:

1. authorizes exactly that one additional test path;
2. tightens the already authorized prefetch regression assertions;
3. corrects the full-suite working-directory command in doc 164.

Where this document differs from doc 164, it controls only these three items.
All other doc-164 requirements remain mandatory.

## 2. Exact additional semantic mock scope

Inventory found `{}` semantic mocks in several tests, but only this additional
file patches `app.services.today_service.SemanticService` and therefore crosses
the strict TodayService boundary:

```text
apps/api/tests/test_wave3_day_pipeline_reuse.py
```

Authorize editing this path only at:

- imports;
- `_setup_service_mocks` semantic-layer return value.

Import canonical:

```python
from app.schemas.semantic import SemanticLayer
```

Replace:

```python
mock_semantic.return_value.build_semantic_layer.return_value = {}
```

with:

```python
mock_semantic.return_value.build_semantic_layer.return_value = SemanticLayer(
    day_status="steady",
    day_theme="Спокойный день",
    sphere_themes=[],
    top_keywords=[],
)
```

Do not alter test scenarios, call counts, expected cache behavior, sidecar
mocks, runtime selection or test count.

Do not edit these inventory matches:

```text
apps/api/tests/test_audit_activation_sidecar_artifacts.py
apps/api/tests/test_audit_today_modes.py
```

They patch their audit module boundary, not `TodayService`, and are outside
scope.

## 3. Final exact tracked scope

Final diff against HEAD must be exactly seven files:

```text
apps/api/app/schemas/access.py
apps/api/app/schemas/today.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_service.py
apps/api/tests/test_day_no_birthday_fallback.py
apps/api/tests/test_today_preview_transport.py
apps/api/tests/test_wave3_day_pipeline_reuse.py
```

No eighth tracked path is allowed. Index remains empty; no commit/push.

## 4. Prefetch per-day failure boundary correction

In `TodayService._prefetch_week`, the per-day `try` must include session
acquisition, child-service construction and child payload calculation:

```python
async def _calc_one(day: Date) -> None:
    try:
        async with SessionLocal() as session:
            service = TodayService(session, self._horizon_integration_service)
            await service.get_today_payload(
                user_id,
                day,
                None,
                skip_prefetch=True,
            )
    except Exception:
        # existing per-day warning log
```

Reason: a connection/session-open failure for one day must remain within that
day's best-effort failure policy. It must not escape to the outer gather and
allow sibling coroutines to outlive the tracked parent task.

Keep one concurrent gather over all seven `_calc_one` coroutines. Do not add
sequential awaits, cancellation swallowing or a second task registry.

Update the existing `get_today_payload` function-contract `side_effects` line
without adding lines if possible. It must state that the method may schedule a
best-effort week-prefetch task in addition to DB/sidecar/LLM effects.

## 5. Prefetch regression assertions must prove session identity

The current in-progress test counts fake factory calls but does not record the
child service's actual `self.db`; it therefore does not prove that the request
DB object was not reused.

In `test_prefetch_week_never_propagates_preview_context`:

1. create an explicit `request_db` sentinel and construct the parent service
   with it;
2. have the fake `SessionLocal` factory create seven distinct fake session
   objects;
3. record each fake object in `created_sessions`;
4. record the exact objects returned by `__aenter__` and passed to
   `__aexit__`;
5. patch `TodayService.get_today_payload` at class level and record
   `self.db`, positional args and kwargs for every child call;
6. assert exact set/identity equality among created, entered, exited and child
   `self.db` objects;
7. assert every child `self.db is not request_db`;
8. assert every call has positional values `(user_id, expected_day, None)` and
   exact kwargs `{"skip_prefetch": True}`;
9. assert exact dates `today-3 ... today+3`, independent of completion order;
10. assert no `selection_context` argument.

Do not use integer counters as a substitute for object identity. Do not combine
multiple statements with semicolons. Keep the test readable and deterministic.

`test_today_preview_transport.py` was already 997 lines before R1 and must stay
at or below the GRACE 1000-line limit. Blank-line-only compaction outside the
prefetch test is authorized only to satisfy that mechanical limit. Outside:

- the `timedelta` import;
- the exact prefetch test function;
- blank-line-only removals needed for the line limit;

there must be no token/behavior/assertion change in this file.

## 6. GRACE note for the touched day fallback test

Doc 164 requires all six original tracked paths to be GRACE-clean. The existing
header in `test_day_no_birthday_fallback.py` was malformed before R1, so the
already in-progress repair to a paired module contract/map and contracts for
its three tests is authorized.

Do not add new tests or alter their business assertions. This GRACE repair does
not change the collection count.

The newly authorized `test_wave3_day_pipeline_reuse.py` must also remain
GRACE-clean; do not rewrite its existing header/markers if already clean.

## 7. Correct full API command

Doc 164 section 9.3 used the wrong working directory. Running from
`apps/api` makes root-relative/path-sensitive tests fail with unrelated
`FileNotFoundError` or `ModuleNotFoundError: scripts`.

Supersede that command with this exact root command:

```bash
cd /opt/solarsage-astro
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
```

Require unchanged:

```text
1406 passed
4 skipped
0 failed
0 errors
```

The two failures observed from a wrong `cd apps/api` invocation are not product
failures and must not be fixed by changing source/tests/import paths.

All lifecycle-warning rejection strings from doc 164 remain mandatory.

## 8. Additional focused gate

From repository root run:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_day_no_birthday_fallback.py \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_wave3_day_pipeline_reuse.py \
  -q
```

Do not hard-code a guessed count. Report the collected/pass count exactly.
No test may be added, removed, skipped or deselected.

Ruff and GRACE final path lists now contain all seven paths from section 3.
Cold MyPy, original ten-file targeted `226 passed`, contract checks and all
other doc-164 gates remain unchanged.

## 9. Updated callback

Use doc-164 callback with these replacements/additions:

```text
READY_STAGE_2_W3B3_R1A_ARCH_REVIEW
final_tracked_scope: EXACT_7_FILES
semantic_test_doubles: CANONICAL_SEMANTIC_LAYER_2_FILES
prefetch_per_day_failure_boundary: SESSION_OPEN_THROUGH_PAYLOAD
prefetch_direct_regression: PASS_7_FRESH_IDENTITIES_7_ENTERED_7_EXITED_NO_REQUEST_DB
ruff: PASS_ZERO_7
authorized_grace: PASS_7
focused_tests: N_PASS_3_FILES
api_full: 1406_PASS_4_SKIP_ZERO_LIFECYCLE_WARNINGS
```

Keep every other callback field from doc 164. Then stop without staging,
commit, push, service changes or next-wave work.
