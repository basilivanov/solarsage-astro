# Stage 2.W3A — architect acceptance, exact commit and push

Дата: `2026-07-13`
Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`1dd9d8ab2c9126bab29bfa0acf32b201dcd9284b`
Accepted implementation:
`153_STAGE_2_W3A_FEATURE_API_RUFF_CORRECTION_TZ.md`.
Prepared next wave:
`155_STAGE_2_W3B1_SCHEMA_MYPY_CORRECTION_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZED EXACT COMMIT/PUSH ONLY**

Исполнитель работает лично. Запрещены subagents, delegation, `delegate_*`,
background coding/review tasks и использование их результатов как evidence.

## 1. Accepted evidence

Architect independently reviewed all 19 diffs, verified the two intentional
re-exports, both lambda-to-def closures, the repo-root import bootstrap and the
complete real-proof test formatting expansion. Material gates were rerun.

```text
tracked implementation scope          exact 19 API Ruff files
Ruff before                           97 diagnostics / 19 paths
Ruff after                            zero / All checks passed
intentional version re-exports        preserved by same-name aliases
PRODUCT_SPHERE_ORDER re-export        preserved by same-name alias
removed imports                       exact Ruff-proven dead names
lambda -> nested def                  equivalent 2/2
evaluated F541 strings                byte-equivalent 3/3
fixture E402 suppressions             exact two authorized lines only
real-proof tests                      formatting/dead-import cleanup only
test functions/params/assertions      unchanged
GRACE self-tests                      13 PASS
authorized GRACE                      19/19 PASS
targeted regression                   14 files / 295 tests PASS
full API                              1405 passed / 4 skipped
contracts check/compat/fixture        PASS / additive 0 breaking / PASS
shared Python contracts               44 PASS
MyPy diagnostic count                 129 / 24 paths before and after
MyPy normalized output                identical
frontend guard                        PASS
git diff check                        PASS
index                                 empty
runtime/services                      unchanged
ports 3003/8001/18092                 absent
```

No correction wave is required. No content edit is authorized here.

## 2. Mandatory preflight

Before staging:

1. completely read 127, 153, 154 and 155;
2. run `git fetch origin` without merge/rebase;
3. prove current branch exactly
   `preview/solarsage-v2-human-first-navigator-ux`;
4. prove local HEAD = tracking = remote feature =
   `1dd9d8ab2c9126bab29bfa0acf32b201dcd9284b`;
5. prove `main` and `origin/main` remain
   `c9bc36bd9a947566eddb1ffcf5617967c7412676` and are ancestors;
6. prove index empty;
7. prove tracked diff exact 19 implementation paths from section 3;
8. reproduce Ruff zero and review the intentional re-export aliases;
9. prove 154 and 155 are the only task docs untracked;
10. prove only five frozen unrelated paths otherwise remain untracked;
11. prove runtime services unchanged and ports `3003`, `8001`, `18092` absent.

Stop on mismatch. Never reset, restore, checkout paths, stash, amend, rebase or
force-push. Do not edit any file during this wave. If a scope, whitespace or
evidence mismatch exists, stop for architect correction.

## 3. Exact implementation paths

```text
apps/api/app/core/versions.py
apps/api/app/schemas/horizon_content_canon.py
apps/api/app/schemas/horizon_content_canon_types.py
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_service.py
apps/api/app/services/personal_fact_pack_service.py
apps/api/tests/_horizon_guidance_testkit.py
apps/api/tests/test_horizon_actions_canon.py
apps/api/tests/test_horizon_canon_service.py
apps/api/tests/test_horizon_claim_validator.py
apps/api/tests/test_horizon_coverage.py
apps/api/tests/test_horizon_guidance_service.py
apps/api/tests/test_horizon_pipeline_service.py
apps/api/tests/test_horizon_selection_service.py
apps/api/tests/test_real_today_v2_api_proof.py
apps/api/tests/test_today_fixture_contract.py
apps/api/tests/test_today_horizon_integration_service.py
```

## 4. Exact task-document paths

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/154_STAGE_2_W3A_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/155_STAGE_2_W3B1_SCHEMA_MYPY_CORRECTION_TZ.md
```

