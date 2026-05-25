---
id: doc-deploy
status: stale
wave: W-1.0
last_review: 2026-05-25
---
# DEPLOY.md — развёртывание Astro Mini App на VDS

> **STATUS: stale (pre-W-1.0).** This document predates the
> Phase-1 stack lockdown and references services/env-vars that no
> longer match the canon (SolarSage sidecar, systemd units
> `astro-api`/`astro-worker`/`astro-web`, `apps/web/` layout,
> `/opt/solarsage-astro` VDS model, `SOLARSAGE_*` env-vars without
> canonical prefix, etc.). The authoritative deployment surface
> will be re-derived in a dedicated **W-DEPLOY** wave (TBD,
> post-W-1.5). Do not use as a runbook. Retained for product-history
> context only; see `grace/development-plan.xml` (`<future-waves>`
> → `W-DEPLOY`) for the tracking anchor.

Документ — пошаговое ТЗ. Каждая команда выполняется именно в указанном
порядке. Если шаг падает — не идти дальше, а чинить шаг.

**Папка проекта на VDS:** `/opt/solarsage-astro` (владелец — пользователь `astro`).
**nginx уже установлен и настроен** на сервере — этот гайд его не переустанавливает
и не подкладывает конфиги. Админ сервера сам добавит проксирование на наши
upstream-порты (`127.0.0.1:3000` и `127.0.0.1:8000`). Пример server-block —
в шаге 7 ниже, чисто как подсказка.

---

## 0. Что должно быть в наличии

- VDS:
  - Ubuntu 22.04 LTS или 24.04 LTS;
  - ≥ 2 vCPU, ≥ 4 GB RAM, ≥ 40 GB SSD;
  - публичный IPv4;
  - root-доступ по SSH-ключу;
  - **nginx уже стоит, работает и сам терминирует TLS** на нужном домене.
- Домен (`astro.example.com`), A-запись на IP VDS, SSL уже выписан админом
  сервера (certbot / Cloudflare / другой issuer — на усмотрение админа).
- Telegram бот (`BOT_TOKEN` от @BotFather).
- LLM API key.
- (Опц.) GitHub-репо с этим монорепо и deploy-key.

---

## 1. Bootstrap VDS (root, ~3 мин)

```bash
ssh root@VDS_IP
apt update && apt -y upgrade
# скачай или scp-ни bootstrap-vds.sh из репо
bash /tmp/bootstrap-vds.sh
```

Скрипт:
- ставит `git`, `build-essential`, `python3.12`, `nodejs 20`, `pnpm`,
  `postgresql-16`, `redis-server` (nginx **не трогает**);
- создаёт пользователя `astro`, копирует ему SSH-ключи;
- создаёт `/opt/solarsage-astro` с владельцем `astro:astro`;
- 2 GB swap; ufw 22/80/443; запрещает root-логин.

Дальше всё — под `astro`:
```bash
sudo -iu astro
```

## 2. Получить код в /opt/solarsage-astro

Вариант А — git:
```bash
ssh-keygen -t ed25519 -C "astro@$(hostname)" -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub        # → Deploy Key в GitHub
git clone git@github.com:<you>/astro.git /opt/solarsage-astro
```

Вариант Б — scp/rsync с локальной машины (если репо ещё не публичный):
```bash
# на локали
rsync -av --exclude node_modules --exclude .venv --exclude .next \
  ./astro/  astro@VDS:/opt/solarsage-astro/
```

Затем:
```bash
cd /opt/solarsage-astro
cp .env.example .env
nano .env
```

Особо проверить:
- `APP_DOMAIN` совпадает с реальным;
- `POSTGRES_PASSWORD`, `APP_SECRET`, `SOLARSAGE_API_KEY` — `openssl rand -hex 32`;
- `TELEGRAM_BOT_TOKEN`, `LLM_API_KEY` — рабочие.

## 3. Postgres

```bash
make db-create
PGPASSWORD=$POSTGRES_PASSWORD psql -h 127.0.0.1 -U astro -d astro -c '\conninfo'
```

## 4. SolarSage sidecar

Слушает только `127.0.0.1:18091`, наружу не торчит.

```bash
cd /opt/solarsage-astro/apps/solarsage
make install        # создаёт .venv в этой же папке, ставит pyswisseph
make run            # smoke-тест: на 18091 должен подняться сервис
# Ctrl+C, потом systemd:
sudo cp /opt/solarsage-astro/infra/systemd/solarsage.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now solarsage
curl -s -H "X-API-Key: $SOLARSAGE_API_KEY" http://127.0.0.1:18091/v1/health
```

