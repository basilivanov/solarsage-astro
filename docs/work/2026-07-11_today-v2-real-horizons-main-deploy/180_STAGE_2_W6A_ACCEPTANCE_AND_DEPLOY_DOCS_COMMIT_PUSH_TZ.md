# Stage 2.W6A — architect acceptance and final deploy-doc commit

Дата: `2026-07-13`

Current main:
`24b453e95bd244e9628cd66a74caee24b9d70e8c`.

Evidence:
`177_STAGE_2_W6A_DEPLOY_PREFLIGHT_AND_WHEEL_PROOF_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZE EXACT FOUR-DOC COMMIT/PUSH ONLY**

Работай лично, без subagents/delegation/background coding.

## 1. Accepted W6A evidence

```text
main/origin/remote             24b453e95bd244e9628cd66a74caee24b9d70e8c
merge                          57230b7b8eedb772a936726f6abf97427bc37f6a
runtime units                  canonical confirmed
DB                             running / accepting 5433
sudo noninteractive            PASS
nginx test                     PASS with known unrelated warnings
same filesystem                PASS
available disk                 22550320 KiB at coder proof
env enable flags               UNSET / UNSET / dual default
env edit target                .env only
Settings override parse        True / True
current contracts              API+sidecar editable 0.1.0
wheel proof                    5983-byte valid py3-none-any wheel
wheel metadata/import/dry-run  PASS
temporary artifacts            removed
repo/env/build/services        unchanged
```

Architect independently repeated isolated Git-tree wheel build and confirmed
the same name, size, nine-entry content, `py.typed`, metadata and no tests.
Wheel byte SHA is not treated as reproducible across independent builds because
ZIP timestamps vary; W6B retained wheel hash is the sole deploy authority.

## 2. Purpose of this commit

Commit the accepted preflight, exact atomic deployment protocol, exact
production acceptance protocol and this authorization before any deploy
mutation. The resulting docs-only commit becomes `DEPLOY_SHA`.

After this push no Git commit/push is allowed during W6B/W7. This keeps:

```text
local main = origin/main = remote main = API health git SHA = deployed source
```

## 3. Pre-staging gate

Require:

```text
branch/HEAD/origin/remote main  main / 24b453e95bd244e9628cd66a74caee24b9d70e8c
tracked worktree/index          clean / empty
untracked                       frozen five + docs 177–180
runtime/env/build               unchanged
temporary ports                absent
```

Exact hashes:

```text
222954740fef4ec391a4bf7e443f543db0fd7267bf96f68f928c3a7e38d5f1df  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/177_STAGE_2_W6A_DEPLOY_PREFLIGHT_AND_WHEEL_PROOF_TZ.md
cf321701195d6494606e683292d183dc208f23bdfd26d909b32d68994b4fffe1  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/178_STAGE_2_W6B_ATOMIC_PRODUCTION_DEPLOY_TZ.md
95e99fba1daec549906fadd6a4c8b81f07e3ae0b49654e6f6341138ef964ae3b  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/179_STAGE_2_W7_PRODUCTION_ACCEPTANCE_TZ.md
```

Doc 180 is new. Stop on mismatch. No reset/restore/checkout/stash/amend/rebase/
pull.

## 4. Exact staging and commit

Stage exactly docs 177, 178, 179, 180 with explicit paths. Require cached set
exact four, unstaged tracked diff empty, cached diff check PASS and frozen paths
unstaged.

Commit exact subject:

```text
docs(release): authorize v2 production deployment
```

Require parent exact `24b453e...` and commit path set exact four docs.

## 5. Post-commit gates and normal push

Run:

```bash
git diff --check 57230b7b8eedb772a936726f6abf97427bc37f6a...HEAD
git diff --quiet
git diff --cached --quiet
npx vitest run __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
pnpm guardrails:prod
sudo -n nginx -t
```

All pass. Then:

```bash
git push origin main:main
```

No force/tags. Fetch and require local/origin/remote main equal new docs commit.
Require its parent `24b453e...`, exact subject/paths and zero non-doc diff.

Feature refs remain `b4a4daf...`. Runtime/env/build/services unchanged.

## 6. Callback and stop

```text
PUSHED_STAGE_2_W6_DEPLOY_AUTHORIZED_MAIN
parent: 24b453e95bd244e9628cd66a74caee24b9d70e8c
deploy_sha: <40-char docs commit>
subject: docs(release): authorize v2 production deployment
commit_paths: EXACT_DOCS_177_178_179_180
non_docs_diff: ZERO
launcher_unit: PASS
typecheck: PASS
prod_guard: PASS
nginx_test: PASS_WITH_KNOWN_UNRELATED_WARNINGS
local_origin_remote_main: EQUAL
feature_refs: b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28_UNCHANGED
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
runtime_env_build_services: UNCHANGED
production_deploy: AUTHORIZED_NOT_STARTED
```

Then stop. Architect verifies the final SHA and explicitly sends W6B with that
exact callback SHA.
