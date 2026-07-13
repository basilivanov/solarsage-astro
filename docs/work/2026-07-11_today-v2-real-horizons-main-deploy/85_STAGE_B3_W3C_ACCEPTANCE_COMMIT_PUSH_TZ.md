# Stage B3.W3C — architect acceptance, runtime evidence commit and push

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted HEAD/origin: `8db2505a55a71f910bda151d39e6f8ed3036e12f`
Runtime document: `84`
Статус: **ACCEPTED — DOCS-ONLY COMMIT/PUSH**

## 1. Acceptance evidence

The architect independently confirmed:

~~~text
sidecar restart count:          exactly 1
sidecar PID:                    1593852 -> 3582982
sidecar active since:           2026-07-12 22:02:52 MSK
API PID:                        355509 unchanged
listeners:                      one canonical 127.0.0.1:18091
forbidden listeners:            no 18092 / 8001
proof date:                     2026-07-08
proof transport:                ASGI real routes
proof status:                   pass
calculation identity:           ss-calc-1.2.0
activation identity:            al-1.1
scoring identity:               ss-scoring-2.0
payload/frontend/content:       today.v2.1 / 3 / 10
pipeline:                       built / selected / 3 / deterministic
horizons:                       long, medium, fast
canon keys:                     9 exact
fixture dependency:             false
activation evidence count:      155
raw payload artifacts:          zero
raw activation IDs:             zero
HEAD/origin:                    equal at accepted SHA
tracked tree:                   clean
index:                          empty
services:                       API active unchanged; sidecar active restarted
~~~

## 2. Non-blocking stabilization note

`GET /v1/health` still reports the legacy configuration label
`calculation_version=ss-1.0.0`, while the actual activation/day payload proves
the current contract identity `ss-calc-1.2.0`.

This does not invalidate W3C because the real calculated payload and shared
contract are exact. It is an observability consistency item for the later
stabilization/release-hardening wave; do not change product code in this
docs-only commit.

## 3. Executor protocol

- Perform only exact docs stage, commit and push.
- Do not edit content.
- No subagents/delegation.
- Do not restart/reload any service.
- Do not switch branches or touch `main`.
- Do not begin B4/frontend/deploy.
- Never use broad/directory/wildcard staging.
- Stop after callback.

## 4. Exact staged paths

~~~text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/84_STAGE_B3_W3C_CONTROLLED_SIDECAR_RUNTIME_CONVERGENCE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/85_STAGE_B3_W3C_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

Exact total: **2 paths**.

Never stage or touch:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 5. Pre-stage and exact staging

Require:

~~~text
branch exact preview branch
HEAD = origin = 8db2505a55a71f910bda151d39e6f8ed3036e12f
tracked tree clean
index empty
documents 84/85 have no trailing whitespace
~~~

Stage both paths explicitly. Prove the cached path set equals exactly two and
`git diff --cached --check` passes.

## 6. Commit and push

Create one commit:

~~~text
docs(today): record real horizon runtime proof
~~~

Push normally to the current preview branch. No amend/rebase/force-push.

Then prove local/origin SHA equality, exact parent, exact two-path commit,
tracked-clean tree and empty index. Services remain active and unchanged by the
commit operation.

## 7. Exact callback

~~~text
PUSHED_STAGE_B3_W3C
parent_sha: 8db2505a55a71f910bda151d39e6f8ed3036e12f
commit_sha: <new SHA>
origin_sha: <same SHA>
commit_subject: docs(today): record real horizon runtime proof
staged_paths: 2 EXACT_ALLOWLIST
real_proof: PASS 2026-07-08 long,medium,fast
tracked_tree: CLEAN
index: EMPTY
unrelated_paths: UNTOUCHED
main: UNCHANGED
services: UNCHANGED BY COMMIT
next_wave: NOT_STARTED
~~~

Stop after callback.
