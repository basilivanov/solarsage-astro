# Review R4 — make local PostgreSQL runtime explicit under systemd hardening

Дата: 2026-07-15

## Контекст production smoke

Энд-то-энд запрос к `POST /api/auth/telegram` с корректным HMAC вернул HTTP 500. Безопасный journal traceback показал:

```text
PermissionError: [Errno 13] Permission denied: '/home/astro/.postgresql/postgresql.key'
```

Причина: API запущен с `ProtectHome=true`, а asyncpg при неопределённом SSL-режиме пытается проверить пользовательский PostgreSQL client key. База PostgreSQL находится на loopback `127.0.0.1:5433` в Docker и не требует TLS между API и DB.

На сервере временно проверен workaround `PGSSLMODE=disable` в `.env.production`; после него реальный Telegram HMAC smoke полностью зелёный. Теперь это должно стать частью репозитория, чтобы чистый bootstrap не требовал ручного исправления.

## Границы

Разрешено менять только:

```text
infra/systemd/solarsage-api.service
docs/PRODUCTION_RUNBOOK.md
```

Не менять API-код, DATABASE_URL, Docker, nginx, frontend, миграции, секреты и другие systemd units. Commit/push/server mutations запрещены. Frozen paths не трогать.

## Требуемое изменение

В `[Service]` файла `infra/systemd/solarsage-api.service` добавить явное окружение:

```ini
Environment="PGSSLMODE=disable"
```

Разместить рядом с `EnvironmentFile`, с понятным комментарием о loopback PostgreSQL и `ProtectHome=true`. Не добавлять credentials и не печатать `.env.production`.

Обновить `docs/PRODUCTION_RUNBOOK.md` в разделе database/runtime:

- указать, что production PostgreSQL доступен только через loopback `127.0.0.1:5433`;
- зафиксировать, что API unit явно задаёт `PGSSLMODE=disable`, потому что TLS между локальным API и локальным DB не используется, а systemd `ProtectHome=true` запрещает asyncpg искать пользовательские client certificates;
- предупредить, что эту настройку нельзя заменять ослаблением `ProtectHome` или публикацией DB наружу.

## Проверки

Из корня репозитория:

```bash
systemd-analyze verify infra/systemd/solarsage-api.service
git diff --check
git status --short
```

Проверить diff вручную:

- изменены ровно два разрешённых файла;
- нет секретов, токенов, `DATABASE_URL` и ослабления hardening;
- `ProtectHome=true` сохранён;
- присутствует ровно один `PGSSLMODE=disable` в API unit.

Вернуть handoff с exact списком файлов, результатами проверок и подтверждением отсутствия commit/push/server mutations. После handoff остановиться.
