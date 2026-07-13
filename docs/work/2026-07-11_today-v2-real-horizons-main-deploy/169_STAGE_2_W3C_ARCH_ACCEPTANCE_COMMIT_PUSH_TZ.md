# Stage 2.W3C — architect acceptance, proof commit and push

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`0717bdd4123cee145a30d2c6120f22d155522246`

Implementation proof:
`168_STAGE_2_W3C_SIDECAR_CHANGED_PATH_STATIC_PROOF_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZE EXACT TWO-DOC COMMIT/PUSH ONLY**

No subagents, delegation or background coding/review agents.

## 1. Accepted evidence

W3C is accepted as a proof-only wave. No sidecar code correction is required
or authorized.

Independent architect verification:

```text
sidecar changed paths                         18
sidecar changed Python paths                  16
current paths existing in origin/main         14
new clean Python paths                         2
Ruff binary                                   API venv 0.15.14
origin/main diagnostics on 14 existing paths 18
current diagnostics on 16 paths                8
removed baseline diagnostics                  10
new normalized signatures                      0
diagnostics on feature-added/replaced lines     0
sidecar tests                                 201 PASS
sidecar warning                               known Starlette deprecation only
sidecar pip check                             PASS
sidecar-venv tool install                     not performed
tracked worktree                              clean
index                                         empty
runtime/services/ports                        unchanged/absent
```

The initial architect inventory accidentally passed the two feature-added
paths to Ruff as nonexistent `origin/main` files, producing two synthetic
`E902` entries. Doc 168 has been corrected before commit. The valid comparison
is `18 → 8`, with ten baseline diagnostics removed and zero new signatures.

## 2. Pre-staging gate

Require:

```text
HEAD = upstream feature = remote feature
  0717bdd4123cee145a30d2c6120f22d155522246

main = origin/main = remote main
  c9bc36bd9a947566eddb1ffcf5617967c7412676

tracked worktree clean
index empty
```

Require exact hash:

```text
bfef9c933885c8ccdbb630f88e3013026ee75999eb79827c0fda14b93bd5c786  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/168_STAGE_2_W3C_SIDECAR_CHANGED_PATH_STATIC_PROOF_TZ.md
```

Doc 169 is newly architect-created and has no pre-existing hash requirement.

Stop on mismatch. No reset, restore, checkout, stash, amend or rebase.

## 3. Exact staging

Stage exactly:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/168_STAGE_2_W3C_SIDECAR_CHANGED_PATH_STATIC_PROOF_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/169_STAGE_2_W3C_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Use explicit `git add -- <two paths>`. Do not use directory/wildcard/all adds.

Frozen untracked paths remain unstaged:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Require cached path set exact two, unstaged tracked diff empty and
`git diff --cached --check` PASS.

## 4. Exact commit and push

Commit with exact subject:

```text
docs(release): prove sidecar static baseline
```

Require parent exact `0717bdd4123cee145a30d2c6120f22d155522246` and
commit path set exact two.

Push only:

```bash
git push origin HEAD:preview/solarsage-v2-human-first-navigator-ux
```

No force, tags, main push or runtime action.

After push require local/tracking/remote feature equality and unchanged
`main/origin/main/remote main = c9bc36bd9a947566eddb1ffcf5617967c7412676`.

Do not start final RC in this task.

## 5. Required callback and stop

```text
PUSHED_STAGE_2_W3C_ACCEPTED
parent: 0717bdd4123cee145a30d2c6120f22d155522246
commit: <40-char SHA>
subject: docs(release): prove sidecar static baseline
commit_paths: EXACT_2_DOCS
sidecar_source_changes: ZERO
local_tracking_remote_feature: EQUAL
main_origin_remote_main: c9bc36bd9a947566eddb1ffcf5617967c7412676_UNCHANGED
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
runtime_services: UNCHANGED
ports: 3003/8001/18092_ABSENT
final_rc: NOT_STARTED
main_deploy: NOT_STARTED
```

Then stop.
