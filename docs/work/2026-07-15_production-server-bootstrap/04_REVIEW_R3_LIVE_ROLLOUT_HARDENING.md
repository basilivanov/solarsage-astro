# Review R3 — hardening after the live production rollout

Дата: 2026-07-15

Продакшен уже поднят на `astro.vasiliy-ivanov.ru`, TLS и все три runtime-сервиса работают. Во время реального запуска обнаружены три точечных инфраструктурных дефекта. Исправить только их, без рефакторинга соседнего кода.

## Границы задачи

Разрешено менять только:

```text
scripts/prod-deploy.sh
infra/production/docker-compose.yml
.github/workflows/visual-regression.yml
```

Нельзя:

- менять API, frontend product code, systemd, nginx, миграции и production env;
- выполнять server mutations;
- делать commit или push;
- добавлять новые npm/pnpm dependencies;
- трогать frozen untracked paths: `.grace/`, `artifacts/design/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, `skills/`.

## 1. Исправить ложный skip HTTPS smoke

Файл: `scripts/prod-deploy.sh`, блок `https-smoke`.

### Проблема

Скрипт запускается пользователем `astro`, а директория `/etc/letsencrypt/live/...` закрыта для чтения/статирования обычным пользователем. Поэтому проверка:

```bash
[ -f /etc/letsencrypt/live/astro.vasiliy-ivanov.ru/fullchain.pem ]
```

возвращает false даже при исправном сертификате и рабочем HTTPS. В результате production smoke ошибочно пропускается.

### Требуемая реализация

Полностью убрать проверку наличия файла сертификата и ветку `HTTPS smoke skipped`.

На стадии `https-smoke` всегда проверять публичный production endpoint:

```text
https://astro.vasiliy-ivanov.ru/api/health
```

Требования к `curl`:

- обычная TLS verification, без `-k` / `--insecure`;
- `--connect-timeout 5`;
- `--max-time 15`;
- HTTP error должен давать non-zero (`-f`);
- тело ответа не печатать;
- при успехе вывести `HTTPS public endpoint is healthy.`;
- при ошибке вывести понятную ошибку в stderr и завершить deploy non-zero.

Не определять готовность HTTPS через чтение `/etc/letsencrypt`, `sudo`, `ss`, `netstat` или локальный порт: нужен именно end-to-end запрос через публичный домен, Nginx и валидную цепочку сертификата.

## 2. Ограничить Docker json-file logs PostgreSQL

Файл: `infra/production/docker-compose.yml`, service `db`.

Добавить штатную ротацию Docker-логов:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

Сохранить все существующие security, healthcheck, loopback bind, volume и restart настройки без изменений. Не менять имя контейнера и volume.

## 3. Убрать динамический `npx wait-on` из visual workflow

Файл: `.github/workflows/visual-regression.yml`, step `Wait for server`.

### Проблема

`npx wait-on` может скачать пакет, которого нет в lockfile. Это ухудшает воспроизводимость CI, тратит compute minutes и добавляет supply-chain/network dependency.

### Требуемая реализация

Заменить step на bounded bash/curl loop без новых dependencies:

- максимум 120 попыток;
- пауза 1 секунда;
- URL `http://127.0.0.1:3002/`;
- `curl -fsS` и подавление body;
- при успехе вывести короткое подтверждение и завершить step с кодом 0;
- после 120 неудач вывести ошибку в stderr и завершить step с кодом 1;
- не использовать бесконечный цикл;
- не использовать `npx`, `pnpm dlx`, `wait-on`, `sleep` длиннее 1 секунды.

Не менять manual-only trigger, Playwright install/run, artifact upload и порт 3002.

## Обязательная проверка

Выполнить из `/opt/solarsage-astro`:

```bash
bash -n scripts/prod-deploy.sh scripts/prod-backup.sh
POSTGRES_USER=astro POSTGRES_PASSWORD=dummy POSTGRES_DB=astro \
  docker compose -f infra/production/docker-compose.yml config >/tmp/solarsage-prod-compose-r3.yml
python3 - <<'PY'
from pathlib import Path
import yaml

for path in (
    Path('.github/workflows/visual-regression.yml'),
    Path('.github/workflows/deploy-production.yml'),
):
    yaml.safe_load(path.read_text())
    print(f'yaml_ok: {path}')
PY
git diff --check
git status --short
```

Дополнительно проверить по diff:

- в `prod-deploy.sh` больше нет обращения к `/etc/letsencrypt/live` и строки `HTTPS smoke skipped`;
- в visual workflow больше нет `npx wait-on`;
- compose render содержит `logging`, `max-size: 10m`, `max-file: "3"` для `db`;
- изменены только три разрешённых файла.

## Handoff

Вернуть архитектору:

1. краткое описание трёх изменений;
2. exact список изменённых файлов;
3. результаты всех проверок;
4. `git diff --stat`;
5. подтверждение, что commit/push/server mutations не выполнялись.

После handoff остановиться.
