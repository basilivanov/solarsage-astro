# Stage 2.W3B2 R1 — invalid partial timing fail-safe correction

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`1e3fe7de712619bf69fc18d504293fa93d15530f`
Parent implementation:
`159_STAGE_2_W3B2_PURE_SELECTION_GUIDANCE_MYPY_TZ.md`.

Статус: **MANDATORY ARCHITECT REVIEW CORRECTION — NO COMMIT/PUSH**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Architect finding

The eight-file W3B2 implementation is structurally sound and reaches the
required static target:

```text
W3B2 MyPy       28 -> 0
global MyPy     118/21 -> 90/13
outside W3B2    normalized-identical
Ruff/GRACE      clean
targeted        231 PASS
API full        1405 PASS / 4 SKIP
```

However, review proved one unaccepted runtime behavior change in
`HorizonTimingService.classify`.

Input shape:

```text
active_from   malformed non-null string, e.g. "bad"
active_until  null
exact_at      null
```

Observed semantics:

```text
pre-W3B2 implementation
  _detect_precision -> "invalid"
  partial-boundary branch forwards precision="invalid"
  HorizonTimingAssessment rejects the non-contract literal
  result: Pydantic ValidationError escapes

current W3B2 implementation
  partial-boundary branch rewrites precision to null
  result: ineligible assessment with warning partial_timing
```

The second outcome avoids the crash but misclassifies malformed evidence as a
mere missing-boundary case. It also makes the callback claim
`runtime_equivalence: PASS` false.

The module contract already requires ordinary invalid evidence to return a
typed ineligible assessment instead of raising. The correct fix is explicit:
classify malformed partial evidence as `invalid_timing`, not preserve the old
crash and not relabel it `partial_timing`.

## 2. Exact R1 edit scope

Edit only:

```text
apps/api/app/services/horizon_timing_service.py
apps/api/tests/test_horizon_timing_service.py
```

The other seven current W3B2 production paths are byte-frozen:

```text
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
apps/api/app/services/horizon_guidance_builders.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/horizon_selection_service.py
apps/api/app/services/personal_fact_pack_service.py
```

Docs `159`, `160`, `161` are architect-owned and must remain unchanged and
un-staged.

No other source/test/config/contract edit. No `git add`, commit or push. Do not
start W3B3.

## 3. Exact production correction

Inside `HorizonTimingService.classify`, preserve the early
`precision is None` missing-timing branch.

Move the existing `precision == "invalid"` return branch so it executes before
the `active_from is None or active_until is None` partial-boundary branch.

Required order:

```text
1. precision is None          -> missing_timing
2. precision == invalid       -> invalid_timing
3. missing active boundary:
     precision == mixed       -> mixed_precision, precision null
     date/instant             -> partial_timing, precision preserved
4. precision == mixed         -> mixed_precision
5. normal date/instant flow
```

Remove the now-duplicate later invalid branch. Do not duplicate code.

Restore the partial branch to a statically narrowed expression equivalent to:

```python
precision=None if precision == "mixed" else precision
```

At that point control-flow must prove that the non-mixed value is only
`date | instant`; no cast, ignore or broad `str` is allowed.

Do not change:

- `_detect_precision`;
- `_safe_assessment` types;
- warning literals;
- target-clock handling;
- timing arithmetic/states/durations;
- horizon eligibility or source speed behavior.

## 4. Exact regression proof

Extend the existing parametrized matrix
`test_timing_error_and_target_clock_matrix` by exactly one case:

```python
(
    {
        "active_from": "bad",
        "exact_at": None,
        "active_until": None,
    },
    {},
    "invalid_timing",
),
```

The existing test already proves returned assessment warning semantics. Do not
add a new test function, helper, fixture or production-only assertion.

Expected targeted suite total changes from 231 to 232 solely because of this
new parameter case.

## 5. Frozen/current hashes before R1

```text
eb9eb2dd5e1dc05aec40eca7604d5a20832d94f44bec901adca830fde4443903  apps/api/app/services/horizon_timing_service.py
d02223dfb71b69dcb14cb3288ada3e80f248fc172ac7fbf963429ce9c4b24a16  apps/api/tests/test_horizon_timing_service.py
```

Snapshot/hash all other seven W3B2 paths before editing and prove they remain
byte-identical afterward.

## 6. Mandatory gates

### 6.1. Direct regression

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_horizon_timing_service.py \
  -q
```

Record the exact file test count and prove the newly added parameter returns:

```text
precision       null
warning_codes   ["invalid_timing"]
eligible        false
```

### 6.2. W3B2 static proof

Repeat exact eight production-file Ruff and GRACE commands from doc 159, plus
GRACE on `test_horizon_timing_service.py`.

Require:

```text
Ruff production exact 8       zero
Ruff changed test             zero
GRACE self-tests              13 PASS
GRACE production exact 8      clean
GRACE changed test            clean
```

Repeat cold MyPy from doc 159. Require exactly unchanged:

```text
global diagnostics            90
global failing paths          13
W3B2 production paths          0
W3B3 frozen                   10 / 2
legacy frozen                 80 / 11
outside normalized drift       0
```

### 6.3. Targeted/full regression

Repeat the exact ten-file targeted suite from doc 159. Require:

```text
10 files / 232 PASS
```

Then run:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
pnpm guardrails:frontend
git diff --check
```

Require API full becomes exactly 1406 PASS / 4 SKIP because the parametrized
case adds one collected test; contracts/fixture/44/frontend/diff remain green.

## 7. Final scope

Final W3B2 tracked scope after R1 is exact nine paths:

```text
8 production service files from doc 159
1 test file: apps/api/tests/test_horizon_timing_service.py
```

Require index empty, docs untracked/unchanged, frozen unrelated paths untouched,
HEAD/tracking/remote still base SHA, main untouched, services unchanged and
ports `3003`, `8001`, `18092` absent.

## 8. Required callback

```text
READY_STAGE_2_W3B2_R1_INVALID_PARTIAL_TIMING_FIXED
base_head: 1e3fe7de712619bf69fc18d504293fa93d15530f
tracked_scope: EXACT_9_FILES_8_PRODUCTION_1_TEST
r1_scope: TIMING_SERVICE_PLUS_EXISTING_PARAM_MATRIX
invalid_partial_behavior: INELIGIBLE_INVALID_TIMING
old_validation_escape: CLOSED
partial_valid_behavior: UNCHANGED
mypy_w3b2: PASS_ZERO
mypy_total: 90_DIAGNOSTICS_13_PATHS
mypy_w3b3_frozen: 10_DIAGNOSTICS_2_PATHS
mypy_legacy_frozen: 80_DIAGNOSTICS_11_PATHS
mypy_new_migrated: ZERO
ruff: PASS_ZERO_9
grace_selftests: 13_PASS
authorized_grace: PASS_9
timing_tests: <N>_PASS
targeted_tests: 10_FILES_232_PASS
api_full: 1406_PASS_4_SKIP
contracts_check_compat_fixture: PASS
py_contracts: 44_PASS
frontend_guard: PASS
git_diff_check: PASS_ZERO
index: EMPTY
commit_push: NOT_PERFORMED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop. W3B3/W3C/final RC/main/deploy remain forbidden.