## 5. Backend (FastAPI + worker)

```bash
cd /opt/solarsage-astro/apps/api
make install        # python -m venv .venv && pip install -e .
make migrate        # alembic upgrade head
sudo cp /opt/solarsage-astro/infra/systemd/astro-api.service    /etc/systemd/system/
sudo cp /opt/solarsage-astro/infra/systemd/astro-worker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now astro-api astro-worker
curl -s http://127.0.0.1:8000/health
```

## 6. Frontend (Next.js)

```bash
cd /opt/solarsage-astro/apps/web
pnpm install --frozen-lockfile
pnpm build
sudo cp /opt/solarsage-astro/infra/systemd/astro-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now astro-web
curl -s http://127.0.0.1:3000 | head -n 5
```

## 7. Reverse proxy (nginx уже стоит на VDS)

Репозиторий nginx-ом **не управляет**. Этот шаг делает админ сервера
руками — кладёт site-конфиг, делает `nginx -t && systemctl reload nginx`.
SSL уже у админа выписан (certbot / Cloudflare / свой issuer) — мы в это
не лезем.

Минимально нужно прокинуть в уже существующий `server { listen 443 ssl … }`
для нашего домена два location-блока:

```nginx
# === Astro Mini App upstreams ===
upstream astro_web { server 127.0.0.1:3000; keepalive 32; }
upstream astro_api { server 127.0.0.1:8000; keepalive 32; }

# внутри server { listen 443 ssl …; server_name astro.example.com; }
client_max_body_size 5m;

location /api/ {
    proxy_pass         http://astro_api;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_read_timeout 60s;
}

location / {
    proxy_pass         http://astro_web;
    proxy_http_version 1.1;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header   X-Forwarded-Proto $scheme;
    proxy_set_header   Upgrade           $http_upgrade;
    proxy_set_header   Connection        "upgrade";
}
```

Что важно:
- `/api/` уходит на FastAPI, всё остальное — на Next.js;
- никаких новых `listen 80/443` блоков от нас не нужно — врезаемся в уже
  существующий server-block по нашему домену;
- HTTP→HTTPS редирект и SSL-сертификаты — на стороне админа, мы их не
  переоформляем;
- `nginx -t && systemctl reload nginx` (НЕ restart — другие сайты не
  должны падать).

## 8. Telegram Mini App

В @BotFather:
- `/mybots → <bot> → Bot Settings → Configure Mini App → Edit Mini App URL`
  → `https://$APP_DOMAIN/`.

Webhook (если нужен):
```bash
curl -F "url=https://$APP_DOMAIN/api/telegram/webhook" \
     -F "secret_token=$TELEGRAM_WEBHOOK_SECRET" \
     "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook"
```

## 9. Smoke-тест

```bash
curl -s https://$APP_DOMAIN/api/health
curl -s https://$APP_DOMAIN/api/day/2026-05-24 -H 'X-Tg-Init-Data: dev'
```

Открыть Mini App в Telegram → Today screen с mock-данными (`apps/api`
сейчас отдаёт fixture `TodayPayload` — это нормально, см. фазы в
`docs/07_Backend_architecture_draft.md`).

## 10. Бэкапы

```bash
sudo cp /opt/solarsage-astro/infra/systemd/astro-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now astro-backup.timer
sudo systemctl list-timers astro-backup.timer
```

Дампы лежат в `/var/backups/astro` (создаётся `backup.sh`-ом, ротация 14 дней).

Логи:
```bash
sudo journalctl -fu astro-api
sudo journalctl -fu astro-worker
sudo journalctl -fu astro-web
sudo journalctl -fu solarsage
```

## 11. Дальнейшие деплои

```bash
ssh astro@VDS
cd /opt/solarsage-astro
make deploy           # git pull + build + systemctl restart
```

---

## Перенос на другой VDS

```bash
# на старом VDS
make backup
scp /var/backups/astro/db-*.dump newvds:/tmp/

# на новом VDS — пройти шаги 1–7 (тот же .env)
PGPASSWORD=$POSTGRES_PASSWORD pg_restore \
  -h 127.0.0.1 -U astro -d astro --clean --if-exists /tmp/db-*.dump
sudo systemctl restart astro-api astro-worker astro-web
# обновить A-запись домена → новый IP
```

Никаких разбросанных скриптов: всё, что нужно для переезда — этот
репозиторий + один `.env` + один dump.
