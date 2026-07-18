# ТЗ R5 — controlled staging rollout и live-доказательства P0

Дата: 2026-07-14
Ветка: `fix/backend-p0-security-hardening`
Исполнитель: кодер в `tmux astro:0.0`
Роль архитектора: постановка, контроль, ревью и финальная приёмка
Статус кода до начала этого этапа: R4A принят; полный API suite, Ruff, GRACE lint, logging guardrails, compileall и `git diff --check` зелёные.

## 1. Цель этапа

Безопасно довести уже реализованные P0-исправления до реально запущенного staging API на этом сервере и доказать снаружи, что:

1. публичный API больше не работает как `development`;
2. внутренние маршруты физически отсутствуют в route table;
3. CORS разрешает только два точных HTTPS origin и не отражает произвольный Origin;
4. входящий `X-Correlation-Id` становится непрозрачным `h1_<24 hex>`;
5. raw UUID/ID canary не попадает в journald даже через `/api/_log`;
6. `/api/health` остаётся доступным и показывает SHA принятого коммита;
7. остальные systemd-сервисы не перезапускаются;
8. код и документация зафиксированы локальным коммитом, но ничего не отправлено в remote.

Это operational-этап. Не добавлять новый функционал, не рефакторить принятый код и не «улучшать заодно» другие сервисы.

## 2. Жёсткие ограничения

### 2.1. Разрешено

- читать состояние git/systemd/nginx/env без показа секретных значений;
- запустить перечисленные ниже проверки;
- создать один локальный commit принятого P0-набора;
- сделать защищённую резервную копию `.env`;
- изменить только перечисленные несекретные ключи в `/opt/solarsage-astro/.env`;
- ужесточить права на `.env` и `.env.production`;
- выполнить preflight импорта;
- перезапустить только `solarsage-api.service`;
- выполнить локальные и HTTPS live-probes;
- при реальной аварии применить описанный ниже согласованный rollback.

### 2.2. Запрещено

- `git add .`, `git add -A`, `git commit -a`;
- `git reset --hard`, `git checkout --`, удаление пользовательских файлов;
- push, force-push, merge, rebase;
- менять `main` или переключаться с текущей ветки;
- печатать целиком `.env`, `.env.production`, process environment или journal;
- выводить token, cookie, Telegram initData, DATABASE_URL, API keys, salt;
- генерировать новый `GRACE_USER_SALT`: текущий salt длиной 40 уже есть, его необходимо сохранить байт-в-байт;
- изменять значения любых env-ключей, кроме whitelist из раздела 6;
- трогать БД, запускать Alembic, инвалидировать кэши: этот P0 не меняет DB schema и cache schema;
- перезапускать `solarsage-sidecar`, `solarsage-frontend`, `ductor-astro`, PostgreSQL, Docker или Nginx;
- запускать ручной `uvicorn`, `nohup` или второй API-процесс;
- модифицировать код после локального commit без остановки и отдельного отчёта архитектору.

### 2.3. Замороженные пути — не читать в staging, не добавлять, не удалять, не менять

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Они должны остаться untracked и не попасть в commit.

## 3. Каноническая runtime-топология

- API unit: `solarsage-api.service`
- API bind: `127.0.0.1:8000`
- API EnvironmentFile: `/opt/solarsage-astro/.env`
- API WorkingDirectory: `/opt/solarsage-astro/apps/api`
- Python: `/opt/solarsage-astro/apps/api/.venv/bin/python`
- Uvicorn запускается только systemd unit-ом.
- Public hosts:
  - `https://dev.astro.vasiliy-ivanov.ru`
  - `https://test.astro.vasiliy-ivanov.ru`
- Nginx уже проксирует `/api/*` на `127.0.0.1:8000`; его конфигурацию не менять.

## 4. Фаза A — неизменяемый pre-commit аудит

Перед любыми staging/config действиями выполнить и сохранить в итоговый отчёт только безопасные результаты:

```bash
cd /opt/solarsage-astro
git branch --show-current
git rev-parse HEAD
git status --short
git diff --check
```

