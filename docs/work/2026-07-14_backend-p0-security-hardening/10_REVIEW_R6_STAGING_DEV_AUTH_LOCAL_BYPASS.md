# Review R6 — закрыть local `/api/auth/dev` bypass в staging

Дата: 2026-07-14

Ветка: `fix/backend-p0-security-hardening`

Текущий HEAD: `f3a4a116fa7ce046c51532040ce02cc2864a0af6`

Исполнитель: интерактивный кодер в `tmux astro:0.0`

Роль архитектора: постановка, независимый security review, live-приёмка

## 1. Статус предыдущего rollout

R5 в целом успешен:

- staging env валиден;
- CORS exact allowlist работает;
- четыре P0 internal routes отсутствуют;
- logging privacy canary зелёные;
- API active/running на commit `f3a4a11`;
- secrets не изменены и имеют mode 600;
- push не выполнялся.

Но финальная архитектурная проверка обнаружила отдельный fail-closed bypass в уже существующем dev-auth guard. До его закрытия P0 не принимается окончательно.

## 2. Подтверждённая проблема

Файл:

```text
apps/api/app/api/auth.py
```

Текущая функция:

```python
def _is_local_dev_auth_request(request: Request) -> bool:
    if settings.app_env == "production":
        return False
    ...
```

Текущий endpoint guard:

```python
if not settings.dev_mode and not _is_local_dev_auth_request(request):
    raise HTTPException(403, ...)
```

Из-за проверки только literal `production` функция возвращает `True` для прямого loopback request в средах:

- `staging`;
- `stage`;
- `preview`;
- `test`;
- неизвестных/пустых значениях, если модуль вызван отдельно от startup policy.

На реально запущенном staging архитектор получил read-only доказательство без создания session:

```text
runtime_app_env staging
synthetic_local_dev_auth_allowed True
```

Публичный запрос через Nginx сейчас получает 403 благодаря proxy headers, но прямой запрос к `127.0.0.1:8000` без proxy marker проходит guard и способен создать test user/session. Это local-process/SSRF bypass и нарушение канона:

```text
Dev auth допустим только в canonical development environment.
Staging/production auth — только Telegram HMAC.
```

Startup policy с `DEV_MODE=false` не компенсирует ошибку endpoint guard, потому что функция явно обходит `DEV_MODE=false` для «local request».

## 3. Exact scope

Разрешено изменить только:

```text
apps/api/app/api/auth.py
apps/api/tests/test_auth_endpoints.py
docs/work/2026-07-14_backend-p0-security-hardening/10_REVIEW_R6_STAGING_DEV_AUTH_LOCAL_BYPASS.md
```

Не менять:

- `runtime_security.py`;
- `main.py`;
- другие routers/services/tests;
- `.env` и `.env.production`;
- Nginx/systemd units;
- DB schema/data вручную;
- frontend/sidecar/bot.

Никакого общего auth refactor, router split, rate limiting или нового endpoint в этом corrective.

## 4. Exact implementation

### 4.1. Canonical development check

В `apps/api/app/api/auth.py` добавить рядом с `_LOCAL_DEV_HOSTS` immutable allowlist:

```python
_LOCAL_DEVELOPMENT_ENVS = frozenset({"dev", "development"})
```

В начале `_is_local_dev_auth_request()` заменить literal production check на fail-closed normalization:

```python
def _is_local_dev_auth_request(request: Request) -> bool:
    raw_env = settings.app_env
    environment = raw_env.strip().lower() if isinstance(raw_env, str) else ""
    if environment not in _LOCAL_DEVELOPMENT_ENVS:
        return False
    if not _is_loopback_client(request):
        return False
    if _host_header_name(request.headers.get("host")) not in _LOCAL_DEV_HOSTS:
        return False
    return not _has_proxy_origin_header(request)
```

Не использовать условие `!= production`, потому что оно снова забудет staging/test/unknown.

Не импортировать `build_runtime_security_policy()` в auth route: endpoint guard должен быть маленьким, side-effect-free и не запускать полную startup validation на request path.

Не менять дальнейшую логику создания dev user/profile/session.

### 4.2. Сохранить deliberate local development behavior

После исправления должны одновременно выполняться:

| APP_ENV | DEV_MODE | Request | Результат |
|---|---:|---|---|
| `development` | false | loopback client + local Host + no proxy headers | разрешён, как сейчас |
| `dev` | false | loopback client + local Host + no proxy headers | разрешён |
| `development` | false | public Host | 403 |
| `development` | false | любой proxy-origin header | 403 |
| `staging`/`stage`/`preview` | false | даже идеальный loopback/local Host | 403 |
| `production`/`prod` | false | любой request | 403 |
| `test`/unknown/empty/non-string | false | любой request | 403 |

