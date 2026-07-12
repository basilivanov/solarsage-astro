# Stage B3.W2 — architect acceptance, exact commit and push

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted parent HEAD/origin: `ecae4d0ff95bf29953fbb6957e48c38a7d22e198`
Implementation/review documents: `78`, `79`, `79A`, `79B`
Статус: **ACCEPTED — EXACT COMMIT/PUSH ONLY**

## 1. Architect acceptance

The architect reviewed the final W2/R2 worktree and independently proved:

~~~text
focused backend:                167 passed
horizon regression:             242 passed
request-local reuse:              15 passed
contract Vitest:                  21 passed
TypeScript:                       PASS
GRACE owned files:                 3/3 PASS
fixture normalization:            PASS
contract compatibility:           breakingChanges=0, overrideUsed=false
generated OpenAPI/TS/Zod hashes:  exact expected values
canonical fixture hash:           exact expected value
new production lines >140:         0
git diff --check:                 PASS
index:                            EMPTY
HEAD/origin:                      accepted parent, equal
~~~

Source review confirmed:

- the real Today request reuses the exact request-local activation, selected
  scoring, natal context and final advice objects;
- `HorizonPipelineService` is called exactly once for the selected V2 path;
- the public payload contains a strict typed built/unavailable pipeline audit;
- current identity is `today.v2.1` / frontend `3` / content `10`;
- old `today.v2` / frontend `2` remains schema-compatible for cached rows;
- current cache rows require a valid V2 body and pipeline audit;
- horizon canon versions participate in canon and cache identity;
- `SemanticV2Service` starts from the exact nine canonical versions and only
  permits typed core-scoring overrides;
- generated contracts and normalized fixture derive from Pydantic source;
- no duplicate sidecar, natal, scoring, LLM, profile or network call was added;
- logs contain only the closed sanitized horizon diagnostic envelope.

W2 is accepted without further source changes.

## 2. Executor protocol

- Perform only the mechanical staging, commit and push defined here.
- Do not edit any source, test, fixture, generated file or document content.
- Do not run subagents or delegate.
- Do not switch branches.
- Do not touch `main`, systemd, nginx, ports, env, databases or builds.
- Do not start W3, B4 or deployment.
- Never use `git add .`, `git add -A`, directory staging or wildcards.
- Stop immediately after the exact callback.

## 3. Exact staged allowlist

### 3.1 Contract/runtime tests

~~~text
__tests__/contracts/generated-runtime.test.ts
__tests__/contracts/today-fixture-roundtrip.test.ts
~~~

### 3.2 Backend production

~~~text
apps/api/app/core/versions.py
apps/api/app/schemas/today.py
apps/api/app/services/cache_key_service.py
apps/api/app/services/canon_service.py
apps/api/app/services/semantic_v2_service.py
apps/api/app/services/today_horizon_integration_service.py
apps/api/app/services/today_service.py
~~~

### 3.3 Backend tests

~~~text
apps/api/tests/test_audit_today_modes.py
apps/api/tests/test_day_endpoints.py
apps/api/tests/test_downstream_v2_audit.py
apps/api/tests/test_horizon_canon_service.py
apps/api/tests/test_payload_v2_downstream_mapping.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_today_horizon_integration_service.py
apps/api/tests/test_today_horizons_contract.py
apps/api/tests/test_today_meta_versions.py
~~~

### 3.4 Generated contract and canonical fixture

~~~text
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
packages/contracts/_generated.ts
packages/contracts/_generated.zod.ts
packages/contracts/openapi.json
~~~

### 3.5 Audit tools

~~~text
scripts/audit_downstream_v2.py
scripts/audit_today.py
~~~

### 3.6 Owning architecture documents

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/78_STAGE_B3_W2_REAL_TODAY_POPULATION_CONTRACT_CACHE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/79_STAGE_B3_W2_ARCH_REVIEW_R1_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/79A_STAGE_B3_W2_R1_RESTART_FINAL_GATES_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/79B_STAGE_B3_W2_ARCH_REVIEW_R2_FINAL_CLEANUP_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/79C_STAGE_B3_W2_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

The exact staged set is **29 paths**.

Never stage, modify or delete:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 4. Pre-stage proof

Run from `/opt/solarsage-astro`:

~~~bash
git status --short --branch
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git diff --cached --quiet
git diff --check
~~~

Requirements:

- exact feature branch;
- local and origin SHA both equal the accepted parent;
- index is empty;
- all 24 implementation/test/generated/fixture/audit paths and all five W2
  documents exist;
- no tracked path outside section 3 is changed;
- unrelated untracked paths remain untouched.

Run an explicit trailing-whitespace scan over every untracked W2 source, test
and document. Ordinary `git diff --check` does not inspect untracked files.

Before staging, prove exact generated hashes:

~~~text
packages/contracts/openapi.json
  917a04222aeeb793bd9ce6831d2ecfdcde8666663b6542ed6d1693028daba3dd
packages/contracts/_generated.ts
  e081d9dcf1ba19290c6489b52e6b01815d5e915474aab1d28569475304608a30
packages/contracts/_generated.zod.ts
  6fc7665fe0058803eef838fb9f3b84119b97695c857153d5984966666f4be78e
e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
  6100ddc601ae06a903ca038f975818b2f0ccec12e228ab2c86993f218e2bfa4c
~~~

If any requirement differs, do not stage or repair content. Return the exact
contradiction to the architect.

## 5. Exact stage and audit

Stage every path from section 3 explicitly with one or more commands of the
form:

~~~bash
git add -- <exact-path-1> <exact-path-2> ...
~~~

Do not use a directory path.

Then prove:

~~~bash
git diff --cached --name-status
git diff --cached --check
git status --short
~~~

Compare the staged path set programmatically against the 29-path allowlist.
The sets must be exactly equal. If an unexpected path was staged, unstage only
that path with `git restore --staged -- <path>` and stop if equality cannot be
restored without changing content.

## 6. Commit and push

Create exactly one commit with subject:

~~~text
feat(today): populate real three-horizon payloads
~~~

No amend, rebase, merge, force-push or second commit.

Push normally:

~~~bash
git push origin preview/solarsage-v2-human-first-navigator-ux
~~~

## 7. Post-push proof

Run:

~~~bash
NEW_SHA=$(git rev-parse HEAD)
ORIGIN_SHA=$(git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux)
test "$NEW_SHA" = "$ORIGIN_SHA"
git show --name-status --format=fuller HEAD
git status --short --branch
git diff --cached --quiet
~~~

Requirements:

- commit subject exact;
- commit parent exact accepted parent;
- commit path set exact 29-path allowlist;
- local and origin SHA equal;
- tracked tree clean and index empty;
- only frozen unrelated untracked paths remain;
- `main` and all services remain unchanged.

## 8. Exact callback

~~~text
PUSHED_STAGE_B3_W2
parent_sha: ecae4d0ff95bf29953fbb6957e48c38a7d22e198
commit_sha: <new SHA>
origin_sha: <same SHA>
commit_subject: feat(today): populate real three-horizon payloads
staged_paths: 29 EXACT_ALLOWLIST
generated_hashes: EXACT
fixture_hash: EXACT_NORMALIZED
tracked_tree: CLEAN
index: EMPTY
unrelated_paths: UNTOUCHED
main: UNCHANGED
services: UNCHANGED
next_wave: NOT_STARTED
~~~

Stop after callback.