Обязательные условия:

- branch ровно `fix/backend-p0-security-hardening`;
- исходный HEAD до P0-коммита ожидается `8f9aa022550653020e0dc9d1f1269d73f6ee63cf`;
- `git diff --check` пустой и exit code 0;
- в status нет неожиданного tracked-файла вне принятого набора;
- frozen paths только untracked.

Если условие не выполнено — ничего не stage, не commit, не менять env, не restart; остановиться и сообщить архитектору.

### 4.1. Последний компактный gate перед commit

Полный suite уже был принят на R4A, но перед фиксацией выполнить минимум:

```bash
cd /opt/solarsage-astro/apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_runtime_security_policy.py \
  tests/test_public_surface_security.py \
  tests/test_cors_security.py \
  tests/test_logging.py \
  tests/test_logging_privacy.py \
  tests/test_log_envelope_shape.py \
  tests/test_log_intake.py \
  tests/test_redactor_canaries.py \
  tests/test_microcopy_misses.py \
  -q
python -m ruff check app tests
deactivate
cd /opt/solarsage-astro
python3 scripts/check_logging_guardrails.py
git diff --check
```

Любой non-zero exit запрещает commit и rollout.

Не «чинить тест на месте». Если gate красный, зафиксировать имя теста/проверки и остановиться.

## 5. Фаза B — точный локальный commit

### 5.1. Stage только whitelist

Не использовать широкие команды staging. Выполнить ровно explicit add принятого набора:

```bash
cd /opt/solarsage-astro
git add -- \
  .env.example \
  apps/api/.env.example \
  apps/api/app/api/_log.py \
  apps/api/app/api/auth.py \
  apps/api/app/api/debug.py \
  apps/api/app/api/natal.py \
  apps/api/app/core/config.py \
  apps/api/app/core/dependencies.py \
  apps/api/app/core/log_identity.py \
  apps/api/app/core/logging.py \
  apps/api/app/core/redactor.py \
  apps/api/app/core/runtime_security.py \
  apps/api/app/main.py \
  apps/api/app/middleware/correlation.py \
  apps/api/app/services/calendar_service.py \
  apps/api/app/services/chat_service.py \
  apps/api/app/services/day_scoring_runtime_service.py \
  apps/api/app/services/horary_service.py \
  apps/api/app/services/log_intake.py \
  apps/api/app/services/natal_report_service.py \
  apps/api/app/services/today_service.py \
  apps/api/tests/conftest.py \
  apps/api/tests/test_cors_security.py \
  apps/api/tests/test_log_envelope_shape.py \
  apps/api/tests/test_log_intake.py \
  apps/api/tests/test_logging.py \
  apps/api/tests/test_logging_privacy.py \
  apps/api/tests/test_microcopy_misses.py \
  apps/api/tests/test_public_surface_security.py \
  apps/api/tests/test_redactor_canaries.py \
  apps/api/tests/test_runtime_security_policy.py \
  scripts/check_logging_guardrails.py \
  docs/work/2026-07-14_backend-legacy-refactoring-audit \
  docs/work/2026-07-14_backend-p0-security-hardening
```

После staging выполнить:

```bash
git diff --cached --check
git diff --cached --name-status
git status --short
```

Проверить автоматически и визуально:

- нет `.env` и `.env.production`;
- нет ни одного frozen path;
- нет файлов вне whitelist;
- новые `log_identity.py`, `runtime_security.py` и 4 новых security-test файла staged;
- оба docs/work каталога staged, включая этот R5-файл.

Если staged набор неверный, разрешено только точечно снять ошибочный path через `git restore --staged -- <path>`; рабочее содержимое не удалять.

### 5.2. Локальный commit

После точной проверки:

```bash
git commit -m "fix(api): harden deployed runtime and logging privacy"
```

Сохранить безопасные идентификаторы:

```bash
git rev-parse HEAD
git rev-parse --short HEAD
git show --stat --oneline --summary HEAD
```

Назовём новый SHA `P0_COMMIT`. Push запрещён.

