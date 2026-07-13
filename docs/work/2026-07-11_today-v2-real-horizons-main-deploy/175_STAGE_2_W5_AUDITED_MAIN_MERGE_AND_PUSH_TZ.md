# Stage 2.W5 — audited main merge, full post-merge gates and normal push

Дата: `2026-07-13`

Accepted feature:

```text
preview/solarsage-v2-human-first-navigator-ux
b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28
```

Accepted main base:

```text
main / origin/main / remote main
c9bc36bd9a947566eddb1ffcf5617967c7412676
```

Parent master:
`127_STAGE_2_CORRECTIVE_RELEASE_MAIN_DEPLOY_WAVE_MASTER.md`.

RC acceptance:
`174_STAGE_2_W4_FINAL_RC_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md`.

Статус: **AUTHORIZED MAIN INTEGRATION ONLY — NO DEPLOY / NO RUNTIME MUTATION**

Работай лично в `tmux astro:0.0`, без subagents/delegation/background coding.

## 1. Goal and exact result

Integrate the accepted frontend, API, sidecar and contracts into `main` through
one audited non-fast-forward merge commit, run the full post-merge release
matrix before publishing it, then normally push `main`.

Required merge subject:

```text
merge: release SolarSage V2 human-first horizons
```

Required merge topology:

```text
parent 1  c9bc36bd9a947566eddb1ffcf5617967c7412676
parent 2  b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28
tree      byte-equivalent to accepted feature tree b4a4dafc...
```

This wave does not change product code, config, env, build, DB or services. It
only switches branches, creates the exact merge commit, runs gates and pushes
`main` after success.

Document 175 remains architect-owned/untracked during this wave. A separate
post-merge acceptance docs commit will follow after architect review.

## 2. Absolute restrictions

- no source/test/config/docs edit by coder;
- do not edit document 175;
- no rebase, squash, cherry-pick, amend, reset, restore, checkout paths, stash;
- no `git pull`;
- no force push, tags or feature-branch rewrite;
- no conflict resolution by guessing;
- no dependency install or venv mutation;
- no build/swap, env flags, systemd/nginx/Docker/DB mutation;
- no service restart/reload/stop;
- no preview 3003, candidate 3010, API 8001 or mock 18092;
- no manual uvicorn;
- no frozen-path cleanup.

If the merge unexpectedly conflicts, run only `git merge --abort`, prove main
returned to exact `c9bc36b...`, and return blocked. Do not resolve a conflict in
this wave.

Frozen paths remain untouched and unstaged:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 3. Preflight on feature branch

Run:

```bash
git fetch origin --prune
git branch --show-current
git rev-parse HEAD
git rev-parse '@{upstream}'
git rev-parse preview/solarsage-v2-human-first-navigator-ux
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git rev-parse main
git rev-parse origin/main
git ls-remote --heads origin \
  refs/heads/main \
  refs/heads/preview/solarsage-v2-human-first-navigator-ux
git merge-base main preview/solarsage-v2-human-first-navigator-ux
git merge-base --is-ancestor origin/main preview/solarsage-v2-human-first-navigator-ux
git rev-list --count origin/main..preview/solarsage-v2-human-first-navigator-ux
git rev-list --count preview/solarsage-v2-human-first-navigator-ux..origin/main
git diff --check origin/main...preview/solarsage-v2-human-first-navigator-ux
git diff --quiet
git diff --cached --quiet
git status --short --branch
```

Require exactly:

```text
current branch                   preview/solarsage-v2-human-first-navigator-ux
feature local/tracking/remote    b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28
main local/tracking/remote       c9bc36bd9a947566eddb1ffcf5617967c7412676
merge base                      c9bc36bd9a947566eddb1ffcf5617967c7412676
origin/main ancestor             yes
feature-only/main-only           60 / 0
tracked worktree/index           clean / empty
untracked                        frozen five + doc 175
```

Stop on any mismatch. In particular, if remote main advanced, do not merge.

## 4. Immutable runtime/config snapshot

Before branch switch record:

```bash
systemctl show \
  solarsage-sidecar.service \
  solarsage-api.service \
  solarsage-frontend.service \
  nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp --no-pager

ss -ltnp 'sport = :3002 or sport = :3003 or sport = :3010 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'

sha256sum \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID .env .env.production \
  > /tmp/stage2-w5-start.sha256

stat -c '%n %s %a %U:%G' \
  next-env.d.ts tsconfig.json package.json pnpm-lock.yaml \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts \
  .next-prod/BUILD_ID .env .env.production \
  > /tmp/stage2-w5-start.stat
```

Require canonical witnesses unchanged from RC:

```text
sidecar   3582982 / Sun 2026-07-12 22:02:52 MSK
API       3940721 / Mon 2026-07-13 06:54:31 MSK
frontend  916433  / Thu 2026-07-09 11:30:03 MSK
nginx     1048    / Wed 2026-07-01 15:36:15 MSK
3002/8000/18091 present
3003/3010/8001/18092 absent
```

Do not print env values.

## 5. Switch and exact merge

Switch only by branch name:

```bash
git switch main
```

Require current branch `main`, HEAD `c9bc36b...`, tracked clean/index empty and
the same allowed untracked paths.

Synchronize without creating a commit:

```bash
git merge --ff-only origin/main
```

