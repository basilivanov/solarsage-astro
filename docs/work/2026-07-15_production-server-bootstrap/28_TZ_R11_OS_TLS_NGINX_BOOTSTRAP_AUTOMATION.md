# R11 — автоматизация базовой ОС, TLS/ACME и защитного Nginx

## Роль и режим работы

Ты кодер. Реализуй ровно описанный ниже production-infra slice. Архитектор отдельно проведёт ревью и сам решит, когда применять изменения на сервере.

Модель для этой задачи: `cliproxy/gemini-3-flash-agent`.

Запрещено:

- делать `commit`, `push`, merge или checkout другой ветки;
- подключаться к production-серверу;
- запускать `--apply`/выдачу сертификата на текущей машине;
- стартовать, останавливать или рестартовать `solarsage-api`, `solarsage-sidecar`, `solarsage-frontend`;
- читать или печатать `.env`, `.env.production`, токены, SSH private keys и другие секреты;
- трогать frozen/unrelated paths: `.grace/`, `artifacts/design/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, `skills/`;
- переписывать прикладной backend/frontend-код — эта задача только про host bootstrap/TLS/Nginx/runbook.

Сохраняй GRACE-разметку (`AI_HEADER`, module contract/map, function contracts для нетривиальных функций). В инфраструктурных shell/nginx-файлах `emitted_logs: none` допустимо.

## Цель

После этой задачи подготовка нового Ubuntu 24.04 production host должна быть воспроизводимой и разделённой на безопасные этапы:

1. root-команда ставит/проверяет системные зависимости и базовые защитные сервисы;
2. отдельная root-команда безопасно получает или принимает существующий Let's Encrypt certificate, устанавливает canonical Nginx и автоматическое renewal/reload;
3. существующий `prod-host-prepare.sh` владеет финальным runtime state и fingerprint;
4. ни одна из этих команд не запускает приложение;
5. первый запуск кода остаётся отдельной, только ручной операцией по команде владельца.

## Канонические значения

- OS: Ubuntu `24.04` (`noble`), только `amd64`;
- user/group: `astro:astro`, home `/home/astro`, shell `/bin/bash`;
- app root: `/opt/solarsage-astro`;
- domain: `astro.vasiliy-ivanov.ru`;
- expected public IPv4: `157.22.192.242`;
- Node.js: major `22`;
- pnpm: exact `10.32.1`;
- Python: `3.12`;
- Docker Compose: plugin form `docker compose`, не legacy `docker-compose`;
- ACME webroot: `/var/www/letsencrypt`;
- certificate: `/etc/letsencrypt/live/astro.vasiliy-ivanov.ru/{fullchain.pem,privkey.pem}`;
- certificate freshness threshold: минимум 14 суток;
- Nginx final site: `/etc/nginx/sites-available/astro.vasiliy-ivanov.ru.conf` + exact symlink in `sites-enabled`;
- default reject: `/etc/nginx/conf.d/00-solarsage-default-reject.conf`;
- Certbot deploy hook: `/etc/letsencrypt/renewal-hooks/deploy/20-solarsage-reload-nginx`.

## Обязательные изменения

### 1. Новый `scripts/prod-os-bootstrap.sh`

Сделай root-only idempotent script с интерфейсом строго:

```text
scripts/prod-os-bootstrap.sh --check
scripts/prod-os-bootstrap.sh --apply
```

Другие аргументы/комбинации должны завершаться с exit `2` и usage. Проверка аргументов идёт до root-check. Далее `set -euo pipefail`, `umask 027`, non-blocking `flock` на `/run/solarsage-os-bootstrap.lock`.

#### `--check` — строго read-only

Не вызывать `apt update`, `apt install`, `systemctl enable/start/restart`, `ufw allow/enable`, `corepack prepare`, запись файлов или создание каталогов.

Агрегировать понятные ошибки и завершаться ненулевым кодом, если нарушен хотя бы один контракт:

- exact Ubuntu 24.04, codename noble, architecture amd64;
- пользователь и группа `astro` существуют; primary group `astro`; home `/home/astro`; shell `/bin/bash`; home — каталог `astro:astro` с mode не шире `0750`;
- команды существуют: `git`, `curl`, `cmp`, `sha256sum`, `python3.12`, `node`, `corepack`, `pnpm`, `docker`, `nginx`, `certbot`, `pg_dump`, `pg_isready`, `systemctl`, `visudo`, `openssl`, `runuser`, `install`, `flock`, `getent`, `stat`, `systemd-analyze`, `ufw`, `fail2ban-client`;
- Node major ровно `22`; pnpm version ровно `10.32.1`; `python3.12 --version` соответствует 3.12;
- `docker compose version` успешен;
- systemd units `docker.service`, `nginx.service`, `fail2ban.service`, `certbot.timer`, `unattended-upgrades.service` существуют, enabled; Docker/Nginx/Fail2ban/timer active, unattended-upgrades active или в допустимом oneshot/exited state;
- `fail2ban-client status sshd` успешен;
- `ufw status` — active; правила разрешают inbound `22/tcp`, `80/tcp`, `443/tcp` для IPv4 и IPv6; default incoming deny, outgoing allow. Не делай хрупкий grep по локализованному выводу: принудительно используй `LC_ALL=C` и проверяй exit/output осознанно;
- NTP synchronized (`timedatectl show -p NTPSynchronized --value` равно `yes`). Не меняй timezone: для этого проекта `Europe/Moscow` допустим.

Не добавляй `astro` в group `docker`: приложению и deploy user не нужен безграничный root-equivalent доступ через Docker socket.

#### `--apply` — системные зависимости, но не приложение

Последовательность должна быть fail-fast и идемпотентной:

1. Проверить OS/codename/arch до первой мутации.
2. Создать system user/group `astro`, только если отсутствует. Если существующая сущность противоречит канону — fail, а не молча переделывать UID/home/shell. Новый пользователь: home `/home/astro`, shell `/bin/bash`, locked password. Не менять существующий пароль.
3. Использовать noninteractive apt (`DEBIAN_FRONTEND=noninteractive`), но не делать full/dist upgrade.
4. Установить базовые Ubuntu packages как минимум: `ca-certificates`, `curl`, `git`, `gnupg`, `openssl`, `sudo`, `nginx`, `certbot`, `python3.12`, `python3.12-venv`, `python3-pip`, `postgresql-client-16`, `fail2ban`, `ufw`, `unattended-upgrades`.
5. Если рабочего Docker + Compose plugin ещё нет, настроить официальный Docker apt repository без `curl | sh`: скачать key во временный root-only файл, проверить непустой файл, atomically install в `/etc/apt/keyrings/docker.asc`, создать canonical source для Ubuntu noble/текущего amd64, затем установить `docker-ce`, `docker-ce-cli`, `containerd.io`, `docker-buildx-plugin`, `docker-compose-plugin`. Уже рабочую инсталляцию Docker не заменять другим package family.
6. Если Node major не 22, настроить NodeSource `node_22.x` без `curl | sh`: key URL `https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key`, dearmor во временный файл, atomically install `/etc/apt/keyrings/nodesource.gpg`, canonical source `https://deb.nodesource.com/node_22.x nodistro main`, затем `apt install nodejs`. Если Node 22 уже рабочий, не переустанавливать без причины.
7. Активировать exact pnpm `10.32.1` через Corepack. После операции обязательно проверять фактический `pnpm --version`; не полагаться только на успешный exit Corepack. Не запускать package-manager из каталога проекта и не менять lockfile.
8. Установить новый repo template `infra/fail2ban/jail.d/solarsage-sshd.local` в `/etc/fail2ban/jail.d/solarsage-sshd.local`, owner root:root, mode 0644. Содержимое:
   - `[sshd]`, `enabled = true`, `backend = systemd`;
   - `maxretry = 5`, `findtime = 10m`, `bantime = 1h`;
   - не переопределять SSH port произвольным значением.