После commit не должно остаться tracked modifications. Допустимы только frozen untracked paths. Если есть иной modified/untracked файл — не продолжать rollout до объяснения.

## 6. Фаза C — защищённый backup и staging env

### 6.1. Backup без вывода содержимого

Создать root-only каталог и копию текущего `.env`:

```bash
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
sudo install -d -o root -g root -m 0700 /var/backups/solarsage-astro
sudo install -o root -g root -m 0600 \
  /opt/solarsage-astro/.env \
  "/var/backups/solarsage-astro/.env.before-p0-${stamp}"
sudo stat -c '%n mode=%a owner=%U group=%G size=%s' \
  "/var/backups/solarsage-astro/.env.before-p0-${stamp}"
```

Не выполнять `cat`, `head`, `tail`, `dotenv list`, `env`, `printenv` над secret-файлом/process env.

Запомнить путь как `ENV_BACKUP` для возможного согласованного rollback.

### 6.2. До изменения проверить только metadata/наличие

Разрешена проверка только имён ключей, количества и длины значений. Значения секретов не печатать.

Обязательно подтвердить:

- `DATABASE_URL` присутствует и не пустой;
- `TELEGRAM_BOT_TOKEN` присутствует и не пустой;
- `GRACE_USER_SALT` присутствует и имеет длину не менее 32;
- текущий salt не копируется в отчёт и не заменяется.

Для этого использовать скрипт/команду, выводящую только `KEY present length=N` для этих трёх ключей. Не выводить значение даже частично.

### 6.3. Единственный whitelist изменяемых env-значений

В `/opt/solarsage-astro/.env` установить ровно:

```dotenv
APP_ENV=staging
GRACE_ENV=staging
APP_DOMAIN=dev.astro.vasiliy-ivanov.ru
CORS_ALLOWED_ORIGINS=https://dev.astro.vasiliy-ivanov.ru,https://test.astro.vasiliy-ivanov.ru
DEV_MODE=false
SESSION_COOKIE_SECURE=true
```

Все остальные строки/ключи должны сохранить прежние значения. Особенно не менять:

- `GRACE_USER_SALT`;
- `TELEGRAM_BOT_TOKEN`;
- `DATABASE_URL`;
- LLM provider/model/API keys;
- sidecar URL;
- V2 flags;
- session name/TTL;
- любые bot/frontend значения.

Использовать установленный `python-dotenv` CLI, а не ручной `sed`, `tee`, `cat` или patch secret-файла. Запускать от владельца `astro`, чтобы не превратить файл в root-owned:

```bash
DOTENV=/home/astro/.local/bin/dotenv
ENV_FILE=/opt/solarsage-astro/.env

sudo -u astro "$DOTENV" -f "$ENV_FILE" -q never set APP_ENV staging
sudo -u astro "$DOTENV" -f "$ENV_FILE" -q never set GRACE_ENV staging
sudo -u astro "$DOTENV" -f "$ENV_FILE" -q never set APP_DOMAIN dev.astro.vasiliy-ivanov.ru
sudo -u astro "$DOTENV" -f "$ENV_FILE" -q never set CORS_ALLOWED_ORIGINS https://dev.astro.vasiliy-ivanov.ru,https://test.astro.vasiliy-ivanov.ru
sudo -u astro "$DOTENV" -f "$ENV_FILE" -q never set DEV_MODE false
sudo -u astro "$DOTENV" -f "$ENV_FILE" -q never set SESSION_COOKIE_SECURE true
```

Примечание: эти шесть значений несекретны; допустимый stdout `KEY=value` относится только к ним.

После изменения:

```bash
sudo chown astro:astro /opt/solarsage-astro/.env /opt/solarsage-astro/.env.production
sudo chmod 0600 /opt/solarsage-astro/.env /opt/solarsage-astro/.env.production
sudo stat -c '%n mode=%a owner=%U group=%G size=%s' \
  /opt/solarsage-astro/.env \
  /opt/solarsage-astro/.env.production
```