Не менять существующий контракт, по которому deliberate local development может работать при `DEV_MODE=false`: этот fallback уже покрыт тестами и нужен текущему local workflow. В этой задаче требуется только environment boundary.

### 4.3. GRACE/module contract truth

Поскольку меняется security behavior публичного route, привести комментарии `auth.py` в соответствие, не переписывая весь файл:

- `AI_HEADER/ROLE` должен упоминать `/api/auth/dev` как local-development-only surface;
- module contract `purpose` должен перечислять Telegram auth, logout и local dev auth;
- `invariants` должен явно говорить: local dev auth fail-closed outside canonical `dev|development`;
- module map должен включать `ROUTE_AUTH_DEV`;
- function contract `_is_local_dev_auth_request` добавить, если его нет;
- `auth_dev.error_behavior` уточнить: 403 outside canonical local development or when request is not trusted-local.

Не добавлять произвольные log events.

## 5. Exact tests

Файл:

```text
apps/api/tests/test_auth_endpoints.py
```

### 5.1. Обязательный endpoint regression

Добавить async test с `db_session`, если нужен для проверки отсутствия записи:

```python
@pytest.mark.asyncio
async def test_dev_auth_denies_loopback_in_staging_when_dev_mode_disabled(...):
    monkeypatch.setattr(settings, "dev_mode", False)
    monkeypatch.setattr(settings, "app_env", "staging")

    response = await async_client.post(
        "/api/auth/dev",
        headers={"host": "127.0.0.1:8000"},
    )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "DEV_MODE_DISABLED"
    assert settings.session_cookie_name not in response.headers.get("set-cookie", "")
```

Дополнительно доказать отсутствие side effect: после response в DB не должно появиться нового `User` с `tg_user_id == 999999999`. Использовать `select(User)` и assert `scalar_one_or_none() is None`. Если fixture уже создаёт такого user, вместо этого зафиксировать count до/после; не удалять существующие test rows.

### 5.2. Parametric helper regression

Добавить unit/parametrized test на `_is_local_dev_auth_request` или endpoint, который для trusted-looking loopback request возвращает deny для:

```python
[
    "staging",
    "stage",
    "preview",
    "production",
    "prod",
    "test",
    "",
    "unknown",
]
```

Также проверить trim/case для разрешённых local development aliases:

```python
["dev", "development", " DEV ", "Development"]
```

Они должны сохранить существующий local behavior.

Не ослаблять и не удалять существующие tests:

- public Host denied;
- spoofed `x-forwarded-for` denied;
- spoofed `x-forwarded-host` denied;
- localhost development allowed;
- profile/session behavior local development.

### 5.3. Negative tests

Обязательное доказательство, что `DEV_MODE=true` не является самостоятельным способом запустить staging app уже находится в runtime-security tests. Не дублировать полный startup policy здесь.

## 6. Локальные gates до commit

Выполнить:

```bash
cd /opt/solarsage-astro

apps/api/.venv/bin/python -m py_compile apps/api/app/api/auth.py

apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_auth_endpoints.py \
  apps/api/tests/test_runtime_security_policy.py \
  apps/api/tests/test_public_surface_security.py \
  apps/api/tests/test_cors_security.py \
  apps/api/tests/test_logging.py \
  apps/api/tests/test_logging_privacy.py \
  apps/api/tests/test_log_envelope_shape.py \
  apps/api/tests/test_log_intake.py \
  apps/api/tests/test_redactor_canaries.py \
  apps/api/tests/test_microcopy_misses.py \
  -q

apps/api/.venv/bin/python -m ruff check \
  apps/api/app/api/auth.py \
  apps/api/tests/test_auth_endpoints.py

python3 scripts/grace_lint.py \
  apps/api/app/api/auth.py \
  apps/api/tests/test_auth_endpoints.py

python3 scripts/check_logging_guardrails.py
git diff --check
```

Затем полный backend suite, потому что auth fixture используется широко:

```bash
cd /opt/solarsage-astro/apps/api
.venv/bin/python -m pytest tests/ -q
```

Любой fail — commit/restart запрещены. Не чинить unrelated test и не расширять scope.

## 7. Commit boundary

Перед staging:

```bash
cd /opt/solarsage-astro
git status --short
git diff -- apps/api/app/api/auth.py apps/api/tests/test_auth_endpoints.py
```

Ожидаются только два modified code/test файла и этот новый untracked docs-файл; frozen paths остаются untracked.

Stage только:

```bash
git add -- \
  apps/api/app/api/auth.py \
  apps/api/tests/test_auth_endpoints.py \
  docs/work/2026-07-14_backend-p0-security-hardening/10_REVIEW_R6_STAGING_DEV_AUTH_LOCAL_BYPASS.md
```

Проверить:

```bash
git diff --cached --check
git diff --cached --name-status
```

Создать отдельный локальный commit:

```bash
git commit -m "fix(api): deny dev auth outside local development"
```

Не amend предыдущий commit. Не push.

## 8. Runtime preflight и controlled restart

Env уже настроен и валиден. Его не менять и новый backup не создавать.

До restart выполнить с реальным `.env`:

```bash
cd /opt/solarsage-astro/apps/api
sudo -u astro /home/astro/.local/bin/dotenv \
  -f /opt/solarsage-astro/.env run -- \
  /opt/solarsage-astro/apps/api/.venv/bin/python -c '
from app.api.auth import _is_local_dev_auth_request
from app.core.config import settings
from app.main import app
from starlette.requests import Request
scope = {
    "type": "http",
    "asgi": {"version": "3.0"},
    "http_version": "1.1",
    "method": "POST",
    "scheme": "http",
    "path": "/api/auth/dev",
    "raw_path": b"/api/auth/dev",
    "query_string": b"",
    "root_path": "",
    "server": ("127.0.0.1", 8000),
    "client": ("127.0.0.1", 45678),
    "headers": [(b"host", b"127.0.0.1:8000")],
}
assert settings.app_env == "staging"
assert settings.dev_mode is False
assert _is_local_dev_auth_request(Request(scope)) is False
assert "/api/auth/telegram" in {r.path for r in app.routes}
print("r6_staging_dev_auth_preflight_ok")
'
```

Если assertion/import падает — restart запрещён.

Снять PID API и соседних сервисов. Затем перезапустить только:

```bash
sudo systemctl restart solarsage-api.service
```

Не restart frontend/sidecar/bot/nginx.

## 9. Live acceptance после restart

### 9.1. Health/SHA

Local/dev/test `/api/health`:

- HTTP 200;
- exact keys `status`, `version`, `git_sha`;
- `git_sha` равен short SHA нового R6 commit.

### 9.2. Главный regression probe

Теперь безопасно выполнить прямой local request без proxy headers:

```bash
curl --connect-timeout 5 --max-time 15 \
  -i -X POST \
  -H 'Host: 127.0.0.1:8000' \
  http://127.0.0.1:8000/api/auth/dev
```

Обязательно:

- HTTP 403;
- error code `DEV_MODE_DISABLED`;
- нет `Set-Cookie`;
- нет нового session/user side effect.

Публичный dev-host request также 403.

### 9.3. Не сломать Telegram auth

Не посылать fake real auth, который может шуметь. Достаточно:

- `/api/auth/telegram` присутствует в local OpenAPI/route table;
- malformed empty request возвращает contract validation/auth error, но не 404/500;
- Telegram auth tests зелёные.

### 9.4. P0 smoke после второго restart

Повторить компактно:

- four internal routes local/dev -> 404;
- evil Origin GET/OPTIONS -> no ACAO;
- allowed dev Origin GET -> exact ACAO;
- synthetic raw `X-Correlation-Id` -> response `h1_[0-9a-f]{24}`, raw отсутствует в journal;
- journal traceback/error count 0;
- соседние service PID не изменились;
- `NRestarts` API стабилен.

Не повторять `/api/_log` malicious batch, если код logging не менялся; достаточно убедиться, что предыдущий marker/logging journal остаётся safe и новый request correlation smoke зелёный.

## 10. Финальное состояние

```bash
git branch --show-current
git log -2 --oneline
git status --short
git diff --check
git diff --cached --check
```

Ожидается:

- два локальных P0 commit, верхний R6;
- no push;
- code/docs clean;
- только frozen untracked paths.

## 11. Формат handoff

```text
R6 RESULT: PASS | FAIL

Code:
- files changed:
- exact guard behavior:
- targeted tests:
- full API tests:
- ruff:
- GRACE lint:
- logging guardrails:

Git:
- previous P0 SHA:
- R6 SHA:
- pushed: no
- status:

Preflight:
- synthetic staging loopback allowed: false

Runtime:
- old/new API PID:
- active/substate/NRestarts:
- neighbor PIDs unchanged:

Live auth:
- local direct /api/auth/dev status/code/set-cookie:
- public /api/auth/dev status/code/set-cookie:
- Telegram route present:
- DB side effect: none

Regression smoke:
- health local/dev/test + SHA:
- internal routes:
- CORS allowed/evil:
- correlation privacy:
- journal errors/tracebacks:

Rollback:
- used: no | details
```

После handoff остановиться. Push запрещён.