Coder stages both exactly as written and does not edit them.

## 5. Exact staging set

Stage only exact 21 explicit paths:

```text
19 implementation paths from section 3
2 task-document paths from section 4
```

Use explicit paths. Forbidden: broad `git add`, directory/wildcard staging or
staging frozen/unrelated files.

Before commit require:

```text
staged count                    21
staged set                      exact 19 implementation + exact 2 docs
unstaged tracked diff           empty
cached diff check               PASS
intentional re-exports          present and unchanged in value/identity
cached suppression additions    exact two E402 lines only
frozen/unrelated in index       zero
```

## 6. Exact commit

Create exactly one normal commit with exact subject:

```text
chore(api): clear feature ruff diagnostics
```

After commit require:

```text
parent                          1dd9d8ab2c9126bab29bfa0acf32b201dcd9284b
subject                         exact
changed paths                   exact 21
implementation paths            exact 19
task docs                       exact 2
tracked worktree                clean
index                           empty
```

No amend, fixup, second commit or W3B1 implementation.

## 7. Mandatory post-commit gates

### 7.1. Exact Ruff and GRACE scope

Run the exact 19-path Ruff command from doc 153 section 9 and require exit zero
with `All checks passed!`.

Then:

```bash
apps/api/.venv/bin/python scripts/test_grace_lint.py
apps/api/.venv/bin/python scripts/grace_lint.py \
  <exact 19 implementation paths>
```

Require 13 self-tests PASS and 19 files clean.

### 7.2. Targeted and full API

Run the exact 14-file targeted command from doc 153 section 10.2 and require:

```text
14 files / 295 tests PASS
```

Then:

```bash
PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest apps/api/tests/ -q
```

Require 1405 passed / 4 skipped.

### 7.3. Contracts

```bash
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
```

Require no drift, additive compatibility with zero breaking changes, fixture
clean and 44 PASS.

### 7.4. MyPy diagnostic baseline

From `apps/api`:

```bash
./.venv/bin/mypy app --no-error-summary --show-error-codes
```

This remains expected-nonzero before W3B. Require exactly 129 diagnostics /
24 paths and no normalized drift from the accepted W3A callback. Do not fix or
stage a MyPy change here.

### 7.5. Frontend and feature integrity

```bash
pnpm guardrails:frontend
git diff --check origin/main...HEAD
```

Require frontend PASS and feature diff PASS_ZERO.

## 8. Normal push and final equality

After every post-commit gate passes:

1. normal push the existing feature branch; never force/change upstream;
2. prove local HEAD = tracking = remote feature SHA;
3. prove exact parent, subject and 21-path commit set;
4. prove tracked worktree clean and index empty;
5. prove only five frozen unrelated untracked paths remain;
6. prove `main`/`origin/main` untouched and still ancestors;
7. prove env/systemd/nginx/database/runtime untouched;
8. prove ports `3003`, `8001`, `18092` absent.

Do not begin W3B1 before callback and a separate architect message. Committed
doc 155 is traceability, not self-authorization.

## 9. Frozen unrelated paths

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 10. Required callback

```text
PUSHED_STAGE_2_W3A_FEATURE_API_RUFF_CLEAN
commit: <sha> chore(api): clear feature ruff diagnostics
staged_scope: EXACT_21
implementation_scope: EXACT_19_API_RUFF_FILES
task_docs: EXACT_2
ruff: PASS_ZERO
intentional_reexports: PRESERVED
grace_selftests: 13_PASS
authorized_grace: PASS_19
targeted_tests: 14_FILES_295_PASS
api_full: 1405_PASS_4_SKIP
contracts_check_compat_fixture: PASS
py_contracts: 44_PASS
mypy_baseline: 129_DIAGNOSTICS_24_PATHS_UNCHANGED
frontend_guard: PASS
feature_diff_check: PASS_ZERO
head_tracking_remote: EQUAL
tracked_index: CLEAN_EMPTY
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
main_deploy: NOT_STARTED
```

Then stop.
