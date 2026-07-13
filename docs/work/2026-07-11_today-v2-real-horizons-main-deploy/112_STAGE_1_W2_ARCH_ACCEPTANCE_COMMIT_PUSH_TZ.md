# Stage 1.W2 — архитектурная приёмка, commit и push

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Accepted base HEAD/origin: `933e749137d00c262c8f2cedec7b945582bf40d1`
Родительские документы: `110`, `111`
Статус: **ACCEPTED FOR EXACT COMMIT AND PUSH**

## 0. Роль и задача

Ты кодер. W2 и security R1 приняты архитектором.

Сделай только:

1. exact preflight;
2. stage exact 9 accepted paths;
3. staged verification;
4. один commit с exact subject;
5. push preview branch;
6. final proof/callback;
7. остановка.

Содержимое файлов не менять. W3 не начинать. Сервисы не перезапускать. 3003 и
18092 не запускать.

## 1. Принятые доказательства

~~~text
W2 architecture/security: ACCEPTED
public raw Host + local forwarded metadata: DENIED_HOST
malformed raw Host + local forwarded metadata: DENIED_HOST
direct loopback:3003: PASS
Next rewrite loopback:8000 -> forwarded loopback:3003: PASS
production absolute deny: PASS
query/cookie/Referer: NOT_SELECTORS
route concurrent contexts: PASS
service cache/sidecar/runtime propagation: PASS
split-brain guard: PASS
settings mutation: ZERO
backend exact GRACE: PASS_4_OF_4
backend W2 module: 59 passed
backend focused: 180 passed
backend full: 1384 passed, 4 skipped, 0 failed
frontend focused: 20 passed
frontend full: 1063 passed
typecheck: PASS
contracts check: PASS, 110 focused contract tests
production guard: PASS
test file length: 997 <= 1000
git diff check: PASS
index: EMPTY
HEAD = origin = 933e749...
services/ports/env: UNCHANGED
~~~

## 2. Exact commit allowlist

Ровно девять путей:

~~~text
apps/api/app/services/today_preview_guard.py
apps/api/app/api/day.py
apps/api/app/services/today_service.py
apps/api/tests/test_today_preview_transport.py
lib/grace/api/client.ts
__tests__/api/grace-client.test.ts
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/110_STAGE_1_W2_GUARDED_TRANSPORT_ROUTE_SERVICE_FRONTEND_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/111_STAGE_1_W2_ARCH_REVIEW_R1_RAW_HOST_CHAIN_TZ.md
docs/work/2026-07-11_today-v2-real-horizons-main-deploy/112_STAGE_1_W2_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

Counts:

~~~text
implementation paths: EXACT_6
architect docs: EXACT_3_110_TO_112
total: EXACT_9
~~~

## 3. Frozen/forbidden paths

Не stage, не менять, не удалять:

~~~text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
~~~

В commit также запрещены любые иные paths, особенно:

~~~text
apps/api/app/api/auth.py
apps/api/app/core/**
apps/api/app/db/**
apps/api/app/schemas/**
apps/api/app/services/day_scoring_runtime_service.py
apps/api/app/services/cache_key_service.py
apps/api/app/services/today_selection_context.py
apps/api/app/services/calendar_service.py
apps/solarsage/**
packages/contracts/**
scripts/preview-v2-real.mjs
next.config.mjs
app/**
components/**
hooks/**
other frontend clients
next-env.d.ts
pnpm-lock.yaml
systemd/env/main
~~~

## 4. Preflight

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
HEAD = origin = 933e749137d00c262c8f2cedec7b945582bf40d1
tracked implementation modify = exact 4
untracked implementation new = exact 2
accepted docs new = exact 3
index empty
only five frozen unrelated paths outside accepted scope
~~~

Если scope отличается — остановиться.

## 5. Stage exact paths

Только explicit path staging. Запрещены `git add .`, `git add -A`, wildcards.

~~~bash
git add -- \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_today_preview_transport.py \
  lib/grace/api/client.ts \
  __tests__/api/grace-client.test.ts \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/110_STAGE_1_W2_GUARDED_TRANSPORT_ROUTE_SERVICE_FRONTEND_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/111_STAGE_1_W2_ARCH_REVIEW_R1_RAW_HOST_CHAIN_TZ.md \
  docs/work/2026-07-11_today-v2-real-horizons-main-deploy/112_STAGE_1_W2_ARCH_ACCEPTANCE_COMMIT_PUSH_TZ.md
~~~

## 6. Staged verification

~~~bash
git diff --cached --name-only
git diff --cached --check
git diff --cached --stat
~~~

Доказать exact equality со списком из §2:

~~~text
TOTAL=9
IMPLEMENTATION=6
ARCH_DOCS=3
FORBIDDEN=0
~~~

### 6.1 Final focused proof before commit

~~~bash
PYTHONPATH=apps/api apps/api/.venv/bin/python - <<'PY'
from app.services.today_preview_guard import *

case = TodayPreviewGuardInput(
    app_env="development",
    marker_value=TODAY_PREVIEW_HEADER_VALUE,
    client_host="127.0.0.1",
    host="public.example:8000",
    origin=None,
    forwarded=None,
    x_forwarded_for="127.0.0.1",
    x_forwarded_host="127.0.0.1:3003",
    x_forwarded_port="3003",
    x_real_ip=None,
    tg_user_id=TODAY_PREVIEW_TG_USER_ID,
    tg_username=TODAY_PREVIEW_TG_USERNAME,
)
decision = authorize_today_preview(case)
assert decision.authorized is False
assert decision.reason is TodayPreviewGuardReason.HOST_DENIED
print("ADVERSARIAL_HOST_CHAIN: PASS")
PY

apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_today_preview_transport.py

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py \
  -q

npx vitest run __tests__/api/grace-client.test.ts
~~~

Ожидается:

~~~text
adversarial: PASS
backend exact GRACE: PASS_4_OF_4
backend W2 module: 59 passed
frontend focused: 20 passed
~~~

Не повторять full suites: они уже приняты на exact worktree.

## 7. Commit

Exact subject:

~~~text
feat(preview): add guarded real v2 request path
~~~

~~~bash
git commit -m "feat(preview): add guarded real v2 request path"
~~~

После commit:

~~~bash
git show --check --oneline HEAD
git diff-tree --no-commit-id --name-only -r HEAD
git status --short --branch
~~~

Parent обязан быть:

~~~text
933e749137d00c262c8f2cedec7b945582bf40d1
~~~

## 8. Push

~~~bash
git push origin preview/solarsage-v2-human-first-navigator-ux
~~~

После push:

~~~bash
git rev-parse HEAD
git rev-parse refs/remotes/origin/preview/solarsage-v2-human-first-navigator-ux
git ls-remote --heads origin refs/heads/preview/solarsage-v2-human-first-navigator-ux
~~~

Все SHA совпадают.

## 9. Final state

~~~bash
git diff --quiet
git diff --cached --quiet
git status --short
ss -ltnp 'sport = :3003 or sport = :18092 or sport = :8000 or sport = :18091 or sport = :3002'
systemctl show \
  solarsage-api.service solarsage-sidecar.service solarsage-frontend.service \
  --property=Id,MainPID,ExecMainStartTimestamp,EnvironmentFiles --no-pager
~~~

Ожидается:

- tracked clean;
- index empty;
- only five frozen untracked paths;
- 3003/18092 absent;
- API PID/start timestamp still `355509` / `Wed 2026-07-08 21:05:20 MSK`;
- sidecar PID/start still `3582982` / `Sun 2026-07-12 22:02:52 MSK`;
- frontend PID/start still `916433` / `Thu 2026-07-09 11:30:03 MSK`;
- env/main unchanged;
- W3 not started.

## 10. Callback

~~~text
PUSHED_STAGE_1_W2
base_sha: 933e749137d00c262c8f2cedec7b945582bf40d1
commit_sha: <sha>
commit_subject: feat(preview): add guarded real v2 request path
commit_paths: EXACT_9
implementation_paths: EXACT_6
architect_docs: EXACT_3_110_TO_112
staged_diff_check: PASS
adversarial_host_chain: PASS_DENIED
backend_exact_grace: PASS_4_OF_4
backend_w2_module: 59 PASS
frontend_focused: 20 PASS
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
