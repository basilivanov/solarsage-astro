# Review R1 — runtime blockers перед production rollout

Дата: 2026-07-15

Основная структура change-set принята, но rollout запрещён до исправления перечисленных дефектов.

Исправлять только новые/изменённые production deployment files текущей ветки. Никаких server mutations, commit или push.

## 1. Critical: `.env.production` sourced, но не exported

В `scripts/prod-deploy.sh` сейчас:

```bash
source .env.production
```

Shell variables после этого не попадают в `pnpm build`, Python preflight, Alembic и child processes, если строки env не содержат `export`.

Исправить:

```bash
set -a
# shellcheck source=/dev/null
source .env.production
set +a
```

`set +x` оставить до source. Не печатать значения.

В `scripts/prod-backup.sh` явный `PGPASSWORD` экспорт уже покрывает `pg_dump`, но для единообразного truthful contract также использовать `set -a/source/set +a`.

Добавить локальный regression/static check в script self-validation или отдельную shell-проверку, чтобы deploy script содержал `set -a` до source.

## 2. Critical: Alembic запускается из неверного cwd

Фактическая проверка архитектора:

```text
из repository root:
PYTHONPATH=apps/api apps/api/.venv/bin/alembic -c apps/api/alembic.ini heads
-> FAILED: Path doesn't exist: alembic

из apps/api:
.venv/bin/alembic -c alembic.ini heads
-> PASS, head 0019
```

Причина: `script_location = alembic` относителен к cwd.

В deploy script выполнять migration/current/heads в subshell:

```bash
(
  cd apps/api
  .venv/bin/alembic -c alembic.ini upgrade head
  .venv/bin/alembic -c alembic.ini current
  .venv/bin/alembic -c alembic.ini heads
)
```

Не использовать root-relative `-c apps/api/alembic.ini`.

Исправить те же команды в `docs/PRODUCTION_RUNBOOK.md`.

## 3. Critical: pre-migration backup нельзя молча пропускать

Deploy script проверяет DB через `nc`, но Netcat не входит в установленный/задокументированный production dependency set. На чистом сервере backup будет всегда skipped.

Использовать установленный PostgreSQL client:

```bash
pg_isready -h 127.0.0.1 -p 5433 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

Policy:

- перед каждой migration DB обязана быть reachable;
- если `pg_isready` не PASS — deploy завершается ошибкой;
- если reachable — `scripts/prod-backup.sh` обязателен;
- backup failure блокирует migration;
- не писать «skipping backup» для routine/initial deploy: пустая новая DB также может быть корректно дампнута после инициализации контейнера.

В backup script добавить:

```bash
trap 'unset PGPASSWORD' EXIT
```

И удалять partial dump/checksum при failure через аккуратный trap либо явный cleanup, чтобы повреждённый файл не выглядел валидным backup.

## 4. Critical: bot username env key неверный

Repository/runtime использует:

```text
BOT_USERNAME
```

Сейчас deploy preflight и runbook используют `TELEGRAM_BOT_USERNAME`, которого нет в production contract.

Исправить везде на `BOT_USERNAME`.

Preflight должен обязательно требовать значение и проверять normalized username:

```python
bot_username = os.environ.get("BOT_USERNAME", "").strip().lstrip("@")
assert bot_username == "AstroGrace_Bot"
```

Не делать проверку optional.

## 5. Env file permissions check неверен как policy

Числовое сравнение decimal modes:

```bash
if [ "$PERMS" -gt 640 ]
```

не является корректной проверкой permission bits (`604` меньше `640`, но world-readable).

Для этого deployment contract разрешить только:

```text
600
640
```

Любой другой mode — fail. Дополнительно проверить owner/group:

```text
owner: astro
group: astro
```

Сообщение не должно печатать содержимое файла.

## 6. Nginx ACME location сейчас перекрывается dotfile regex

Regex:

```nginx
location ~ /\. {
    deny all;
}
```

может перехватить `/.well-known/acme-challenge/` после prefix match.

Оба ACME location сделать:

```nginx
location ^~ /.well-known/acme-challenge/ {
    root /var/www/html;
    allow all;
}
```

Dotfile deny оставить для остальных путей.

Убрать `preload` и `includeSubDomains` из HSTS для первого production launch. Использовать консервативно:

```nginx
Strict-Transport-Security "max-age=31536000"
```

Не включать preload до отдельного доменного аудита.

Если используются стандартные Certbot option files, включить их только там, где файл гарантирован после issuance; не создавать конфиг, который нельзя проверить до сертификата.

## 7. HTTPS smoke не должен использовать `-k`

В `scripts/prod-deploy.sh` удалить `curl -k`.

Policy:

- если certificate/fullchain path ещё отсутствует во время initial pre-TLS bootstrap — вывести truthful `HTTPS smoke skipped: certificate not installed`;
- если certificate существует — обычный `curl -fsS`, с полной TLS verification;
- invalid/expired/mismatched certificate должен валить smoke, а не скрываться `-k`.

## 8. Visual regression workflow слушает не тот порт

Workflow ждёт `http://localhost:3002`, но запускает `pnpm run start`, который по умолчанию слушает 3000.

Запускать явно:

```bash
pnpm exec next start -H 127.0.0.1 -p 3002 &
```

Использовать `pnpm exec playwright`, а не `npx`, чтобы не было скрытой установки/версии вне lockfile.