9. UFW: задать default deny incoming/default allow outgoing; идемпотентно разрешить `22/tcp`, `80/tcp`, `443/tcp`; `ufw --force enable`. Не делать `ufw reset` и не удалять неизвестные правила — это может оборвать доступ. После apply `--check` обязан выявить лишний публичный allow как отдельную ошибку/ручное решение, но apply не должен угадывать, что можно удалить.
10. Enable/start только базовые units: Docker, Nginx, Fail2ban, certbot timer, unattended-upgrades. Restart Fail2ban допустим только после успешной проверки его config. Для Nginx до TLS этапа допустим стандартный пакетный default site; приложение не проксировать.
11. Финально выполнить ту же verification-функцию, что использует `--check`.

Не клонируй Git-репозиторий и не создавай `.env.production`: private repository access и секреты — отдельный operator boundary.

### 2. Nginx assets для безопасного ACME bootstrap

Создай `infra/nginx/00-solarsage-default-reject.conf`:

- отдельный HTTP default server на IPv4/IPv6, `server_name _`, `return 444`;
- отдельный HTTPS default server на IPv4/IPv6 с `ssl_reject_handshake on`;
- не использовать production certificate в default server;
- конфиг должен быть совместим с Nginx 1.24 на Ubuntu 24.04.

Создай `infra/nginx/astro-acme-bootstrap.conf`:

- только port 80, exact `server_name astro.vasiliy-ivanov.ru`;
- `location ^~ /.well-known/acme-challenge/` с root `/var/www/letsencrypt`, `try_files $uri =404`, без proxy;
- все остальные URI возвращают `503` и `Retry-After: 60`; до получения сертификата не редиректить на несуществующий HTTPS;
- не добавлять dev/test домены.

Обнови `infra/nginx/astro.vasiliy-ivanov.ru.conf`:

- ACME root в HTTP и HTTPS — `/var/www/letsencrypt`;
- HTTP redirect только на canonical `https://astro.vasiliy-ivanov.ru$request_uri`, не через `$host`;
- сохранить канонические upstream ports: API 8000, frontend 3002;
- сохранить security headers, TLS 1.2/1.3 и текущие bounded proxy timeouts;
- exact host обслуживает только этот server block; unknown Host/SNI забирает default reject;
- dotfile deny не должен перекрывать ACME location (порядок/prefix semantics проверить).

### 3. Certbot deploy hook

Создай executable template `infra/certbot/deploy-hooks/20-solarsage-reload-nginx`:

- `#!/usr/bin/env bash`, `set -euo pipefail`, `umask 027`;
- сначала `/usr/sbin/nginx -t`, затем `/usr/bin/systemctl reload nginx.service`;
- никаких env/secrets/сетевых вызовов;
- owner/mode при установке: root:root 0755;
- `bash -n` должен проходить.

### 4. Новый `scripts/prod-cert-prepare.sh`

Поддержать строго:

```text
scripts/prod-cert-prepare.sh --check
scripts/prod-cert-prepare.sh --apply
scripts/prod-cert-prepare.sh --apply --email operator@example.com
```

- email опционален, если уже есть валидный certificate;
- если certificate отсутствует/невалиден и email не передан — exit 2 до Nginx mutation/certbot call;
- email валидировать консервативно: одна строка, без whitespace/control chars, ровно один `@`, непустые local/domain части. Email не секрет, но не печатай его без необходимости;
- unknown args/duplicate flags/order deviations — exit 2;
- root-only, `set -euo pipefail`, `umask 027`, non-blocking lock `/run/solarsage-cert-prepare.lock`;
- script запускается только из repository checkout, но вычисляет repo root относительно собственного пути, а не cwd.

#### Общий preflight до mutation

- exact OS/codename/arch;
- required repo files существуют как regular files и не являются symlink: оба Nginx config, final Nginx config, deploy hook;
- `nginx`, `certbot`, `openssl`, `curl`, `getent`, `install`, `systemctl`, `cmp`, `readlink`, `mktemp`, `flock` существуют;
- DNS A set для домена после unique/sort равен ровно `157.22.192.242`; не принимай дополнительный неожиданный A record;
- не делать зависимость от внешнего «what is my IP» сервиса;
- валидный certificate = fullchain/key доступны, `openssl x509 -checkend 1209600` успешен, SAN содержит exact `DNS:astro.vasiliy-ivanov.ru`;
- Let's Encrypt `live/*` являются symlink по нормальному устройству Certbot — не отвергай их только из-за symlink, но конечные targets должны быть regular readable files.

#### `--check` — read-only exact-state verification

Проверить:

