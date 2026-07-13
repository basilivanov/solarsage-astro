# Stage B3.W3A — architect acceptance, exact commit and push

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted parent HEAD/origin: `9e1c6c0af9103e73e56d65644642d5c075fba3a3`
Implementation/review documents: `81`, `81A`
Статус: **ACCEPTED — EXACT COMMIT/PUSH ONLY**

## 1. Acceptance evidence

The architect independently confirmed:

~~~text
former failures:                6/6 PASS
targeted:                       36 passed
focused backend:               142 passed
full API:                      1258 passed, 4 skipped, 0 failed
horizon regression:             242 passed
GRACE:                            3/3 PASS
contract Vitest:                 21 passed
TypeScript:                       PASS
generated contract hashes:       exact unchanged
canonical fixture hash:          exact unchanged
git diff --check:                PASS
index:                           EMPTY
HEAD/origin:                     accepted parent, equal
~~~

Source review confirmed one immutable canonical runtime identity resolver now
drives:

- expected cache reads;
- Today write cache identity;
- Calendar semantic-cache write identity;
- Today public meta calculation/scoring/payload/frontend/content fields.

V1/V2 selection is based only on selected scoring. Frontend and dual-run flags
cannot independently select the family. The full API baseline is now green and
the six frozen failures are closed permanently.

## 2. Executor protocol

- Perform only exact stage, commit and push.
- Do not edit file content.
- No subagents/delegation.
- Do not switch branches or touch `main`.
- Do not start W3B/B4/deploy.
- Do not touch services, env, ports, database or builds.
- Never use broad/directory/wildcard staging.
- Stop after callback.

## 3. Exact staged paths

~~~text
apps/api/app/services/cache_key_service.py
apps/api/app/services/calendar_service.py
apps/api/app/services/today_service.py
apps/api/tests/test_semantic_v2_service.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_today_v2_payload.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/81_STAGE_B3_W3A_FULL_GREEN_IDENTITY_STABILIZATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/81A_STAGE_B3_W3A_ARCH_REVIEW_R1_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/81B_STAGE_B3_W3A_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

Exact total: **9 paths**.

Never stage or touch:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

## 4. Pre-stage and exact staging

Prove exact branch, parent/origin equality, empty index, diff check and the
nine-path allowlist. Explicitly scan untracked documents for trailing
whitespace.

Stage each section 3 path explicitly with `git add -- <exact paths>`.

Then prove:

~~~bash
git diff --cached --name-status
git diff --cached --check
git status --short
~~~

The staged set must equal the nine paths exactly. Do not alter content to make
the set match.

## 5. Commit and push

Create one commit:

~~~text
fix(today): unify runtime identity and green backend
~~~

No amend/rebase/force-push.

Push normally:

~~~bash
git push origin preview/solarsage-v2-human-first-navigator-ux
~~~

Then prove local/origin SHA equality, exact parent, exact commit path set,
tracked-clean tree and empty index.

## 6. Exact callback

~~~text
PUSHED_STAGE_B3_W3A
parent_sha: 9e1c6c0af9103e73e56d65644642d5c075fba3a3
commit_sha: <new SHA>
origin_sha: <same SHA>
commit_subject: fix(today): unify runtime identity and green backend
staged_paths: 9 EXACT_ALLOWLIST
api_full_evidence: 1258 passed, 4 skipped, 0 failed
tracked_tree: CLEAN
index: EMPTY
unrelated_paths: UNTOUCHED
main: UNCHANGED
services: UNCHANGED
next_wave: NOT_STARTED
~~~

Stop after callback.