Исправить malformed header line:

```text
# #################################################################-----------
```

на нормальный separator, согласованный с остальными workflow files.

## 9. GitHub deploy workflow: только forced-command transport

Workflow сейчас:

- делает ненужный checkout;
- пишет ED25519 key в `id_rsa` через `echo`;
- отправляет произвольную remote command строку.

Исправить:

- убрать `actions/checkout`: deployment job только вызывает server-side forced command;
- файл назвать `~/.ssh/solarsage_prod_deploy`;
- создать через `install -m 600 /dev/null ...`;
- писать secret через `printf '%s\n'`, не `echo`;
- убрать CR на концах безопасным способом, если GitHub secret multiline получает Windows line endings;
- SSH вызывать с `-i`, `IdentitiesOnly=yes`, `BatchMode=yes`, `StrictHostKeyChecking=yes`;
- не передавать shell command. Вызов должен только открыть transport, а authorized key forced command запускает root-owned deployment entrypoint;
- cleanup удаляет key и при необходимости known_hosts, без вывода.

Пример intent:

```bash
ssh -T \
  -i ~/.ssh/solarsage_prod_deploy \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=yes \
  "${PROD_USER}@${PROD_HOST}"
```

Не добавлять `StrictHostKeyChecking=no`.

## 10. Systemd boot ordering

Усилить truthful dependencies:

- sidecar: `After=Wants=network-online.target`;
- API: `After=network-online.target docker.service solarsage-sidecar.service`, `Wants=network-online.target solarsage-sidecar.service`, `Requires=docker.service`;
- frontend: `After=network-online.target solarsage-api.service`, `Wants=network-online.target solarsage-api.service`;
- backup service: `After=docker.service`, `Requires=docker.service`.

Не привязывать API к несуществующему systemd unit контейнера. Docker restart policy поднимет `solarsage-db`; API `Restart=on-failure` переживёт короткое окно его health startup.

Backup service добавить:

```text
UMask=0077
PrivateTmp=true
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=full
ReadWritePaths=/var/backups/solarsage
```

Убедиться, что это не мешает чтению `/opt/solarsage-astro/.env.production` и запуску host `pg_dump`.

## 11. Runbook exactness

Исправить:

- DB table: host address `127.0.0.1:5433`; container internal `5432` пояснить отдельно;
- `POSTGRES_USER` не фиксировать на выдуманный `solarsage_admin`; production bootstrap использует out-of-band value, docs перечисляет key names;
- `TELEGRAM_BOT_USERNAME` -> `BOT_USERNAME`;
- добавить обязательные deployed validation keys:
  - `CORS_ALLOWED_ORIGINS`;
  - `GRACE_USER_SALT`;
  - `SESSION_COOKIE_SECURE`;
  - `DEV_MODE`;
  - `SOLARSAGE_URL`;
  - `LLM_PROVIDER`, `LLM_MODEL`, `LLM_MAX_TOKENS`;
  - V2 flags names;
- не показывать строки `KEY=SECURE_*` как будто это готовый env; дать список names + meaning;
- migration commands выполнять из `apps/api`;
- Telegram раздел явно говорит: Bot API настраивает description/commands/menu, avatar загружается вручную через BotFather; Ductor отсутствует;
- initial Nginx flow: temporary HTTP ACME config -> certificate issuance -> canonical TLS config -> `nginx -t` -> reload;
- branch/private repo note: Actions deploy нельзя включать до того, как production change окажется в `origin/main`.

## 12. Docker Compose cleanup

Убрать obsolete top-level:

```yaml
version: '3.8'
```

Compose v2/v5 использует current Compose Specification и иначе печатает warning.

Остальную DB topology не менять.

## 13. Argument and failure hygiene

Deploy script должен принимать только:

```text
no args
--current
```

Любой другой аргумент -> usage + exit 2.

На любом failure итог должен показывать stage и target/old SHA без secrets. Использовать простой `trap` с текущим stage label; не делать ложный automatic rollback после Alembic.

## 14. Repeat gates

После исправлений:

```bash
bash -n scripts/prod-deploy.sh scripts/prod-backup.sh
git diff --check

POSTGRES_USER=astro POSTGRES_PASSWORD=dummy POSTGRES_DB=astro \
docker compose -f infra/production/docker-compose.yml config >/tmp/prod-compose.yml

PYTHONPATH=apps/api apps/api/.venv/bin/python - <<'PY'
from pathlib import Path
s = Path('scripts/prod-deploy.sh').read_text()
assert 'set -a' in s
assert 'BOT_USERNAME' in s
assert 'TELEGRAM_BOT_USERNAME' not in s
assert 'nc -z' not in s
assert 'curl -k' not in s
assert 'cd apps/api' in s
PY

rg -n 'TELEGRAM_BOT_USERNAME|curl -k|nc -z|StrictHostKeyChecking=no|pnpm run start &' \
  scripts/prod-*.sh docs/PRODUCTION_RUNBOOK.md .github/workflows infra/nginx
```

Ожидается пустой forbidden output.

Также повторить guardrails из `00_TZ.md` и targeted `test_health.py`.

## 15. Handoff

Commit/push/server mutation запрещены.

Вернуть `PRODUCTION_BOOTSTRAP_CODE R1: READY_FOR_REVIEW | FAIL` с перечислением исправленных пунктов и exact gate results. После handoff остановиться.
