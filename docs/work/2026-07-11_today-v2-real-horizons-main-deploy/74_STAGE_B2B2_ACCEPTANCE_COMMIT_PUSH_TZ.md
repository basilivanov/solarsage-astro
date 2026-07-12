# Stage B2B2 — architect acceptance, exact commit and push

Дата: 2026-07-12  
Ветка: `preview/solarsage-v2-human-first-navigator-ux`  
Accepted parent HEAD/origin: `c47863a0c4b2be2242c276bb610a262b4b91a737`  
Implementation/review documents: `68`–`73`  
Статус: **ACCEPTED — EXACT COMMIT/PUSH ONLY**

## 1. Architect acceptance evidence

The architect independently confirmed the final R5 worktree:

~~~text
focused B2B2:                 160 passed
R5 direct sanitization:       11/11 passed
GRACE:                        12/12 PASS
coverage:                     60/60, 100.0%
strict YAML mutations:        18/18 rejected
claim/policy mutations:       91/91 rejected by intended code
benchmark isolated:           p95=24.0 ms, 1728 combinations, 23/23 runs
upstream regression:          82 passed
contracts:                    PASS_NO_PUBLIC_DIFF
full API:                     1202 passed, 4 skipped, exact six known failures
HEAD/origin:                  unchanged at c47863a...
index:                        empty
~~~

The six failures are the frozen pre-B2B2 baseline listed in documents `72` and
`73`; no new failure exists. B5 must close them before main release.

## 2. Executor protocol

- The coder performs only the mechanical commit/push described here.
- No source/test/document content changes are allowed.
- No subagents, delegation or second worktree.
- Do not switch branches.
- Do not touch `main`, services, ports, env, builds or runtime.
- Do not stage unrelated paths.
- Do not use broad `git add .`, `git add -A` or wildcard staging.
- After callback, stop. Do not start B3.

## 3. Exact allowed staged paths

Implementation and tests:

~~~text
apps/api/app/schemas/horizon_guidance.py
apps/api/app/services/horizon_claim_policy.py
apps/api/app/services/horizon_claim_validator.py
apps/api/app/services/horizon_guidance_builders.py
apps/api/app/services/horizon_guidance_formatter.py
apps/api/app/services/horizon_guidance_service.py
apps/api/tests/_horizon_guidance_testkit.py
apps/api/tests/fixtures/horizon_guidance_coverage.v1.yml
apps/api/tests/test_horizon_claim_validator.py
apps/api/tests/test_horizon_coverage.py
apps/api/tests/test_horizon_guidance_formatter.py
apps/api/tests/test_horizon_guidance_service.py
apps/api/tests/test_horizon_pipeline_benchmark.py
~~~

Owning architecture/review documents:

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/68_STAGE_B2B2_DETERMINISTIC_GUIDANCE_CLAIMS_COVERAGE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/69_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R1_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/70_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R2_NEW_CODER_HANDOFF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/71_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R3_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/72_STAGE_B2B2_ARCH_REVIEW_CORRECTIONS_R4_SANITIZATION_FINAL_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/73_STAGE_B2B2_R5_NEW_CODER_CONTINUATION_FINAL_SANITIZATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/74_STAGE_B2B2_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

Never stage or modify:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 4. Pre-stage proof

Run and capture:

~~~bash
git status --short --branch
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git diff --cached --quiet
~~~

Requirements:

- current branch is exact feature branch;
- HEAD and origin equal accepted parent SHA;
- index is empty;
- every B2B2 path above exists;
- unrelated paths remain untracked and untouched.

Perform an explicit whitespace scan over all untracked allowed files before
staging. Ordinary `git diff --check` does not inspect them.

## 5. Exact stage, audit and commit

Stage each path from section 3 explicitly with `git add -- <path...>`.

Then prove:

~~~bash
git diff --cached --name-status
git diff --cached --check
git status --short
~~~

The staged set must equal the section 3 allowlist exactly. If it differs,
unstage only the unexpected path with `git restore --staged -- <path>` and stop
if the index cannot be made exact. Do not alter file contents.

Create exactly one commit:

~~~text
feat(today): generate grounded horizon guidance deterministically
~~~

No amend.

## 6. Push and proof

Push normally:

~~~bash
git push origin preview/solarsage-v2-human-first-navigator-ux
~~~

Then verify:

~~~bash
NEW_SHA=$(git rev-parse HEAD)
ORIGIN_SHA=$(git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux)
test "$NEW_SHA" = "$ORIGIN_SHA"
git show --stat --oneline --decorate HEAD
git status --short --branch
git diff --cached --quiet
~~~

Tracked worktree/index must be clean. Only the frozen unrelated untracked paths
may remain.

## 7. Exact callback

~~~text
PUSHED_STAGE_B2B2
parent_sha: c47863a0c4b2be2242c276bb610a262b4b91a737
commit_sha: <new SHA>
origin_sha: <same SHA>
commit_subject: feat(today): generate grounded horizon guidance deterministically
staged_paths: 20 EXACT_ALLOWLIST
tracked_tree: CLEAN
index: EMPTY
unrelated_paths: UNTOUCHED
main: UNCHANGED
services: UNCHANGED
next_stage: NOT_STARTED
~~~

Stop after callback.

