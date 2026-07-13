# Stage 1.W2 — архитектурное ревью R1: raw Host must remain loopback

Дата: 2026-07-13
Ветка: `preview/solarsage-v2-human-first-navigator-ux`
Base HEAD/origin: `933e749137d00c262c8f2cedec7b945582bf40d1`
Родительское ТЗ: `110_STAGE_1_W2_GUARDED_TRANSPORT_ROUTE_SERVICE_FRONTEND_TZ.md`
Статус: **R1 CORRECTION REQUIRED — NO COMMIT / NO PUSH**

## 0. Роль и цель

Ты кодер. Исправь один подтверждённый security defect W2 и заверши callback.

Вся остальная W2 реализация предварительно принята:

~~~text
changed implementation paths: exact 6
backend exact GRACE: pass 4/4
backend exact ruff: pass
backend exact mypy: pass
backend compile: pass
new W2 backend module: 59 passed
frontend focused: 20 passed
typecheck: pass
contracts check: pass, 110 focused contract tests
production guard: pass
git diff check: pass
~~~

Не переписывай guard/route/service/frontend architecture.

## 1. Блокирующий finding

Сейчас guard ошибочно авторизует эту комбинацию:

~~~text
app_env=development
marker=today-v2-real
client_host=127.0.0.1
Host=public.example:8000
X-Forwarded-For=127.0.0.1
X-Forwarded-Host=127.0.0.1:3003
X-Forwarded-Port=3003
exact dev identity
~~~

Фактический результат до R1:

~~~text
TodayPreviewGuardDecision(authorized=True, reason=authorized)
~~~

Причина: `authorize_today_preview` выбирает local forwarded host как effective
host и не валидирует raw `Host`, когда forwarded host присутствует.

Это нарушает ТЗ 110:

- public Host deny;
- весь transport/forwarded chain должен оставаться local/loopback;
- local forwarded metadata не может «перекрыть» публичный raw authority.

## 2. Exact R1 allowlist

Разрешено менять только:

~~~text
apps/api/app/services/today_preview_guard.py
apps/api/tests/test_today_preview_transport.py
~~~

Не менять остальные четыре W2 implementation path:

~~~text
apps/api/app/api/day.py
apps/api/app/services/today_service.py
lib/grace/api/client.ts
__tests__/api/grace-client.test.ts
~~~

Не менять документ 111, auth/core/schema/db/contracts/launcher/services/env.

Итоговый общий W2 scope по-прежнему exact 6 implementation paths.

## 3. Required guard correction

До effective-host precedence валидировать raw `Host` независимо от forwarded
host:

~~~text
Host present + malformed authority -> HOST_DENIED
Host present + public/non-loopback authority -> HOST_DENIED
Host present + valid loopback authority -> continue
~~~

`X-Forwarded-Host` / RFC `Forwarded host=` всё ещё определяют effective external
preview authority/port по правилам ТЗ 110, но не имеют права скрыть public raw
Host.

Canonical Next rewrite остаётся разрешён:

~~~text
Host=127.0.0.1:8000
X-Forwarded-Host=127.0.0.1:3003
X-Forwarded-Port=3003
all forwarded clients loopback
~~~

Direct local остаётся разрешён:

~~~text
Host=127.0.0.1:3003
no forwarded headers
~~~

Отсутствующий Host можно трактовать по текущей effective-host fail-closed logic;
не расширяй allow surface. Public/malformed present Host обязан deny.

Не менять reason enum. Для finding использовать existing `HOST_DENIED`.

## 4. Required tests

В existing canonical file добавить/расширить parametrization без создания нового
test file:

~~~text
apps/api/tests/test_today_preview_transport.py
~~~

Обязательные cases:

1. public raw Host + otherwise exact local X-Forwarded-* -> `HOST_DENIED`;
2. malformed raw Host + otherwise exact local X-Forwarded-* -> `HOST_DENIED`;
3. internal loopback Host:8000 + forwarded loopback Host:3003 remains authorized;
4. direct loopback Host:3003 remains authorized.

