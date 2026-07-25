# ТЗ 01 — Bugsink infra: compose-проект + systemd unit + документация

Дата: 2026-07-24
Master-план: `docs/work/2026-07-24_prod-error-loop/00_TZ.md` (Slice 1)
Кодер: НИЧЕГО НЕ КОММИТИТЬ и не пушить — коммит делает ревьюер.

## Цель

Один наблюдаемый результат: в репо появляется готовый к установке на прод
compose-проект Bugsink (self-hosted error tracker) + systemd unit + записи в
документации. `docker compose config` для нового файла проходит.

## Контекст

- Bugsink — self-hosted трекер ошибок (Sentry-SDK совместимый), образ
  `bugsink/bugsink`. Живёт на прод-хосте отдельным compose-проектом
  `solarsage-bugsink`, НЕ внутри `infra/production/docker-compose.app.yml`
  (там invariant «только immutable per-SHA app-образы»).
- API-контейнер будет слать события на `http://bugsink:8000` — поэтому Bugsink
  подключается к существующей сети `solarsage-app_app` как external.
- UI смотрим только через SSH-туннель → порт публикуем только на loopback.
- Стиль compose-файлов и заголовков — как в
  `infra/production/docker-compose.app.yml` (AI_HEADER + MODULE_CONTRACT/MAP,
  комментарии `#`). Стиль systemd unit — как `infra/systemd/solarsage-db.service`.

## Разрешённые файлы

1. `infra/production/docker-compose.bugsink.yml` — СОЗДАТЬ
2. `infra/systemd/solarsage-bugsink.service` — СОЗДАТЬ
3. `AGENTS.md` — добавить строки (см. ниже)
4. `docs/PRODUCTION_RUNBOOK.md` — добавить раздел (см. ниже)

Не трогать: `docker-compose.app.yml`, `docker-compose.yml`, любой код
apps/api, фронтенд. Никаких других файлов.

## Требования

### 1. `infra/production/docker-compose.bugsink.yml`

- GRACE-заголовок (AI_HEADER + START/END_MODULE_CONTRACT + START/END_MODULE_MAP)
  по образцу `docker-compose.app.yml`.
- `name: solarsage-bugsink`
- service `bugsink`:
  - `image: bugsink/bugsink:2.5.0` (pinned, НЕ latest)
  - `container_name: solarsage-bugsink`
  - `restart: unless-stopped`
  - environment:
    - `SECRET_KEY: ${BUGSINK_SECRET_KEY:?bugsink secret key required}`
    - `CREATE_SUPERUSER: ${BUGSINK_SUPERUSER:-}` (нужен только при первом старте;
      комментарий: после создания админа очистить в env-файле)
    - `PORT: "8000"`
    - `ALLOWED_HOSTS: 127.0.0.1,localhost,bugsink`
  - `volumes`: `bugsink-data:/data` (named volume, SQLite живёт в /data)
  - `ports`: `127.0.0.1:18095:8000`
  - `networks`: `app` (см. ниже) с `aliases: [bugsink]`
  - `logging`: json-file `max-size: "10m"`, `max-file: "3"`
  - `security_opt: [no-new-privileges:true]`
- `networks`: `app:` → `external: true`, `name: solarsage-app_app`
- `volumes`: `bugsink-data:` (без внешних опций)
- В contract: outputs `bugsink on 127.0.0.1:18095 (UI via SSH tunnel)` и
  `http://bugsink:8000 inside solarsage-app_app`; invariant — loopback-only
  publish, no secrets in file.

### 2. `infra/systemd/solarsage-bugsink.service`

По образцу `infra/systemd/solarsage-db.service` (прочитать его и повторить
структуру): `Description`, `Requires=docker.service`, `After=docker.service`,
`Type=oneshot`, `RemainAfterExit=yes`, `WorkingDirectory` — директория, куда на
проде будет установлен файл (по аналогии с db unit; если там
`/etc/solarsage/compose`, использовать её же), `ExecStart=/usr/bin/docker compose
-f docker-compose.bugsink.yml -p solarsage-bugsink up -d`, `ExecStop=... down`,
`TimeoutStartSec`, `[Install] WantedBy=multi-user.target`. Env-файл с секретами:
`EnvironmentFile=/etc/solarsage/bugsink.env` (root:astro 0640, создаёт
оператор — отразить в runbook).

