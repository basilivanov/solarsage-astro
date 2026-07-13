# Stage 2.W4 — final RC architect acceptance, docs-only commit and push

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`dc1af73a1094b09cc938304b739a11ce17cd8508`.

Evidence:

- `170_STAGE_2_W4_FINAL_RELEASE_CANDIDATE_TZ.md`;
- `173_STAGE_2_W4_R2_CLEAN_PUSHED_RUNTIME_CONTINUATION_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZE EXACT TWO-DOC COMMIT/PUSH ONLY**

Работай лично в `tmux astro:0.0`, без subagents/delegation/background coding.

## 1. Accepted final release candidate

The feature branch is accepted as ready for a separately audited merge to
`main`.

Independent architect evidence:

```text
feature HEAD/upstream/remote           dc1af73a1094b09cc938304b739a11ce17cd8508
main/origin/remote main                c9bc36bd9a947566eddb1ffcf5617967c7412676
topology                               origin/main ancestor; 59 / 0

contracts generate drift              0
contracts check                        110 PASS
contracts compatibility                16 additive / 0 breaking
fixture contract                       PASS
Python contracts                       44 PASS

Vitest                                 97 files / 1067 PASS
typecheck                              PASS
frontend/prod/contracts/secrets guards PASS
frontend GRACE                         47 paths clean
backend GRACE                          main 85 -> feature 61; new/add-line 0/0

API pytest                             1406 PASS / 4 SKIP
sidecar pytest                         201 PASS
preview security                       163 PASS
API/sidecar pip check                  PASS / PASS
API Ruff                               main 44 -> feature 31; new/add-line 0/0
API MyPy                               80 legacy / 11 paths; add-line 0
sidecar Ruff                           main 18 -> feature 8; new/add-line 0/0
production runtime fixture/mock import 0

isolated production build              PASS
candidate dist                         18184 KiB
candidate smoke 3010                   root/API/day 200
candidate cleanup                      3010 and .next-stage2-rc absent
rollback capacity                      22767956 KiB available at proof

real preview Chromium/mobile           2 PASS
real identity                          today.v2.1 / frontend 3 / content 10
real horizons                          long / medium / fast
fixture/interception/mock              zero
redacted E2E attachments               exact six
preview cleanup                        3003 and descendants absent

Telegram HMAC                          auth 200 / profile 200 / logout 204 / revoked 401
HMAC smoke /api/auth/dev               not used
global V2 flags                        UNSET unchanged
tracked config/contracts/env/BUILD_ID  exact starting hashes/modes
canonical services/PIDs                unchanged and healthy
temporary ports                        3003/3010/8001/18092 absent
```

No product/config/test/runtime edit is authorized here.

## 2. Pre-staging gate

Run `git fetch origin --prune` and require:

```text
branch                         preview/solarsage-v2-human-first-navigator-ux
HEAD/upstream/remote feature   dc1af73a1094b09cc938304b739a11ce17cd8508
main/origin/remote main        c9bc36bd9a947566eddb1ffcf5617967c7412676
tracked worktree/index         clean / empty
untracked                      frozen five + docs 173/174
3003/3010/8001/18092           absent
canonical services             unchanged and healthy
```

Require exact hash:

```text
33c8f356b7181932b1dc3909bc25403846fbdf961ac11c20a0afee0a3de51615  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/173_STAGE_2_W4_R2_CLEAN_PUSHED_RUNTIME_CONTINUATION_TZ.md
```

Document 174 is newly architect-created and has no pre-existing hash
requirement.

Stop on mismatch. No checkout, restore, reset, stash, amend, rebase or pull.

## 3. Exact staging

Stage exactly:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/173_STAGE_2_W4_R2_CLEAN_PUSHED_RUNTIME_CONTINUATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/174_STAGE_2_W4_FINAL_RC_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Use explicit `git add -- <path1> <path2>`. Never use `.`, `-A`, wildcard or
directory staging.

Require cached path set exact two, unstaged tracked diff empty,
`git diff --cached --check` pass and frozen paths unstaged.

## 4. Exact commit and post-commit proof

Commit with exact subject:

```text
docs(release): accept final v2 release candidate
```

Require parent exact `dc1af73a1094b09cc938304b739a11ce17cd8508`, subject
exact and commit path set exact two docs.

After commit run:

```bash
git diff --check origin/main...HEAD
git diff --quiet
git diff --cached --quiet
npx vitest run __tests__/scripts/preview-v2-real.test.ts
pnpm typecheck
pnpm guardrails:prod
```

All pass. No build, preview, HMAC, service or env operation.

If a gate fails, do not amend/reset/revert or push.

## 5. Normal feature push

Only after post-commit gates pass:

```bash
git push origin HEAD:preview/solarsage-v2-human-first-navigator-ux
```

No force or tags. Require local HEAD = tracking ref = remote feature.

Require `main`, `origin/main`, remote main remain exact
`c9bc36bd9a947566eddb1ffcf5617967c7412676` and feature topology becomes
`60 / 0` against main.

Final tracked worktree/index clean; only five frozen untracked paths remain.
Canonical services/PIDs unchanged; temporary ports absent.

## 6. Callback and stop

```text
PUSHED_STAGE_2_W4_FINAL_RC_ACCEPTED
parent: dc1af73a1094b09cc938304b739a11ce17cd8508
commit: <40-char SHA>
subject: docs(release): accept final v2 release candidate
commit_paths: EXACT_2_DOCS
launcher_unit: PASS
typecheck: PASS
prod_guard: PASS
local_tracking_remote_feature: EQUAL
main_origin_remote_main: c9bc36bd9a947566eddb1ffcf5617967c7412676_UNCHANGED
topology: FEATURE_60_MAIN_0
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
runtime_services: UNCHANGED_HEALTHY
ports: 3003_3010_8001_18092_ABSENT
main_merge: NOT_STARTED
production_deploy: NOT_STARTED
```

Then stop. Do not switch to or merge `main` until architect sends the dedicated
W5 main-integration TZ.
