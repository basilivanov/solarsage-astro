# Stage 2.W4.R1 — architect acceptance, exact commit and push

Дата: `2026-07-13`

Branch/base: `preview/solarsage-v2-human-first-navigator-ux` /
`42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93`.

Implementation:
`171_STAGE_2_W4_R1_TODAY_REDIRECT_GRACE_ANCHOR_TZ.md`.

Статус: **ARCHITECT ACCEPTED — AUTHORIZE EXACT FOUR-PATH COMMIT/PUSH ONLY**

Работай лично, без subagents/delegation/background coding.

## 1. Accepted result

The W4 Vitest blocker is repaired with one truthful comment-only declaration:

```text
app/(grace)/today/page.tsx
  + // GRACE_ANCHORS: [COMPATIBILITY_REDIRECT]
```

Independent architect review confirmed:

```text
tracked diff paths          1
diff                        exact one added comment line
runtime after comment strip byte-equivalent
focused Vitest              2 files / 5 PASS
full Vitest                 97 files / 1067 PASS
typecheck                   PASS
frontend guard              PASS / 47 GRACE paths clean
GRACE self-tests            11 PASS
GRACE exact path            PASS
GRACE negative              6 PASS / 0 FAIL
production guard            PASS
secrets guard               PASS
index                       empty
runtime services/ports      unchanged / temporary ports absent
```

No further source/config/test edit is authorized in this wave.

## 2. Pre-staging gate

Run `git fetch origin --prune` and require:

```text
branch                         preview/solarsage-v2-human-first-navigator-ux
HEAD/upstream/remote feature   42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93
main/origin/remote main        c9bc36bd9a947566eddb1ffcf5617967c7412676
tracked diff                   exact app/(grace)/today/page.tsx
index                          empty
3003/3010/8001/18092           absent
canonical services             unchanged
```

Require exact hashes before staging:

```text
2eedaab26a63e8dfb031ef5a6c5d6f8ac864aa7f99727df6ce2862cdbebf85cc  app/(grace)/today/page.tsx
a749072156c63d916f2197083ffb37b1445b60a59cd84127f6383860588a6899  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/170_STAGE_2_W4_FINAL_RELEASE_CANDIDATE_TZ.md
5cecd82ee467b3245f2912e3a50ebce86908add99c68ac5df87f847b46aeb041  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/171_STAGE_2_W4_R1_TODAY_REDIRECT_GRACE_ANCHOR_TZ.md
```

Document 172 is newly architect-created and has no pre-existing hash
requirement.

Stop on any mismatch. Do not repair, reset, restore, checkout, stash, amend,
rebase or pull.

## 3. Exact staging

Stage exactly these four paths using explicit arguments:

```text
app/(grace)/today/page.tsx
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/170_STAGE_2_W4_FINAL_RELEASE_CANDIDATE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/171_STAGE_2_W4_R1_TODAY_REDIRECT_GRACE_ANCHOR_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/172_STAGE_2_W4_R1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Never use `git add .`, `-A`, directory or wildcard staging.

Require before commit:

```text
cached path set           exact four above
unstaged tracked diff     empty
cached diff check         PASS
source cached diff        exact one added comment line
frozen paths              unstaged and preserved
```

The five frozen unrelated paths remain untracked and unstaged:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

## 4. Exact commit

Commit with exact subject:

```text
fix(grace): restore today redirect anchor
```

Require:

```text
parent        42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93
subject       exact text above
commit paths  exact four
source diff   exact one comment line
```

No amend, signing-policy change, tag or second commit.

## 5. Post-commit gates before push

From the new clean commit run:

```bash
npx vitest run \
  __tests__/grace-discipline.test.ts \
  __tests__/app/today-redirect.test.ts

npx vitest run
pnpm typecheck
pnpm guardrails:frontend
pnpm guardrails:prod
pnpm guardrails:secrets
git diff --check origin/main...HEAD
git diff --quiet
git diff --cached --quiet
```

Require exact focused `5 PASS`, full `97 files / 1067 PASS`, all guards green,
tracked worktree clean and index empty. Do not start build, preview or HMAC.

If a post-commit gate fails, do not amend/revert/reset or push. Return blocked
callback with safe evidence.

## 6. Normal push and ref proof

Only after all gates pass:

```bash
git push origin HEAD:preview/solarsage-v2-human-first-navigator-ux
```

No force. Then require equality of:

```text
local HEAD
tracking feature ref
git ls-remote feature SHA
```

Require `main`, `origin/main` and remote main remain exactly:

```text
c9bc36bd9a947566eddb1ffcf5617967c7412676
```

Final tracked worktree/index clean; only five frozen untracked paths remain.
Ports `3003/3010/8001/18092` remain absent and canonical services unchanged.

## 7. Callback and stop

```text
PUSHED_STAGE_2_W4_R1_ACCEPTED
parent: 42a0c5dba7d476b156e0ff17d4fdccb5a22aaa93
commit: <40-char SHA>
subject: fix(grace): restore today redirect anchor
commit_paths: EXACT_4
source_change: EXACT_1_COMMENT_LINE
focused_vitest: 2_FILES_5_PASS
full_vitest: 97_FILES_1067_PASS
typecheck: PASS
frontend_guard: PASS
prod_guard: PASS
secrets_guard: PASS
local_tracking_remote_feature: EQUAL
main_origin_remote_main: c9bc36bd9a947566eddb1ffcf5617967c7412676_UNCHANGED
tracked_worktree: CLEAN
index: EMPTY
frozen_untracked: PRESERVED
runtime_services: UNCHANGED
ports: 3003_3010_8001_18092_ABSENT
final_rc_resume: NOT_STARTED
main_deploy: NOT_STARTED
```

Then stop. Do not resume document 170 until architect sends a dedicated
continuation TZ based on the pushed SHA.