Require still exact `c9bc36b...`. Then create one merge commit:

```bash
git merge --no-ff \
  preview/solarsage-v2-human-first-navigator-ux \
  -m 'merge: release SolarSage V2 human-first horizons'
```

No `--squash`, strategy override or manual file edit.

Immediately require:

```bash
merge_sha=$(git rev-parse HEAD)
test "$(git rev-list --parents -n 1 HEAD | awk '{print NF}')" -eq 3
test "$(git rev-parse HEAD^1)" = 'c9bc36bd9a947566eddb1ffcf5617967c7412676'
test "$(git rev-parse HEAD^2)" = 'b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28'
test "$(git log -1 --format=%s)" = 'merge: release SolarSage V2 human-first horizons'
git diff --exit-code b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28 HEAD
git diff --check c9bc36bd9a947566eddb1ffcf5617967c7412676...HEAD
git diff --quiet
git diff --cached --quiet
```

The feature-to-merge tree diff must be zero. Document 175 remains untracked.

## 6. Full post-merge contract matrix before push

Run in exact order:

```bash
pnpm contracts:generate
git diff --exit-code -- \
  packages/contracts/openapi.json \
  packages/contracts/_generated.ts \
  packages/contracts/_generated.zod.ts
pnpm contracts:check
pnpm contracts:compat
pnpm contracts:fixture:check
PYTHONPATH=packages/py-contracts \
  apps/api/.venv/bin/python -m pytest packages/py-contracts/tests/ -q
```

Require generation drift zero, `110 PASS`, `16 additive / 0 breaking`, fixture
PASS and `44 PASS`.

## 7. Full post-merge frontend matrix before push

Run:

```bash
npx vitest run
pnpm typecheck
pnpm guardrails:prod
pnpm guardrails:contracts
pnpm guardrails:frontend
pnpm guardrails:secrets
```

Require exact `97 files / 1067 PASS` and all guards exit zero.

## 8. Full post-merge backend/sidecar matrix before push

Run:

```bash
PYTHONPATH=apps/api \
  apps/api/.venv/bin/python -m pytest apps/api/tests/ -q

PYTHONPATH=apps/solarsage \
  apps/solarsage/venv/bin/python -m pytest apps/solarsage/tests/ -q

PYTHONPATH=apps/api apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_today_preview_access.py \
  apps/api/tests/test_today_selection_context.py \
  apps/api/tests/test_today_cache_v2_key.py \
  -q

apps/api/.venv/bin/python -m pip check
apps/solarsage/venv/bin/python -m pip check
```

Require:

```text
API                 1406 PASS / 4 SKIP
sidecar             201 PASS
preview security    163 PASS
pip check           PASS / PASS
warnings            known Starlette deprecation only; no lifecycle warnings
```

Do not install anything.

## 9. Pre-push merge audit

After all gates require:

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse HEAD^1
git rev-parse HEAD^2
git log -1 --format=%s
git diff --exit-code b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28 HEAD
git diff --check c9bc36bd9a947566eddb1ffcf5617967c7412676...HEAD
git diff --quiet
git diff --cached --quiet
git status --short --branch
git ls-remote --heads origin refs/heads/main
```

Require current branch main; remote main still exact `c9bc36b...`; merge
parents/message/tree exact; tracked clean/index empty; only frozen five + doc
175 untracked.

If remote main changed during tests, do not push or rewrite history. Return
blocked with merge SHA preserved locally.

## 10. Normal main push

Only after section 9 passes:

```bash
git push origin main:main
```

No force. Then `git fetch origin --prune` and require:

```text
local main = origin/main = remote main = merge_sha
feature local/tracking/remote = b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28
merge parent1 = c9bc36b...
merge parent2 = b4a4daf...
merge tree = feature tree
```

## 11. Final immutable runtime/config audit

Recreate `/tmp/stage2-w5-final.sha256` and `.stat` using the exact section 4
path lists. Their diffs against starting snapshots must be empty.

Require service PID/start and listeners unchanged; canonical health 200;
3003/3010/8001/18092 absent; no build or env mutation.

Final state:

```text
current branch               main
tracked worktree/index       clean / empty
untracked                    frozen five + doc 175
main local/tracking/remote   exact merge SHA
feature refs                 b4a4daf... unchanged
production deploy            not started
```

## 12. Callback and stop

```text
PUSHED_STAGE_2_W5_MAIN_MERGE
merge: <40-char SHA>
subject: merge: release SolarSage V2 human-first horizons
parent1: c9bc36bd9a947566eddb1ffcf5617967c7412676
parent2: b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28
merge_tree_equals_feature: YES
contracts: GENERATE_DIFF_0_CHECK_110_COMPAT_16_0_FIXTURE_PASS_PYCONTRACTS_44
frontend: VITEST_97_1067_TYPECHECK_AND_GUARDS_PASS
backend: API_1406_4_SIDECAR_201_PREVIEW_SECURITY_163_PIP_PASS
local_origin_remote_main: EQUAL
feature_refs: b4a4dafc1ad18caeda6eccd9baaa8c8e2700aa28_UNCHANGED
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
runtime_services: UNCHANGED_HEALTHY
ports: 3003_3010_8001_18092_ABSENT
production_deploy: NOT_STARTED
```

Then stop for architect review. Do not start W6 deployment.
