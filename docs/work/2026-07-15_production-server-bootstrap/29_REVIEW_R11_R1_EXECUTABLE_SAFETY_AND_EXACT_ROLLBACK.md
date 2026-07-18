# R11-R1 review — executable safety, exact rollback, strict CLI

## Статус

R11 в текущем виде **не принят**. Исправь только перечисленные дефекты, не расширяя scope. Не делай commit/push и не подключайся к production.

## Критические дефекты

### 1. `prod-cert-prepare.sh --apply` сейчас неисполняем

В top-level apply block используются `local path=...`, `local tmp_file` вне функции. `bash -n` это не ловит, но runtime завершается `local: can only be used in a function`.

Исправление:

- вынести state capture/apply/rollback в функции или убрать все top-level `local`;
- предпочти функции: `capture_path_state`, `restore_path_state`, `cleanup_snapshots`, `rollback`, `apply_cert_state`, `main`;
- после исправления `rg -n '^\s*local ' scripts/prod-cert-prepare.sh` должен показывать `local` только внутри функций.

### 2. CLI `prod-cert-prepare.sh` не соответствует трём разрешённым формам

Сейчас принимаются запрещённые варианты `--check --email ...` и `--email ... --apply`; доходит до root-check вместо exit 2.

Разрешить ровно:

- `--check`;
- `--apply`;
- `--apply --email VALUE`.

Любое другое число аргументов, другой порядок, email с `--check`, duplicate/unknown flags — usage/error и exit 2 **до root-check и lock**.

Email validator:

- запретить все ASCII control chars (`0x00-0x1f`, `0x7f`) и whitespace;
- ровно один `@`, обе части непустые;
- не печатать введённый email в error.

### 3. Rollback сертификатного flow неполный

Сейчас final `verify_cert_state` выполняется после удаления backup temp files, INT/TERM не откатываются, restore не атомарен, dangling symlink может считаться missing, а reload выполняется без обязательного успешного `nginx -t`.

Сделай одну транзакцию от первой Nginx/hook mutation до успешного final verification:

1. До mutation capture exact state каждого path: `missing`, `regular`, `symlink`; для regular — bytes/owner/group/mode; для symlink — raw target и link owner/group. Любой другой live type — fail до mutation.
2. Paths: reject config, bootstrap available/enabled, final available/enabled, enabled default, deploy hook.
3. Использовать `-e || -L`, когда dangling symlink должен считаться существующим.
4. Restore regular file через temp в том же parent + atomic install/mv, exact owner/mode; не следовать неожиданному symlink.
5. Поставить traps после capture и до первой mutation. На EXIT с nonzero/INT/TERM rollback ровно один раз. После commit-success rollback запрещён.
6. Внутри транзакции: install, certbot issue при необходимости, final install, timer enable/start, `nginx -t`, reload и **final `verify_cert_state`**.
7. Только после успешного verification убрать traps/temp snapshots.
8. Rollback сохраняет первоначальный exit status. После restore сначала `nginx -t`; reload только при success. Primary error не маскировать rollback error.
9. Certbot-created account/certificate не удалять.

### 4. Exact verification неполна

В `prod-cert-prepare.sh` и `prod-host-prepare.sh`:

- reject/final/hook/jail должны быть regular и не symlink, затем byte/mode/owner check;
- enabled final — exact symlink;
- default/bootstrap absence проверять `! -e && ! -L`;
- проверять `/var/www/letsencrypt` и `/var/www/letsencrypt/.well-known/acme-challenge`, root:root 0755;
- hostname проверять `openssl x509 -checkhost astro.vasiliy-ivanov.ru`, не substring regex;
- cert/key targets после resolution должны быть readable regular files;
- добавить фактически используемые commands в preflight либо убрать зависимость.

### 5. Nginx headers повреждены escaping

В `infra/nginx/astro.vasiliy-ivanov.ru.conf` появились буквальные `\"...\"`. Вернуть нормальные quoted values без backslash. Не менять остальные принятые proxy/security настройки.

## `prod-os-bootstrap.sh` corrections

### 6. Repo/template preflight до apt mutation

До `apt-get update` вычислить repo root относительно script и проверить Fail2ban template как regular non-symlink. Missing/symlink — fail до первой mutation.