Оба файла должны быть `astro:astro`, mode `600`. Содержимое `.env.production` не изменять.

### 6.4. Post-edit invariant без вывода секретов

Проверяющий скрипт должен завершиться non-zero, если:

- любой из шести whitelist-ключей отсутствует;
- любой встречается не ровно один раз;
- значение не совпадает с указанным;
- `GRACE_USER_SALT` теперь короче 32;
- `TELEGRAM_BOT_TOKEN`/`DATABASE_URL` пусты.

В stdout вывести только:

```text
runtime_env_whitelist_ok
secret_presence_ok DATABASE_URL length=<N>
secret_presence_ok TELEGRAM_BOT_TOKEN length=<N>
secret_presence_ok GRACE_USER_SALT length=<N>
```

Никаких значений.

## 7. Фаза D — preflight до restart

Старый API-процесс пока продолжает работать. До его остановки доказать, что новый процесс сможет импортировать app с обновлённым env.

### 7.1. Проверка unit и текущего PID

```bash
sudo systemctl cat solarsage-api.service
sudo systemctl is-active solarsage-api.service
sudo systemctl show solarsage-api.service \
  -p MainPID -p ActiveState -p SubState -p NRestarts
```

В отчёт не копировать EnvironmentFile содержимое. Ожидается:

- WorkingDirectory `/opt/solarsage-astro/apps/api`;
- ExecStart `.venv/bin/uvicorn ... --host 127.0.0.1 --port 8000`;
- один API unit;
- active/running до restart.

Сохранить `OLD_MAIN_PID` и текущее `NRestarts`.

### 7.2. Import/policy preflight с реальным `.env`

Использовать `dotenv run`, чтобы и Pydantic, и прямые `os.getenv()` получили тот же env, что systemd. Команда не должна печатать env:

```bash
cd /opt/solarsage-astro/apps/api
sudo -u astro /home/astro/.local/bin/dotenv \
  -f /opt/solarsage-astro/.env run -- \
  /opt/solarsage-astro/apps/api/.venv/bin/python -c '
from app.core.config import settings
from app.core.runtime_security import build_runtime_security_policy
from app.main import app
p = build_runtime_security_policy(settings)
assert p.environment == "staging"
assert p.deployed is True
assert p.internal_routes_enabled is False
assert p.cors_allowed_origins == (
    "https://dev.astro.vasiliy-ivanov.ru",
    "https://test.astro.vasiliy-ivanov.ru",
)
assert settings.dev_mode is False
assert settings.session_cookie_secure is True
paths = {r.path for r in app.routes}
for forbidden in (
    "/api/debug",
    "/api/metrics",
    "/api/health/extended",
    "/api/admin/microcopy/misses",
):
    assert forbidden not in paths
assert "/api/health" in paths
print("startup_preflight_ok", len(paths))
'
```

Если import/policy/assert падает, restart запрещён. Не обходить validation и не ослаблять staging-настройки. Сообщить только безопасный error code/exception type, без секретных значений.

### 7.3. Состояние соседних сервисов до restart

Сохранить только active state и MainPID:

```bash
for unit in \
  solarsage-sidecar.service \
  solarsage-frontend.service \
  ductor-astro.service \
  nginx.service; do
  sudo systemctl show "$unit" -p Id -p ActiveState -p SubState -p MainPID
done
```

Эти PID потом должны остаться прежними.

## 8. Фаза E — единственный restart API

Только после зелёного preflight:

```bash
RESTART_SINCE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
sudo systemctl restart solarsage-api.service
```

Проверять короткими интервалами; не запускать параллельный uvicorn:

```bash
sudo systemctl is-active solarsage-api.service
sudo systemctl show solarsage-api.service \
  -p MainPID -p ActiveState -p SubState -p NRestarts
```

Условия успеха:

- `active/running`;
- `NEW_MAIN_PID` ненулевой и отличается от `OLD_MAIN_PID`;
- `NRestarts` не растёт при повторной проверке через несколько секунд;
- `ss -ltnp` показывает listener `127.0.0.1:8000` от единственного uvicorn/systemd процесса;
- нет второго ручного API на 8001 или другом неожиданном порту.