- certificate валиден минимум 14 дней и SAN exact;
- final Nginx file byte-equal repo template, root:root 0644;
- exact enabled symlink указывает на final site;
- default reject byte-equal repo template, root:root 0644;
- `/etc/nginx/sites-enabled/default` отсутствует;
- bootstrap site и его symlink отсутствуют после завершённой установки;
- deploy hook byte-equal repo template, root:root 0755;
- ACME webroot и challenge dir существуют, root:root, mode 0755;
- `certbot.timer` enabled и active;
- `nginx -t` успешен;
- локальный TLS handshake/certificate trust проверить bounded-командой без зависимости от работающего frontend/API. Подход: `curl --resolve astro.vasiliy-ivanov.ru:443:127.0.0.1` с `--connect-timeout`/`--max-time` на ACME nonexistent URL, без `-k`; HTTP 404 допустим, curl/TLS failure — нет;
- никаких app health checks в этом script.

#### `--apply` — transactional Nginx/Certbot flow

1. Пройти общий preflight и email boundary.
2. Создать ACME directories exact owner/mode.
3. До первой Nginx mutation сохранить точное состояние всех затрагиваемых live paths: тип (missing/regular/symlink), bytes regular file, symlink target, owner/mode. Нельзя превращать старый symlink в regular file при rollback.
4. Установить default reject. Удалить только пакетный `/etc/nginx/sites-enabled/default` symlink/file из enabled; не удалять `sites-available/default`.
5. Если валидного certificate нет:
   - установить bootstrap site root:root 0644 и exact enabled symlink;
   - временно убрать final enabled symlink, если он ломает `nginx -t` из-за отсутствующего cert;
   - `nginx -t`, затем reload Nginx;
   - выполнить `certbot certonly --webroot --webroot-path /var/www/letsencrypt --domain astro.vasiliy-ivanov.ru --email <email> --agree-tos --non-interactive --no-eff-email --key-type ecdsa`;
   - проверить выданный certificate через тот же validator;
   - не использовать `certbot --nginx`, потому что canonical config принадлежит repo.
6. Если certificate уже валиден, не вызывать issue/renew и не требовать email.
7. Установить final site, exact symlink и deploy hook; удалить bootstrap live file/symlink; enable/start `certbot.timer`; `nginx -t`; reload Nginx.
8. Выполнить exact verification как в `--check`.
9. При любой ошибке после первой Nginx mutation восстановить все сохранённые Nginx/hook paths byte/type/owner/mode exact, затем `nginx -t`; если restored config валиден — reload. Исходную ошибку не маскировать rollback-ошибкой. Certbot-created certificate/account files не удалять и не «откатывать».
10. Не запускать/рестартовать app services и DB.

Не выполнять `certbot renew --dry-run` автоматически на каждом apply: это staging ACME network operation. Добавь в runbook отдельную одноразовую проверку после bootstrap.

### 5. Интеграция с `prod-host-prepare.sh` и fingerprint

Расширь существующий host runtime owner:

- inventory/preflight включает:
  - `infra/nginx/00-solarsage-default-reject.conf`;
  - `infra/certbot/deploy-hooks/20-solarsage-reload-nginx`;
  - `infra/fail2ban/jail.d/solarsage-sshd.local`;
  - новые shell scripts для `bash -n`, но setup-only scripts не обязаны входить в runtime fingerprint;
- `--apply` atomically устанавливает и rollback-защищает default reject, Certbot hook и Fail2ban jail наряду с existing live files;
- `--apply` может reload Nginx после `nginx -t` и restart Fail2ban после config validation; app services по-прежнему не трогать;
- `--check` exact-verify bytes/type/owner/mode этих трёх live assets;
- проверяет `certbot.timer` enabled/active, certificate >=14 days, ACME dirs, absence enabled default/bootstrap sites;
- fingerprint должен включать только runtime-owned templates:
  - default reject;
  - final domain Nginx config;
  - deploy hook;
  - Fail2ban jail;
  - existing runtime files.
- `astro-acme-bootstrap.conf`, `prod-os-bootstrap.sh`, `prod-cert-prepare.sh` являются bootstrap-only и не должны сами по себе менять runtime fingerprint;
- не ослабляй уже принятые R9A guards: non-executing env parser, symlink rejection для repo templates, exact rollback, no secret output, no app restart.

