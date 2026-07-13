# Stage 1.W3 — docs-only acceptance commit and push checkpoint

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted code/runtime base: `55d98917842bd94700030356da7fa1fc50abe86e`
Статус: **AUTHORIZED EXACT DOCS-ONLY COMMIT/PUSH**

## 1. Цель

Зафиксировать принятый W3 runtime runbook, errata и architect evidence одним
docs-only commit, затем push только текущей preview branch.

Никакой runtime mutation, product/test edit или S1.W4 в этой задаче нет.

## 2. Exact commit allowlist

Commit должен содержать ровно четыре paths:

```text
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/113_STAGE_1_W3_CONTROLLED_CANONICAL_API_CONVERGENCE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/114_STAGE_1_W3_ARCH_ERRATA_LEGACY_UNVERSIONED_PREFLIGHT_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/115_STAGE_1_W3_ARCH_RUNTIME_ACCEPTANCE_EVIDENCE.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/116_STAGE_1_W3_DOCS_ONLY_ACCEPTANCE_COMMIT_PUSH_TZ.md
```

Содержимое этих файлов не менять.

Exact commit subject:

```text
docs(preview): record controlled v2 API convergence
```

## 3. Absolute prohibitions

- no product/test/config edits;
- no staging frozen paths;
- no amend/squash/rebase/merge;
- no force push;
- no service restart/reload/stop;
- no env/unit/nginx edits;
- no 3003/8001/18092;
- no `pnpm preview:v2:real` or W4;
- no manual uvicorn/second API;
- no new runtime proof calls that compute data;
- no cleanup/delete of unrelated paths.

## 4. Preflight

```bash
git branch --show-current
git rev-parse HEAD
git rev-parse refs/remotes/origin/preview/solarsage-v2-human-first-navigator-ux
git ls-remote --heads origin refs/heads/preview/solarsage-v2-human-first-navigator-ux
git diff --quiet
git diff --cached --quiet
git status --short
```

Required:

```text
branch = preview/solarsage-v2-human-first-navigator-ux
HEAD = tracking = remote = 55d98917842bd94700030356da7fa1fc50abe86e
tracked diff = empty
index = empty
```

Exact untracked entries before staging:

```text
?? .grace/
?? artifacts/design/
?? docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/113_STAGE_1_W3_CONTROLLED_CANONICAL_API_CONVERGENCE_TZ.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/114_STAGE_1_W3_ARCH_ERRATA_LEGACY_UNVERSIONED_PREFLIGHT_TZ.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/115_STAGE_1_W3_ARCH_RUNTIME_ACCEPTANCE_EVIDENCE.md
?? docs/work/2026-07-11_today-v2-real-horizons-main-deploy/116_STAGE_1_W3_DOCS_ONLY_ACCEPTANCE_COMMIT_PUSH_TZ.md
?? grace.db
?? skills/
```

Any difference blocks commit.

## 5. Runtime witness before commit

Read-only only:

```bash
systemctl show solarsage-api.service solarsage-sidecar.service solarsage-frontend.service nginx.service \
  --property=Id,ActiveState,SubState,MainPID,ExecMainStartTimestamp --no-pager
ss -ltnp 'sport = :3002 or sport = :3003 or sport = :8000 or sport = :8001 or sport = :18091 or sport = :18092'
```

Required exact witnesses:

```text
API PID/start = 3887119 / Mon 2026-07-13 05:12:53 MSK
sidecar PID/start = 3582982 / Sun 2026-07-12 22:02:52 MSK
frontend PID/start = 916433 / Thu 2026-07-09 11:30:03 MSK
nginx PID/start = 1048 / Wed 2026-07-01 15:36:15 MSK
listeners 8000/18091/3002 present
listeners 3003/8001/18092 absent
```

If any witness changed, stop before staging.

## 6. Exact staging and validation

```bash
git add -- \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/113_STAGE_1_W3_CONTROLLED_CANONICAL_API_CONVERGENCE_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/114_STAGE_1_W3_ARCH_ERRATA_LEGACY_UNVERSIONED_PREFLIGHT_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/115_STAGE_1_W3_ARCH_RUNTIME_ACCEPTANCE_EVIDENCE.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/116_STAGE_1_W3_DOCS_ONLY_ACCEPTANCE_COMMIT_PUSH_TZ.md

git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
```

Assert exact 4 staged paths, all under the allowlist, no other staged path.

## 7. Commit, verify, push

```bash
git commit -m "docs(preview): record controlled v2 API convergence"
```

Immediately verify before push:

```bash
git rev-parse HEAD^
git show -s --format=%s HEAD
git diff-tree --no-commit-id --name-only -r HEAD
git show --check --oneline HEAD
git status --short --branch
```

Required:

```text
parent = 55d98917842bd94700030356da7fa1fc50abe86e
subject = docs(preview): record controlled v2 API convergence
commit paths = exact four docs 113–116
branch ahead exactly 1
tracked tree clean
only five frozen unrelated paths remain untracked
```

Then push only:

```bash
git push origin preview/solarsage-v2-human-first-navigator-ux
```

No force options.

## 8. Post-push proof

```bash
git rev-parse HEAD
git rev-parse refs/remotes/origin/preview/solarsage-v2-human-first-navigator-ux
git ls-remote --heads origin refs/heads/preview/solarsage-v2-human-first-navigator-ux
git diff --quiet
git diff --cached --quiet
git status --short
```

All three SHAs must equal the new commit SHA. Index/tracked tree clean; exact
five frozen untracked paths only.

Repeat runtime witness from section 5 and prove no PID/start/listener change.

## 9. Exact callback

```text
PUSHED_STAGE_1_W3_RUNTIME_EVIDENCE
base_sha: 55d98917842bd94700030356da7fa1fc50abe86e
commit_sha: <new full sha>
commit_subject: docs(preview): record controlled v2 API convergence
commit_paths: EXACT_4_DOCS_113_TO_116
forbidden_commit_paths: ZERO
push: PASS
local_origin_remote_equal: PASS_<new full sha>
tracked_worktree: CLEAN
index: EMPTY
unrelated_paths: EXACT_5_UNTOUCHED_UNTRACKED
api_pid_start: UNCHANGED_3887119_2026_07_13_05_12_53_MSK
sidecar_frontend_nginx: UNCHANGED
listeners_3003_8001_18092: ABSENT
service_restart_reload: NOT_PERFORMED
stage_1_w4: NOT_STARTED
```

После callback остановиться. S1.W4 и 3003 — отдельная architect wave.