Проверка journal после `RESTART_SINCE` должна быть count-only/safe. Не выводить сырые строки целиком. Разрешено сообщить число строк уровня error и имена безопасных exception/error code. Если виден restart loop, сразу перейти к rollback из раздела 12.

## 9. Фаза F — health и public surface

Во всех командах использовать timeout, например `curl --connect-timeout 5 --max-time 15`.

### 9.1. Health

Проверить:

```text
http://127.0.0.1:8000/api/health
https://dev.astro.vasiliy-ivanov.ru/api/health
https://test.astro.vasiliy-ivanov.ru/api/health
```

Для каждого ожидается HTTP 200 и JSON с точным множеством ключей:

```json
{"status": "...", "version": "...", "git_sha": "..."}
```

Никаких дополнительных ключей. `git_sha` должен совпасть с short SHA `P0_COMMIT`. Если `test` host намеренно не маршрутизируется, не додумывать: сохранить код/ошибку и сообщить архитектору, но dev host и local обязаны быть 200.

### 9.2. Внутренние маршруты

Для local и `https://dev.astro.vasiliy-ivanov.ru` каждый маршрут должен вернуть 404:

```text
/api/debug
/api/metrics
/api/health/extended
/api/admin/microcopy/misses
```

401/403/500 не считать успехом. Требуется именно 404: route отсутствует, а не только закрыт auth.

### 9.3. OpenAPI

Получить `/openapi.json` локально и через dev host. JSON `paths` не должен содержать ни один из четырёх внутренних маршрутов. Проверять структурно через `jq`; не через поиск случайного текста всего response.

## 10. Фаза G — live CORS matrix

Проверять `/api/health` как обычным GET, так и OPTIONS preflight.

### 10.1. Allowed origin: dev

Origin:

```text
https://dev.astro.vasiliy-ivanov.ru
```

GET и OPTIONS обязаны вернуть:

- `Access-Control-Allow-Origin` ровно этот origin;
- `Access-Control-Allow-Credentials: true`;
- `Vary` содержит `Origin` без учёта регистра;
- нигде нет `Access-Control-Allow-Origin: *`.

### 10.2. Allowed origin: test

Origin:

```text
https://test.astro.vasiliy-ivanov.ru
```

Те же требования; ACAO должен быть ровно test origin.

### 10.3. Forbidden origin

Использовать synthetic origin:

```text
https://evil-p0-canary.invalid
```

GET:

- endpoint сам может вернуть 200 health;
- заголовок `Access-Control-Allow-Origin` должен полностью отсутствовать;
- wildcard отсутствует.

OPTIONS preflight:

- status может быть 400/другой отказ CORSMiddleware;
- `Access-Control-Allow-Origin` должен отсутствовать;
- wildcard отсутствует.

### 10.4. Exactness traps

Дополнительно убедиться, что не разрешены:

- `http://dev.astro.vasiliy-ivanov.ru`;
- `https://dev.astro.vasiliy-ivanov.ru.evil.invalid`;
- `https://evil-p0-canary.invalid?origin=https://dev.astro.vasiliy-ivanov.ru`.

У всех ACAO отсутствует. Не считать наличие `Access-Control-Allow-Credentials: true` само по себе утечкой: критический критерий для forbidden origin — отсутствие ACAO.

Итог представить таблицей: transport, method, origin, status, ACAO, credentials, Vary, verdict. Не прикладывать весь header dump.

## 11. Фаза H — live logging privacy

Использовать только новые synthetic canary, не реальные user/session ID.

### 11.1. Request correlation canary

Сгенерировать raw UUID локально, например через `uuidgen`, и сохранить в shell variable `RAW_REQUEST_CORR`. Отправить:

```text
GET /api/health
X-Correlation-Id: <RAW_REQUEST_CORR>
```

Проверить:

- response HTTP 200;
- response `X-Correlation-Id` fullmatch `^h1_[0-9a-f]{24}$`;
- он не равен raw UUID;
- raw UUID не встречается ни в response body/headers, ни в journal после probe;
- opaque correlation встречается в journal хотя бы один раз.

Не принимать `h1_...suffix`, uppercase hex, 23/25 hex или raw UUID.

### 11.2. `/api/_log` malicious-envelope canary

Сгенерировать отдельные уникальные значения:

- `RAW_ENVELOPE_CORR` — UUID;
- `RAW_USER_HASH_CANARY` — другой UUID, несмотря на имя поля `_hash`;
- `RAW_QUESTION_ID` — третий UUID;
- `RAW_SESSION_ID` — строка `p0-session-<UUID>`.

Через `jq -nc` передать в stdin curl один batch без временного secret-файла:

```json
{
  "envelopes": [
    {
      "ts": "<UTC ISO timestamp>",
      "level": "info",
      "env": "staging",
      "service": "web",
      "service_version": "p0-live-probe",
      "slice": "SEC-P0",
      "module": "M-LIVE-LOG-PROBE",
      "block": "B-PRIVACY",
      "event": "ui.fetch_started",
      "correlation_id": "<RAW_ENVELOPE_CORR>",
      "user_id_hash": "<RAW_USER_HASH_CANARY>",
      "payload": {
        "question_id": "<RAW_QUESTION_ID>",
        "session_id": "<RAW_SESSION_ID>",
        "probe_kind": "synthetic_p0_privacy"
      }
    }
  ]
}
```

Отправить на local `/api/_log`. Ожидается HTTP 200 и:

```json
{"accepted": 1, "rejected": 0}
```

После небольшой задержки проверить journal, начиная с `RESTART_SINCE`, не печатая совпавшие строки:

- count каждого raw canary должен быть 0;
- строка `synthetic_p0_privacy` должна встречаться хотя бы один раз, иначе probe не доказан;
- envelope correlation должен быть валидным opaque `h1_[0-9a-f]{24}`;
- raw `user_id_hash` должен стать `[redacted-identifier]` либо другим контрактным безопасным представлением, но не сохраниться raw;
- `question_id` и `session_id` не должны содержать raw значения;
- ни один log line этого probe не должен содержать token/cookie/initData.

Для journal использовать проверки вида `journalctl ... | rg -F -q "$CANARY"` и сообщать только `present=0/1`, counts и verdict. Не выводить line content.

### 11.3. Общий envelope smoke

Count-only проверить журнальные JSON-события после restart:

- correlation ID, если присутствует, соответствует `^h1_[0-9a-f]{24}$`;
- environment новых событий — `staging`, а не `dev`;
- нет raw полей `user_id`, `session_id`, `question_id`, `report_id`, `credit_id`, `thread_id`, `message_id` с canary/raw UUID;
- нет traceback/restart loop.

Не пытаться доказать отсутствие всех возможных PII печатью журнала. Достаточны автоматические canary checks и counts.

## 12. Rollback — только при реальной аварии

### 12.1. До restart rollback не нужен

Если preflight не прошёл, старый процесс ещё жив. Ничего не restart. Исправления кода/настроек без архитектора запрещены. Сообщить блокер.

### 12.2. После restart нельзя восстанавливать только старый `.env`

Критическая ловушка: новый код специально запрещает public `APP_ENV=development`. Поэтому restore старого `.env` без rollback кода оставит API в startup loop.

При аварии после restart выполнять только согласованный атомарный rollback пары code+env:

1. Зафиксировать безопасный тип ошибки и состояние сервиса.
2. Не использовать reset/checkout.
3. Выполнить non-destructive revert локального P0-коммита:

   ```bash
   cd /opt/solarsage-astro
   git revert --no-edit "$P0_COMMIT"
   ```

4. Восстановить `.env` из `ENV_BACKUP` с `astro:astro`, mode 600:

   ```bash
   sudo install -o astro -g astro -m 0600 "$ENV_BACKUP" /opt/solarsage-astro/.env
   ```