Не добавлять sleep, network or live service dependency.

Test file сейчас 997 lines при limit 1000. После R1 он обязан оставаться
`<= 1000` и проходить exact GRACE. Используй существующую parametrization и/или
компактируй только комментарии/форматирование; не удаляй semantic coverage и не
добавляй lint suppression.

## 5. No other changes

Запрещено:

- менять evaluation order production/env/marker/client/forwarded/host/origin/port/identity;
- менять constants/reasons;
- ослаблять forwarded address/host checks;
- менять route/service/frontend behavior;
- менять tests вне allowlist;
- делать git add, commit или push;
- запускать W3, service restart, 3003 или 18092.

## 6. Mandatory gates

### 6.1 Exact guard proof

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
print("PUBLIC_RAW_HOST_WITH_LOCAL_FORWARDED: DENIED")
PY
~~~

### 6.2 Backend exact

~~~bash
wc -l apps/api/tests/test_today_preview_transport.py

apps/api/.venv/bin/python scripts/grace_lint.py \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_today_preview_transport.py

apps/api/.venv/bin/ruff check \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_today_preview_transport.py

apps/api/.venv/bin/mypy --follow-imports=skip \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py

apps/api/.venv/bin/python -m py_compile \
  apps/api/app/services/today_preview_guard.py \
  apps/api/app/api/day.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/test_today_preview_transport.py

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py \
  -q
~~~

### 6.3 W2 regression gates

~~~bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_today_preview_transport.py \
  apps/api/tests/test_today_selection_context.py \
  apps/api/tests/test_scoring_v2_runtime_flags.py \
  apps/api/tests/test_today_cache_v2_key.py \
  apps/api/tests/test_today_meta_versions.py \
  apps/api/tests/test_day_endpoints.py \
  -q

apps/api/.venv/bin/python -m pytest apps/api/tests/ -q

npx vitest run __tests__/api/grace-client.test.ts
npx vitest run
npx tsc --noEmit
pnpm contracts:check
pnpm guardrails:prod
~~~

Zero failures required. Frontend files are unchanged in R1, but full callback
must contain final counts because the initial coder stopped before callback.

### 6.4 Scope/final state

~~~bash
git diff --check
git diff --cached --quiet
git diff --name-only
git ls-files --others --exclude-standard apps/api lib __tests__
git rev-parse HEAD
git rev-parse origin/preview/solarsage-v2-human-first-navigator-ux
ss -ltnp 'sport = :3003 or sport = :18092 or sport = :8000 or sport = :18091 or sport = :3002'
systemctl is-active solarsage-api.service solarsage-sidecar.service solarsage-frontend.service
~~~

Ожидается exact 6 W2 implementation paths, index empty, HEAD/origin unchanged,
3003/18092 absent, services unchanged.

## 7. Callback

~~~text
READY_FOR_ARCH_REVIEW_STAGE_1_W2_R1
base_sha: 933e749137d00c262c8f2cedec7b945582bf40d1
r1_changed_paths: EXACT_2
overall_w2_implementation_paths: EXACT_6
public_raw_host_with_local_forwarded: DENIED_HOST
malformed_raw_host_with_local_forwarded: DENIED_HOST
next_rewrite_loopback_3003: PASS
direct_loopback_3003: PASS
guard_test_file_lines: <count <= 1000>
backend_exact_grace: PASS_4_OF_4
backend_w2_module: <count> PASS
backend_focused: <count> PASS
backend_full: <counts>
frontend_focused: <count> PASS
frontend_full: <counts>
typecheck: PASS
contracts_check: PASS
prod_guard: PASS
git_diff_check: PASS
index: EMPTY
commit: NOT_CREATED
push: NOT_CREATED
head_origin: 933e749137d00c262c8f2cedec7b945582bf40d1_EQUAL
ports_3003_18092: ABSENT
services_env_main: UNCHANGED
unrelated_paths: UNTOUCHED
next_wave: NOT_STARTED
~~~

После callback остановиться.
