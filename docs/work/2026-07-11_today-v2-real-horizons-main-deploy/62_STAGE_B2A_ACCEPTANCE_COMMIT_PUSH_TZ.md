# Stage B2A — architect acceptance and scoped commit/push

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Pre-commit HEAD/origin: `3a58c581bbe010e98e78b2295a135f138d32bd88`
Implementation/review chain: `56_...` through `61_...`
Статус: **ACCEPTED FOR EXACT SCOPED COMMIT/PUSH**

## 1. Architect verdict

Stage B2A принят.

Принятый результат:

- отдельный versioned `horizon_selection.v1` canon;
- strict typed startup validation без изменения core canon/cache identity;
- pure target-clock timing classifier без server clock;
- deterministic technical -> product sphere/theme mapping;
- bounded deterministic candidate ranking;
- coherent long/medium/fast triple selection;
- honest typed null reasons;
- self-contained selected anchors с raw timing и candidate features для B2B;
- mutation-sensitive ordering and bounds tests;
- no Today/Semantic/public/frontend/sidecar population yet.

Production behavior после B2A остаётся прежним: `TodayV2Block.horizons` всё ещё
не заполняется реальными backend horizons. Это будет B3 после B2B.

## 2. Закрытые review findings

Подтверждено:

- priority coverage exactly equals allowed horizons; runtime `KeyError` from
  malformed canon is impossible after startup validation;
- all normalized canon values finite in `0..1`;
- selected anchors preserve complete timing, feature scores and convergence;
- internal models reject inconsistent order/ranges/identities and use typed
  warnings/exclusion keys;
- preferred horizon semantics follow technique preference, then preferred-band
  fallback;
- unexpected programming errors propagate instead of becoming ordinary timing
  fallback;
- scoring sphere/key/contribution identities and finite numeric ordering inputs
  fail fast;
- pair scores round before threshold comparison;
- all five overlap components are isolated and once-only;
- family diversity is a `0/0.5/1` bonus and cannot bypass pair thresholds;
- candidate/triple tie-breaks use one production source of truth;
- inactive evidence never reaches classification/mapping;
- input pre-bound proves strength, technique priority, ID and reverse-order
  determinism at the exact 256 cutoff;
- diagnostics use exact pre/post/candidate/cartesian semantics;
- 12x12x12 benchmark evaluates exactly 1728 combinations;
- GRACE maps/contracts are accurate;
- the former 998-line compressed test file is split into readable modules;
- seventh-decimal rounding regression is restored after the split.

## 3. Independent architect gates

### 3.1 B2A focused

```text
55 passed in 2.04s
```

Includes:

- canon/startup;
- timing boundaries;
- sphere mapping;
- core selection;
- ordering/bounds;
- benchmark.

### 3.2 Contracts

```text
pnpm contracts:check: 110 focused tests passed
generation: PASS
fixture normalization: PASS
generated/public diff: ZERO
```

### 3.3 GRACE and maintainability

```text
13 B2A app/test files: PASS

_horizon_selection_testkit.py:       315 lines
test_horizon_selection_service.py:   479 lines
test_horizon_selection_ordering.py:  595 lines
```

Normal formatting restored; no whitespace compression.

### 3.4 Benchmark

Independent architect run:

```text
p95=17.311ms
runs=20
combinations=1728
budget=<100ms
```

### 3.5 Full API regression

Independent architect run:

```text
6 failed, 937 passed, 5 skipped, 1 warning
```

Failure set is exactly the existing accepted baseline:

```text
tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row
tests/test_semantic_v2_service.py::test_semantic_v2_service_no_convergence
tests/test_semantic_v2_service.py::test_semantic_v2_service_with_convergence
tests/test_semantic_v2_service.py::test_audit_canon_versions_only_contains_strings
tests/test_semantic_v2_service.py::test_techniques_list_is_sorted
tests/test_today_v2_payload.py::test_today_payload_v2_block_included_when_flag_enabled
```

No new failures. Final release в `main` всё равно требует отдельной B5
stabilization wave и fully green final gate; baseline-red не считается release
green.

### 3.6 Static/scope

```text
git diff --check: PASS
index: EMPTY
HEAD == origin feature: PASS
public contracts/OpenAPI diff: ZERO
frontend/sidecar/Today integration diff: ZERO
```

## 4. Exact commit scope

Добавить в index только эти paths:

```text
grace/canon/horizon_selection.v1.yml

apps/api/app/schemas/horizon_canon.py
apps/api/app/schemas/horizon_selection.py

apps/api/app/services/canon_service.py
apps/api/app/services/horizon_canon_service.py
apps/api/app/services/horizon_timing_service.py
apps/api/app/services/horizon_sphere_mapping_service.py
apps/api/app/services/horizon_selection_service.py

apps/api/tests/test_canon_service.py
apps/api/tests/test_horizon_canon_service.py
apps/api/tests/test_horizon_timing_service.py
apps/api/tests/test_horizon_sphere_mapping_service.py
apps/api/tests/_horizon_selection_testkit.py
apps/api/tests/test_horizon_selection_service.py
apps/api/tests/test_horizon_selection_ordering.py
apps/api/tests/test_horizon_selection_benchmark.py

docs/work/2026-07-11_today-v2-real-horizons-main-deploy/56_STAGE_B2A_CANON_TIMING_SELECTION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/57_STAGE_B2A_ARCH_REVIEW_CORRECTIONS_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/58_STAGE_B2A_ARCH_REVIEW_TEST_COMPLETENESS_R2_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/59_STAGE_B2A_ARCH_REVIEW_MUTATION_ADEQUACY_R3_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/60_STAGE_B2A_ARCH_REVIEW_TEST_FILE_SPLIT_R4_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/61_STAGE_B2A_ARCH_REVIEW_RESTORE_ROUNDING_REGRESSION_R5_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/62_STAGE_B2A_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Не добавлять:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Не использовать `git add .`, `git add -A`, wildcard или directory add.

## 5. Exact staging verification

Сделать один explicit command:

```bash
git add -- \
  grace/canon/horizon_selection.v1.yml \
  apps/api/app/schemas/horizon_canon.py \
  apps/api/app/schemas/horizon_selection.py \
  apps/api/app/services/canon_service.py \
  apps/api/app/services/horizon_canon_service.py \
  apps/api/app/services/horizon_timing_service.py \
  apps/api/app/services/horizon_sphere_mapping_service.py \
  apps/api/app/services/horizon_selection_service.py \
  apps/api/tests/test_canon_service.py \
  apps/api/tests/test_horizon_canon_service.py \
  apps/api/tests/test_horizon_timing_service.py \
  apps/api/tests/test_horizon_sphere_mapping_service.py \
  apps/api/tests/_horizon_selection_testkit.py \
  apps/api/tests/test_horizon_selection_service.py \
  apps/api/tests/test_horizon_selection_ordering.py \
  apps/api/tests/test_horizon_selection_benchmark.py \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/56_STAGE_B2A_CANON_TIMING_SELECTION_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/57_STAGE_B2A_ARCH_REVIEW_CORRECTIONS_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/58_STAGE_B2A_ARCH_REVIEW_TEST_COMPLETENESS_R2_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/59_STAGE_B2A_ARCH_REVIEW_MUTATION_ADEQUACY_R3_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/60_STAGE_B2A_ARCH_REVIEW_TEST_FILE_SPLIT_R4_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/61_STAGE_B2A_ARCH_REVIEW_RESTORE_ROUNDING_REGRESSION_R5_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/62_STAGE_B2A_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Then:

```bash
git diff --cached --name-only
git diff --cached --check
git status --short
```

Staged list must equal section 4 literally: 23 paths. If not exact — unstage only
the wrong path safely and stop; do not use destructive reset/checkout.

## 6. Commit

One commit only:

```text
feat(today): add deterministic horizon selection
```

Command:

```bash
git commit -m "feat(today): add deterministic horizon selection"
```

No amend/rebase/squash.

## 7. Post-commit gates before push

```bash
cd apps/api
.venv/bin/python -m pytest \
  tests/test_canon_service.py \
  tests/test_horizon_canon_service.py \
  tests/test_horizon_timing_service.py \
  tests/test_horizon_sphere_mapping_service.py \
  tests/test_horizon_selection_service.py \
  tests/test_horizon_selection_ordering.py \
  tests/test_horizon_selection_benchmark.py -q

cd ../..
pnpm contracts:check
git diff --check

cd apps/api
.venv/bin/python -m pytest tests -q
```

Expected:

```text
focused: 55 passed
contracts: PASS
API full: exact same six baseline failures only
```

If any new failure or generated diff appears: do not push and return blocker.

## 8. Push

Only after section 7:

```bash
git push origin preview/solarsage-v2-human-first-navigator-ux
```

No force.

Verify:

```bash
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git log -1 --format='%H%n%s'
git status --short --branch
```

Local/origin SHA must match. Worktree may contain only known unrelated untracked
paths from section 4 exclusions.

Do not start B2B in this turn. Leave preview `3003`/`18092` running.

## 9. Callback

```text
PUSHED_STAGE_B2A_DETERMINISTIC_SELECTION
branch: preview/solarsage-v2-human-first-navigator-ux
commit: <sha>
subject: feat(today): add deterministic horizon selection
staged_scope: EXACT 23
focused_after_commit: 55 passed
contracts_check_after_commit: PASS
api_full_after_commit: BASELINE_RED_IDENTICAL 6 failed, <passed> passed, 5 skipped
push: PASS
origin_feature: <same sha>
unrelated_untracked_only: PASS
preview_3003: LEFT_RUNNING
preview_18092: LEFT_RUNNING
```

Stop after callback. No B2B yet.