5. Перезапустить только `solarsage-api.service`.
6. Доказать local/dev health.
7. Не push. Немедленно остановиться и передать архитектору SHA revert commit и причину.

Rollback не считать успешным завершением P0. Это аварийное восстановление доступности.

## 13. Фаза I — неизменность соседних сервисов

Повторить `systemctl show` для:

- `solarsage-sidecar.service`;
- `solarsage-frontend.service`;
- `ductor-astro.service`;
- `nginx.service`.

Их MainPID должны совпасть с pre-restart snapshot. Если PID изменился сам по внешней причине, не скрывать: указать before/after и `NRestarts`, но не перезапускать снова.

## 14. Финальное состояние git

Выполнить:

```bash
cd /opt/solarsage-astro
git branch --show-current
git log -1 --oneline
git status --short
git diff --check
git diff --cached --check
git remote -v
```

Требования:

- всё ещё `fix/backend-p0-security-hardening`;
- HEAD = `P0_COMMIT`;
- accepted code/docs clean;
- нет staged изменений;
- допустимы только frozen untracked paths;
- remote не изменён;
- commit не отправлен (`git status -sb`/upstream divergence сообщить без push).

Не выполнять push даже если branch ahead.

## 15. Формат handoff-отчёта кодера

После завершения остановиться и прислать архитектору один компактный отчёт:

```text
R5 RESULT: PASS | FAIL | ROLLED_BACK

Git:
- branch:
- previous HEAD:
- P0 commit SHA:
- commit message:
- pushed: no
- unexpected tracked/untracked files: none | list

Preflight:
- targeted pytest:
- ruff:
- logging guardrails:
- diff check:
- startup_preflight:

Runtime config (nonsecret only):
- APP_ENV=staging
- GRACE_ENV=staging
- APP_DOMAIN=dev.astro.vasiliy-ivanov.ru
- CORS origin count=2
- DEV_MODE=false
- SESSION_COOKIE_SECURE=true
- DATABASE_URL present length=N
- TELEGRAM_BOT_TOKEN present length=N
- GRACE_USER_SALT present length=N, unchanged=yes
- .env mode/owner:
- .env.production mode/owner:
- ENV_BACKUP path:

Service:
- OLD_MAIN_PID:
- NEW_MAIN_PID:
- active/substate:
- NRestarts stable:
- listener 127.0.0.1:8000:
- neighbor service PIDs unchanged:

Health:
- local status/keys/git_sha:
- dev HTTPS status/keys/git_sha:
- test HTTPS status/keys/git_sha:

Public surface:
- four local route statuses:
- four dev route statuses:
- OpenAPI forbidden path count local/dev:

CORS matrix:
- compact table for dev/test/evil/trick origins, GET+OPTIONS

Logging privacy:
- request raw correlation present in response/journal: no/no
- response correlation regex: pass
- opaque correlation observed in journal: yes
- /api/_log result:
- each raw canary journal count: 0
- synthetic probe marker observed: yes
- GRACE env observed: staging

Journal:
- restart loop: no
- traceback count:
- safe error summary:

Rollback:
- used: no | yes + reason/revert SHA
```

Не вставлять в handoff:

- содержимое `.env`;
- URL с credentials;
- token/salt/cookie/initData;
- полные строки journal с пользовательскими данными;
- raw canary UUID целиком — только labels и counts.

## 16. Критерий готовности

Работа считается готовой только одновременно при выполнении всех условий:

- локальный P0 commit создан на правильной ветке и не pushed;
- staging env валиден, secrets сохранены и закрыты mode 600;
- API active/running после единственного systemd restart;
- health local+dev 200 и SHA совпадает с commit;
- внутренние routes дают 404 и отсутствуют из OpenAPI;
- allowed CORS exact, forbidden CORS без ACAO;
- request correlation opaque;
- все raw logging canary имеют journal count 0;
- соседние сервисы не перезапущены;
- working tree чист по принятому набору;
- кодер остановился и ждёт архитектурного ревью.

Даже при полном PASS не выполнять push и не продолжать следующую задачу.
