# Stage B3.W3B — architect acceptance, exact commit and push

Дата: 2026-07-12
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted parent HEAD/origin: `a067e971cffb22e7f4b6008ac9518b5414212976`
Implementation/review documents: `82`, `82A`, `82B`, `82C`, `82D`, `82E`
Статус: **ACCEPTED PROOF UTILITY — EXACT COMMIT/PUSH ONLY**

## 1. Acceptance meaning

W3B is accepted as a reproducible, privacy-safe, fail-closed real-route proof
utility.

The real three-horizon runtime proof is **not** falsely marked successful. The
accepted utility correctly rejects the currently loaded stale sidecar with:

~~~json
{"schemaVersion":"today-v2-real-api-proof.v1","status":"error","date":"2026-07-08","code":"activation_version_mismatch"}
~~~

This is the correct W3B outcome because:

- current repository/venv contract is `al-1.1`;
- loaded sidecar process predates the accepted shared contract;
- validation was not weakened;
- no date scan can repair a loaded-process identity mismatch;
- service convergence belongs to a separate architect-authored wave after this
  exact commit/push.

## 2. Independent architect evidence

~~~text
proof unit:                    16 passed
full API:                    1274 passed, 4 skipped, 0 failed
GRACE:                         2 files clean, 0 violations
contract Vitest:              21 passed
TypeScript:                    PASS
fixture normalization:        PASS
script size:                  318 / 320
test size:                    280 / 320
Make raw-value sentinel:       SAFE
malformed URL matrix:          closed invalid_base_url
request phase matrix:          5 real in-memory async cases PASS
main output matrix:            pass/unavailable/error/internal/write/health PASS
official proof artifact:       exact four-key redacted error
raw payload artifacts:         ZERO
raw activation IDs:            ZERO
git diff --check:              PASS
index:                         EMPTY
HEAD/origin:                   accepted parent, equal
services:                      API active unchanged; sidecar active unchanged
~~~

Source review confirmed:

- `TodayPayload.model_validate` is the first typed boundary;
- Pydantic `ValidationError` preserves exact six-field version codes without
  serializing raw input;
- sidecar health runs before auth/profile/day;
- ASGI app stdout/stderr is suppressed and restored at OS descriptor level;
- Secure cookie presence is checked without reading/copying its value;
- auth/profile/day failures have separate closed codes;
- unavailable selection is derived from the typed audit union, not exception
  text;
- success artifact emits structural `long,medium,fast` IDs and hashes raw
  activation identifiers;
- Make aliases are unexported, selected via raw `$(value ...)`, then passed as
  quoted environment data;
- canonical dev profile exactly matches document `82`;
- no product/API/frontend/generated/fixture/runtime file changed.

## 3. Executor protocol

- Perform only exact stage, commit and push.
- Do not edit file content.
- No subagents/delegation.
- Do not switch branches or touch `main`.
- Do not restart/reload services or modify systemd/env.
- Do not begin sidecar convergence, B4, frontend or deploy.
- Never use broad/directory/wildcard staging.
- Stop after callback.

## 4. Exact staged paths

~~~text
Makefile
scripts/prove_today_v2_real_api.py
apps/api/tests/test_real_today_v2_api_proof.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82_STAGE_B3_W3B_REAL_DEV_AUTH_API_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82A_STAGE_B3_W3B_ARCH_REVIEW_R1_PRIVACY_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82B_STAGE_B3_W3B_ARCH_REVIEW_R2_FAIL_CLOSED_RUNTIME_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82C_STAGE_B3_W3B_ARCH_REVIEW_R3_FINAL_PROOF_HARDENING_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82D_STAGE_B3_W3B_ARCH_REVIEW_R4_PROVEN_EDGE_FIXES_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/82E_STAGE_B3_W3B_ARCH_REVIEW_R5_BEHAVIOR_TEST_COMPLETION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/83_STAGE_B3_W3B_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

Exact total: **10 paths**.

Never stage or touch:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

No other tracked or untracked path is part of W3B.

## 5. Pre-stage proof

Before staging, prove:

~~~text
branch = preview/solarsage-v2-human-first-navigator-ux
HEAD = origin branch = a067e971cffb22e7f4b6008ac9518b5414212976
index empty
git diff --check PASS
script 318 lines
test 280 lines
~~~

Scan all seven untracked W3B documents (`82` through `83`) for trailing
whitespace without modifying them.

## 6. Exact staging

Stage each section 4 path explicitly with `git add -- <exact paths>`.

Then prove:

~~~bash
git diff --cached --name-status
git diff --cached --check
git status --short
~~~

The staged set must equal the ten paths exactly. Do not alter content to make
the set match.

## 7. Commit and push

Create one commit:

~~~text
test(today): add fail-closed real API proof
~~~

No amend, rebase or force-push.

Push normally:

~~~bash
git push origin preview/solarsage-v2-human-first-navigator-ux
~~~

Then prove:

- local HEAD equals origin branch;
- commit parent is exact accepted parent;
- commit contains exactly the ten paths;
- tracked tree and index are clean;
- frozen unrelated untracked paths remain untouched;
- `main` and services remain unchanged.

## 8. Exact callback

~~~text
PUSHED_STAGE_B3_W3B
parent_sha: a067e971cffb22e7f4b6008ac9518b5414212976
commit_sha: <new SHA>
origin_sha: <same SHA>
commit_subject: test(today): add fail-closed real API proof
staged_paths: 10 EXACT_ALLOWLIST
proof_unit_evidence: 16 passed
api_full_evidence: 1274 passed, 4 skipped, 0 failed
official_proof: BLOCKED activation_version_mismatch, correctly fail-closed
tracked_tree: CLEAN
index: EMPTY
unrelated_paths: UNTOUCHED
main: UNCHANGED
services: UNCHANGED
next_wave: NOT_STARTED
~~~

Stop after callback.