### 7. APT key/source installation должна быть atomic

- Docker key: canonical `/etc/apt/keyrings/docker.asc`, официальный ASCII key, root:root 0644;
- NodeSource key: `/etc/apt/keyrings/nodesource.gpg`, dearmor во временный файл, затем atomic install;
- source list создавать во временном root-only файле и atomically install root:root 0644;
- temp files чистить trap на любом exit/signal;
- не использовать pipe-to-shell/pipe-to-gpg setup;
- working Docker+Compose/Node 22 не заменять;
- фактические versions валидировать после установки.

### 8. OS verification bugs

- добавить `timedatectl` и `dpkg` в required commands;
- исправить `unattended-upgrades` state capture без двойной строки от `command || echo`;
- unit existence проверять через `systemctl show -p LoadState --value`, `not-found` — ошибка;
- existing home до chmod/chown должен быть real directory, не symlink;
- pnpm exact проверить как root и как `astro` с deterministic PATH;
- `astro` не добавлять в docker group.

### 9. UFW canonical verification и legacy 443

Сделай deterministic check (`LC_ALL=C ufw show added` либо обоснованный эквивалент):

- required inbound allows — только `22/tcp`, `80/tcp`, `443/tcp`;
- любые дополнительные `ufw allow ...` report/error;
- apply не удаляет неизвестные rules;
- apply может нормализовать только exact known legacy `ufw allow 443`: `ufw --force delete allow 443`, затем `ufw allow 443/tcp`;
- запрещён `ufw reset`;
- final verification обнаруживает extras и завершается nonzero с rule text.

Покажи fixture-like sample test выбранного parser.

## `prod-host-prepare.sh` corrections

### 10. Не регрессировать принятый R9A exact rollback

Текущий `rollback_assets` не сохраняет owner/mode/type, не сохраняет enabled default, принимает symlink как regular и reload/restart делает без validation.

Используй generic exact snapshot mechanism:

- capture final available/enabled, default enabled, reject, hook, jail;
- reject unexpected types до mutation;
- exact restore type/bytes/owner/mode/target;
- candidate validation, reload/restart и final exact verification внутри rollback boundary;
- rollback Nginx reload только после `nginx -t`;
- rollback Fail2ban restart только после `fail2ban-client -d`;
- сохранять primary status; INT/TERM/EXIT после mutation обязаны откатывать;
- создать exact challenge directory;
- enable/start `certbot.timer` как ownership финального state;
- не стартовать/рестартовать `solarsage-api`, `solarsage-sidecar`, `solarsage-frontend`; DB-only start/reload допустим;
- inventory repo templates: `-f` и `! -L`, включая новые scripts для `bash -n`;
- fingerprint prevalidation также отвергает symlink.

Не ослабляй non-executing env parser и NUL-safe dirty gate.

## Runbook corrections

### 11. Убрать опасные/неверные инструкции

- удалить широкий `chown -R astro:astro /opt/solarsage-astro`;
- bootstrap требует полный безопасно переданный checkout/bootstrap bundle, а не один script, потому что нужен repo template;
- после `prod-host-prepare --check` явно: **STOP, application remains unchanged until owner command**;
- первый deploy не представлять автоматическим продолжением bootstrap;
- private repo key и env остаются manual secret boundary.

## Проверки

Обязательно показать результаты:

- `bash -n` для обоих новых scripts, host/fingerprint и Certbot hook;
- invalid forms `prod-cert-prepare.sh --check --email x@example.com`, `--email x@example.com --apply`, control-char email — exit 2 без sudo/root-check;
- `prod-os-bootstrap.sh --bad` — exit 2;
- `scripts/prod-infra-fingerprint.sh`;
- `git diff --check`;
- clean `next-env.d.ts`/`tsconfig.json`;
- свободные 3003/18092.

Добавь безопасный executable regression harness path-state capture/restore в temp directory либо эквивалентное доказательство, реально проверяющее regular/symlink/dangling/missing, exact bytes/mode/target. Harness не пишет `/etc`, не вызывает systemctl и не читает env.

## Handoff

Сопоставь пункты 1–11 с конкретным исправлением и evidence. Не делай commit/push.
