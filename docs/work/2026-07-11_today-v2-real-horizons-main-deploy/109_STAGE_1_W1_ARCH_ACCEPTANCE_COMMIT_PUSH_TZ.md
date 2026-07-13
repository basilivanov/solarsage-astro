# Stage 1.W1 — архитектурная приёмка, commit и push

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base HEAD/origin: `828c20df1e9de5282cd410720649d7efac414754`
Родительские документы: `107`, `108`
Статус: **ACCEPTED FOR EXACT COMMIT AND PUSH**

## 0. Роль и единственная задача

Ты кодер. Функциональная реализация Stage 1.W1 и R1 принята архитектором.

Сделай только:

1. preflight exact scope;
2. stage exact 7 accepted paths;
3. staged verification;
4. один commit с exact subject;
5. push текущей preview-ветки;
6. callback и остановка.

Не менять содержимое файлов. Не запускать W2. Не перезапускать сервисы.

## 1. Принятые доказательства

Архитектор независимо подтвердил:

~~~text
selection/cache/runtime architecture: ACCEPTED
exact-4 GRACE: PASS — 4 file(s) clean
ruff exact 4: PASS
mypy production 3 with --follow-imports=skip: PASS
py_compile exact 4: PASS
new focused module: 51 passed
focused W1 aggregate: 123 passed
full API: 1325 passed, 4 skipped, 0 failed
test function contracts: 41 unique
test file length: 998 <= 1000
git diff --check: PASS
index: EMPTY
HEAD = origin: 828c20df...
services/ports: UNCHANGED
~~~

## 2. Exact commit allowlist

Ровно семь путей:

~~~text
apps/api/app/services/today_selection_context.py
apps/api/app/services/day_scoring_runtime_service.py
apps/api/app/services/cache_key_service.py
apps/api/tests/test_today_selection_context.py
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/107_STAGE_1_W1_PURE_SELECTION_CACHE_FOUNDATION_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/108_STAGE_1_W1_ARCH_REVIEW_R1_EXACT_4_GRACE_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/109_STAGE_1_W1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

Commit должен содержать:

~~~text
implementation paths: EXACT_4
architect docs: EXACT_3_107_TO_109
total paths: EXACT_7
~~~

## 3. Frozen/unrelated paths

Не stage, не менять и не удалять:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

Никакие иные untracked/tracked paths не входят в commit.

## 4. Preflight

До `git add` проверить:

~~~bash
git branch --show-current
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
git status --short
git diff --check
git diff --cached --quiet
~~~

Ожидается:

~~~text
branch = preview/solarsage-v2-human-first-navigator-ux
HEAD = origin = 828c20df1e9de5282cd410720649d7efac414754
tracked implementation diff = exact 2 modify
untracked implementation = exact 2 new
untracked accepted docs = exact 3, 107 through 109
index empty
frozen paths untouched
~~~

Если scope отличается — остановиться без commit.

## 5. Stage exact paths

Использовать explicit path staging. Не использовать `git add .`, `git add -A`
или wildcard staging.

~~~bash
git add -- \
  apps/api/app/services/today_selection_context.py \
  apps/api/app/services/day_scoring_runtime_service.py \
  apps/api/app/services/cache_key_service.py \
  apps/api/tests/test_today_selection_context.py \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/107_STAGE_1_W1_PURE_SELECTION_CACHE_FOUNDATION_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/108_STAGE_1_W1_ARCH_REVIEW_R1_EXACT_4_GRACE_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/109_STAGE_1_W1_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

## 6. Mandatory staged verification

### 6.1 Exact list and counts

~~~bash
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
~~~

Доказать exact equality со списком из раздела 2, а также:

~~~text
TOTAL = 7
IMPLEMENTATION = 4
ARCH_DOCS = 3
FORBIDDEN = 0
~~~

Проверить отсутствие в staged:

~~~text
.grace/**
artifacts/design/**
docs/superpowers/**
grace.db
skills/**
apps/api/app/api/**
apps/api/app/services/today_service.py
apps/api/app/services/calendar_service.py
apps/api/app/core/**
apps/api/app/schemas/**
apps/api/app/db/**
apps/solarsage/**
app/**
components/**
hooks/**
lib/**
packages/contracts/**
next-env.d.ts
pnpm-lock.yaml
~~~

### 6.2 Content checks before commit

~~~bash
apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/services/today_selection_context.py \
  apps/api/app/services/day_scoring_runtime_service.py \
  apps/api/app/services/cache_key_service.py \
  apps/api/tests/test_today_selection_context.py

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_selection_context.py \
  apps/api/tests/test_scoring_v2_runtime_flags.py \
  apps/api/tests/test_today_service_v2_dual_run.py \
  apps/api/tests/test_calendar_v2_dual_run.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_today_meta_versions.py \
  -q
~~~

Ожидается:

~~~text
GRACE exact 4: PASS
focused W1: 123 passed
~~~

Не требуется повторно запускать full API: он уже принят на этом exact worktree.

## 7. Commit

Exact subject:

~~~text
feat(api): add request-scoped v2 selection foundation
~~~

Команда:

~~~bash
git commit -m "feat(api): add request-scoped v2 selection foundation"
~~~

После commit проверить:

~~~bash
git show --check --oneline HEAD
git diff-tree --no-commit-id --name-only -r HEAD
git status --short --branch
~~~

Commit обязан иметь parent:

~~~text
828c20df1e9de5282cd410720649d7efac414754
~~~

## 8. Push

~~~bash
git push origin preview/solarsage-v2-human-first-navigator-ux
~~~

После push доказать:

~~~bash
git rev-parse HEAD
git rev-parse refs/remotes/origin/preview/solarsage-v2-human-first-navigator-ux
git ls-remote --heads origin refs/heads/preview/solarsage-v2-human-first-navigator-ux
~~~

Все три SHA должны совпасть.

## 9. Final state

~~~bash
git diff --quiet
git diff --cached --quiet
git status --short
ss -ltnp 'sport = :3003 or sport = :18092 or sport = :8000 or sport = :18091 or sport = :3002'
systemctl is-active solarsage-api.service solarsage-sidecar.service solarsage-frontend.service
~~~

Ожидается:

- tracked worktree clean;
- index empty;
- остаются только пять frozen/unrelated untracked paths;
- 3003/18092 absent;
- 8000/18091/3002 active;
- service start timestamps/env/main unchanged;
- W2 not started.

## 10. Callback

~~~text
PUSHED_STAGE_1_W1
base_sha: 828c20df1e9de5282cd410720649d7efac414754
commit_sha: <sha>
commit_subject: feat(api): add request-scoped v2 selection foundation
commit_paths: EXACT_7
implementation_paths: EXACT_4
architect_docs: EXACT_3_107_TO_109
staged_diff_check: PASS
exact_4_grace: PASS
focused_foundation: 123 PASS
forbidden_commit_paths: ZERO
push: PASS
local_origin_equal: PASS_<sha>
index: EMPTY
tracked_worktree: CLEAN
ports_3003_18092: ABSENT
services_env_main: UNCHANGED
unrelated_paths: UNTOUCHED_UNTRACKED
next_wave: NOT_STARTED
~~~

После callback остановиться.