Проверь и исправь комментарий/список dependencies в `prod-host-prepare.sh` после расширения.

### 6. Production runbook

Обнови `docs/PRODUCTION_RUNBOOK.md`, не удаляя принятые разделы про deploy, DB, backup и fingerprint.

Канонический fresh-host order должен быть явно записан:

1. скопировать/получить repository bootstrap code и запустить `sudo scripts/prod-os-bootstrap.sh --apply`;
2. настроить private GitHub read-only access и получить checkout в `/opt/solarsage-astro` как `astro` (секреты/ключи не хранить в Git);
3. создать `.env.production` exact owner/mode;
4. проверить DNS A = `157.22.192.242`;
5. `sudo scripts/prod-cert-prepare.sh --apply --email ...` (email нужен только при первой выдаче);
6. одноразово `sudo certbot renew --dry-run`, затем `sudo scripts/prod-cert-prepare.sh --check`;
7. `sudo scripts/prod-host-prepare.sh --apply` и затем `--check`;
8. до явной команды владельца остановиться: никаких app deploy/start;
9. единственный первый запуск кода — отдельный manual deploy (`prod-deploy.sh --current` для уже pinned checkout либо manual GitHub workflow после main), только по команде владельца.

Также добавь:

- routine certificate renewal выполняет `certbot.timer`, deploy hook сначала валидирует Nginx и только затем reload;
- как проверить expiry/timer/hook без печати секретов;
- UFW/fail2ban verification;
- package/bootstrap script не делает app deploy;
- private repo boundary: private key и `.env.production` никогда не входят в repository/fingerprint.

### 7. Тесты и доказательства

Обязательные проверки после реализации:

```bash
bash -n scripts/prod-os-bootstrap.sh
bash -n scripts/prod-cert-prepare.sh
bash -n scripts/prod-host-prepare.sh
bash -n infra/certbot/deploy-hooks/20-solarsage-reload-nginx
bash -n scripts/prod-deploy.sh
bash -n scripts/prod-backup.sh
scripts/prod-infra-fingerprint.sh
git diff --check
```

Дополнительно:

- доказать, что `--check` не содержит mutation commands на исполняемом пути. Не ограничивайся grep, объясни структуру dispatch;
- проверить usage/exit 2 для invalid args обоих новых scripts без root mutation;
- если на local host `--check` ожидаемо падает, это нормально: показать только names нарушенных контрактов, не env values;
- выполнить `nginx -t` только если local machine имеет подходящий безопасный config/cert; не править live `/etc/nginx` здесь;
- `git status --short next-env.d.ts tsconfig.json` должен быть пуст;
- порты 3003/18092 должны быть свободны;
- ни один test/output не должен содержать содержимое ключей, token/API key/password/email из production env.

## Файлы, которые ожидается изменить/создать

Разрешённый scope:

- `scripts/prod-os-bootstrap.sh` (new)
- `scripts/prod-cert-prepare.sh` (new)
- `scripts/prod-host-prepare.sh`
- `scripts/prod-infra-fingerprint.sh`
- `infra/nginx/00-solarsage-default-reject.conf` (new)
- `infra/nginx/astro-acme-bootstrap.conf` (new)
- `infra/nginx/astro.vasiliy-ivanov.ru.conf`
- `infra/certbot/deploy-hooks/20-solarsage-reload-nginx` (new)
- `infra/fail2ban/jail.d/solarsage-sshd.local` (new)
- `docs/PRODUCTION_RUNBOOK.md`
- этот work package и новый review/handoff файл в `docs/work/2026-07-15_production-server-bootstrap/` при необходимости.

Если для корректности нужен другой файл — остановись и сначала объясни архитектору, зачем он нужен. Не меняй workflow/app code в R11.

## Handoff

В конце дай компактный отчёт:

- список файлов;
- точное поведение `--check`/`--apply`;
- какие base services разрешённо стартуют/reload/restart;
- подтверждение, что app services не трогаются;
- все команды тестов и их exit/results;
- ожидаемые live-host действия, которые ты сам не выполнял;
- `git status --short` только по scope-файлам.

Не делай commit/push.
