# Stage 2.W3B2 — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`1e3fe7de712619bf69fc18d504293fa93d15530f`
Accepted implementation chain:

- `159_STAGE_2_W3B2_PURE_SELECTION_GUIDANCE_MYPY_TZ.md`;
- `161_STAGE_2_W3B2_R1_INVALID_PARTIAL_TIMING_FAILSAFE_TZ.md`.

Prepared but still unauthorized successor:
`160_STAGE_2_W3B3_SEMANTIC_TODAY_INTEGRATION_MYPY_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Architect acceptance

Architect independently reviewed the complete nine-file delta, reran the cold
MyPy proof and directly reproduced the invalid-partial timing regression.

Accepted semantics:

```text
generic ordered intersections
  read-only inputs, input string subtype and first-input order preserved

canonical theme resolution
  one shared no-cast resolver against validated language canon keys
  generator/policy use the same boundary
  valid theme selection order unchanged

action construction
  exact ActionTemplate and HorizonSphereVerdict types
  filtering/safety/slicing/provenance unchanged

claim validation
  read-only closed horizon map
  truthful NoReturn failure helper, no added assertion/cast

formatter
  typed product-sphere scan equivalent to unique-key dict lookup

selection
  generic subtype-preserving collection helpers
  exact closed horizon dictionary annotations
  scoring/ranking/tie breaks/bounds unchanged

timing
  exact canon/timing/horizon/warning types
  canonical HORIZON_ORDER equals previous long/medium/fast order
  malformed partial timing now satisfies documented fail-safe invariant:
    precision null + invalid_timing + ineligible
  valid partial/mixed/date/instant behavior unchanged

personal facts
  fixed two-element unpack preserves canonical planet ordering
```

Accepted evidence:

```text
tracked implementation scope          exact 9 paths (8 production + 1 test)
W3B2 MyPy before                      28 diagnostics / 8 paths
W3B2 MyPy after                        0
global cold MyPy after                90 diagnostics / 13 paths
future W3B3                           10 diagnostics / 2 paths unchanged
legacy baseline                       80 diagnostics / 11 paths unchanged
outside normalized MyPy drift          0
Ruff                                  PASS_ZERO_9
GRACE self-tests                      13 PASS
authorized GRACE                       9/9 PASS
timing service tests                  19 PASS
targeted regression                   10 files / 232 PASS
full API                              1406 passed / 4 skipped
contracts check                       PASS_NO_DRIFT
contracts compatibility               additive / zero breaking
fixture normalization                 PASS
shared Python contracts               44 PASS
frontend guard                        PASS
git diff check                        PASS_ZERO
index                                 empty
runtime/services                      unchanged
ports 3003/8001/18092                 absent
```

The full API count intentionally increased by one because R1 added exactly one
parameter case to an existing test function. No production endpoint or wire
contract count changed.

No correction wave remains. No file edit is authorized in this acceptance
wave.

## 2. Frozen accepted hashes

Require exactly before staging:

```text
be78bcb77f9c2b125828be29cd727eea881f617cda185ada84a01c07d359cd53  apps/api/app/services/horizon_claim_policy.py
598c06661dd48a0d2a9127eab01d50fa3b1b3f3f24b18abc927fe73e6bc4963a  apps/api/app/services/horizon_claim_validator.py
52050b364497eed78ee23392b0733993b91fc5fc2b406a7e4d969f49aa5201c1  apps/api/app/services/horizon_guidance_builders.py
95d292ef7ab315aadddda494390ef5496694337f23e71b821b0640686bd990fe  apps/api/app/services/horizon_guidance_formatter.py
c90a1d2d3a42d4bac539c620c4cbc7ed29008f9b84a54a6da02a3e7ac2174cb2  apps/api/app/services/horizon_guidance_service.py
37b08c220081a30fe5d396e10e881c6c6ac060f3453c68b694202f3e372aa149  apps/api/app/services/horizon_selection_service.py
dfb748836af7c33a32e7a8a4193b6ffbf58d0ed82d7afac4fc3242addbadb0ba  apps/api/app/services/horizon_timing_service.py
d6f7ee19540e8c4fef018d271183c53a62ff3044ebc5cd859fefd56330d7b19e  apps/api/app/services/personal_fact_pack_service.py
1e251ef2409aea679480e297edc7f2218eed784e841a47b4d9cfa69cad98eb4f  apps/api/tests/test_horizon_timing_service.py
```

## 3. Mandatory preflight

Before staging:

1. completely read `127`, `159`, `160`, `161`, and `162`;
2. run `git fetch origin` without merge/rebase;
3. prove branch exactly
   `preview/solarsage-v2-human-first-navigator-ux`;
4. prove HEAD = tracking = remote feature =
   `1e3fe7de712619bf69fc18d504293fa93d15530f`;
5. prove main = origin/main =
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and both are ancestors;
6. prove index empty;
7. prove tracked diff exact nine implementation paths from section 4;
8. prove all nine hashes exactly match section 2;
9. prove docs `159`, `160`, `161`, `162` are untracked and unchanged;
10. prove only five frozen unrelated groups otherwise remain untracked;
11. reproduce Ruff/GRACE zero and cold MyPy 90/13;
12. directly prove invalid partial timing returns `invalid_timing` without
    escaping ValidationError;
13. prove services/runtime and ports unchanged.

Stop on mismatch. Never edit, reset, restore, checkout paths, stash, amend,
rebase or force-push.

## 4. Exact implementation paths

```text
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
apps/api/app/services/horizon_guidance_builders.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/horizon_selection_service.py
apps/api/app/services/horizon_timing_service.py
apps/api/app/services/personal_fact_pack_service.py
apps/api/tests/test_horizon_timing_service.py
```

## 5. Exact task-document paths

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/159_STAGE_2_W3B2_PURE_SELECTION_GUIDANCE_MYPY_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/160_STAGE_2_W3B3_SEMANTIC_TODAY_INTEGRATION_MYPY_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/161_STAGE_2_W3B2_R1_INVALID_PARTIAL_TIMING_FAILSAFE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/162_STAGE_2_W3B2_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

## 6. Exact staging set

Stage only exact thirteen explicit paths:

```text
9 implementation paths from section 4
4 task-document paths from section 5
```

Use explicit paths. Forbidden: broad `git add`, directory/wildcard staging or
staging any frozen/unrelated file.

Before commit require:

```text
staged count                    13
staged set                      exact 9 implementation + exact 4 docs
unstaged tracked diff           empty
cached diff check               PASS_ZERO
cached implementation hashes    exact section 2
cached frozen/unrelated paths    zero
```

Inspect the complete cached delta. Stop on mismatch; no edit is authorized.

## 7. Exact commit

Create exactly one normal commit with subject:

```text
refactor(api): type horizon guidance pipeline
```

After commit require:

```text
parent                          1e3fe7de712619bf69fc18d504293fa93d15530f
subject                         exact
changed paths                   exact 13
implementation paths            exact 9
task docs                       exact 4
tracked worktree                clean
index                           empty
```

No amend, fixup, second commit or W3B3 implementation.

## 8. Mandatory post-commit gates

### 8.1. Ruff and GRACE

Run Ruff on the exact nine implementation paths and require zero.

```bash
apps/api/.venv/bin/python scripts/test_grace_lint.py
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/services/horizon_claim_policy.py \
  apps/api/app/services/horizon_claim_validator.py \
  apps/api/app/services/horizon_guidance_builders.py \
  apps/api/app/services/horizon_guidance_formatter.py \
  apps/api/app/services/horizon_guidance_service.py \
  apps/api/app/services/horizon_selection_service.py \
  apps/api/app/services/horizon_timing_service.py \
  apps/api/app/services/personal_fact_pack_service.py \
  apps/api/tests/test_horizon_timing_service.py