### 3. `AGENTS.md`

- В таблицу «Production sidecar» (или рядом, отдельной строкой) добавить:
  порт **18095** — SolarSage Bugsink — контейнер `solarsage-bugsink`
  (Compose `solarsage-bugsink`) — трекер ошибок фронта/API, UI только по
  SSH-туннелю, loopback.
- В таблицу «Что где лежит на проде» добавить строку: Bugsink compose —
  `/etc/solarsage/compose/docker-compose.bugsink.yml`, env —
  `/etc/solarsage/bugsink.env`, данные — docker volume `bugsink-data`.
- В список контейнеров на проде добавить `solarsage-bugsink`.

### 4. `docs/PRODUCTION_RUNBOOK.md`

Новый раздел «Error tracking (Bugsink)» (разместить рядом с разделами про
прод-инфраструктуру, стиль заголовков как у соседних разделов):

- Что это: self-hosted трекер ошибок фронта и API; события шлются из API
  (`ERROR_TRACKING_DSN`), UI только по SSH-туннелю.
- Установка (operator steps):
  1. Скопировать `infra/production/docker-compose.bugsink.yml` на прод в
     `/etc/solarsage/compose/`, unit — в `/etc/systemd/system/`
  2. Создать `/etc/solarsage/bugsink.env` (root:astro 0640) с
     `BUGSINK_SECRET_KEY=<случайные 50+ символов>` и на первый старт
     `BUGSINK_SUPERUSER=admin@example.org:<пароль>` (после создания админа —
     удалить строку и restart)
  3. `systemctl daemon-reload && systemctl enable --now solarsage-bugsink`
  4. Туннель с локальной машины:
     `ssh -L 18095:127.0.0.1:18095 root@2.26.20.80 -i ~/.ssh/solarsage_prod_server_ed25519`
     → http://127.0.0.1:18095 → логин → создать проект `solarsage` →
     получить DSN вида `http://<key>@bugsink:8000/<project_id>`
  5. В `/etc/solarsage/app.env` добавить
     `ERROR_TRACKING_DSN=http://<key>@bugsink:8000/<project_id>`
     (вступит в силу со следующим деплоем app-стека; сейчас переменная ещё не
     используется кодом — приедет со Slice 2)
  6. Для авто-триажа: в UI создать API token (Settings → API tokens) —
     понадобится для `scripts/prod-errors/` (Slice 3)
- Проверка: `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:18095/`
  → 200; из api-контейнера: `docker exec solarsage-api python -c
  "import urllib.request; print(urllib.request.urlopen('http://bugsink:8000/', timeout=3).status)"`
- Примечание: compose требует существующей сети `solarsage-app_app`
  (создаётся app-стеком). Если app-стек даун — сначала поднять его.

## Критерии приёмки

1. `docker compose -f infra/production/docker-compose.bugsink.yml -p solarsage-bugsink config` проходит (с подставленными dummy `BUGSINK_SECRET_KEY=x`)
2. В файле нет секретов, порт опубликован только на 127.0.0.1, image pinned `2.5.0`
3. systemd unit синтаксически валиден (`systemd-analyze verify` если доступен, иначе визуально по образцу db unit)
4. AGENTS.md и PRODUCTION_RUNBOOK.md содержат новые записи, стиль совпадает с соседними

## Проверка (одна команда)

```bash
cd /opt/solarsage-astro && BUGSINK_SECRET_KEY=dummy BUGSINK_SUPERUSER= docker compose -f infra/production/docker-compose.bugsink.yml -p solarsage-bugsink config --quiet && echo OK
```

## Отчёт кодера

Коротко: созданные/изменённые файлы, вывод команды проверки, замеченные
соседние проблемы (если есть). Напоминание: не коммитить.