```

Require 13 self-tests PASS and exact nine files clean.

### 8.2. Cold MyPy proof

From `apps/api`:

```bash
set +e
./.venv/bin/mypy app --no-incremental --no-error-summary --show-error-codes \
  > /tmp/stage2-w3b2-acceptance-mypy.log 2>&1
rc=$?
set -e
test "$rc" -eq 1
```

Require:

```text
global diagnostics               90
global failing paths             13
W3B2 production paths             0
W3B3 frozen                      10 / 2
legacy frozen                    80 / 11
new/migrated                      0
```

### 8.3. Regression suites

Run the exact ten-file targeted command from doc 159 and require 232 PASS.

Then:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
pnpm guardrails:frontend
git diff --check origin/main...HEAD
```

Require API 1406 PASS / 4 SKIP, contracts no drift/additive zero breaking,
fixture clean, 44 py-contract tests, frontend guard and feature diff check all
green.

## 9. Normal push and final equality

Only after every post-commit gate passes:

1. normal push existing feature branch; never force/change upstream;
2. prove local HEAD = tracking = remote feature SHA;
3. prove exact parent, subject and thirteen-path commit set;
4. prove tracked worktree clean and index empty;
5. prove only five frozen unrelated untracked groups remain;
6. prove `main`/`origin/main` untouched and ancestors;
7. prove runtime/env/systemd/nginx/database untouched;
8. prove ports `3003`, `8001`, `18092` absent.

Do not begin W3B3 before callback and a separate architect message sending
doc `160`. Its presence in the commit is traceability, not self-authorization.

## 10. Frozen unrelated paths

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 11. Required callback

```text
PUSHED_STAGE_2_W3B2_PURE_SELECTION_GUIDANCE_MYPY_CLEAN
commit: <sha> refactor(api): type horizon guidance pipeline
staged_scope: EXACT_13
implementation_scope: EXACT_9_8_PRODUCTION_1_TEST
task_docs: EXACT_4
source_hashes: PASS_9
theme_boundary: CLOSED_RESOLVER_NO_CAST
collection_typing: GENERIC_READ_ONLY
invalid_partial_behavior: INELIGIBLE_INVALID_TIMING
mypy_w3b2: PASS_ZERO
mypy_total: 90_DIAGNOSTICS_13_PATHS
mypy_w3b3_frozen: 10_DIAGNOSTICS_2_PATHS
mypy_legacy_frozen: 80_DIAGNOSTICS_11_PATHS
ruff: PASS_ZERO_9
grace_selftests: 13_PASS
authorized_grace: PASS_9
targeted_tests: 10_FILES_232_PASS
api_full: 1406_PASS_4_SKIP
contracts_check_compat_fixture: PASS
py_contracts: 44_PASS
frontend_guard: PASS
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop. W3B3/W3C/final RC/main/deploy remain forbidden.
