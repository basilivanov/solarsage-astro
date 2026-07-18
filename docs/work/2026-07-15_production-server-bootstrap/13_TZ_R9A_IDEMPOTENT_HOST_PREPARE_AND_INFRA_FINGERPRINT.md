# R9A — idempotent host preparation and infrastructure fingerprint

Дата: 2026-07-15

Исполнитель: кодер в `tmux astro:0.0` на `gemini-3-flash-agent`.

## 1. Цель

Автоматизировать все repository-owned one-time host preparation steps, не превращая production deployment в автоматический.

После R9A:

- root запускает explicit `prod-host-prepare.sh --apply` для установки/обновления инфраструктуры;
- `--apply` не стартует и не рестартует API/sidecar/frontend;
- `--check` read-only доказывает готовность host;
- PostgreSQL запускается отдельным canonical systemd unit и имеет readiness ordering;
- backup/ephemeris directories создаются с правильными owner/mode;
- legacy/preview production units не устанавливаются glob-ом;
- repository infra имеет deterministic fingerprint;
- code deploy после checkout сверяет fingerprint с применённым host fingerprint и fail-closed останавливается до dependency install/build/migration/restart при mismatch;
- сам запуск приложения остаётся только через manual deploy R8.

Certificate issuance automation будет отдельным R9B. В этой волне host prepare требует уже существующий production certificate и не запускает Certbot.

## 2. Scope

Создать:

```text
scripts/prod-infra-fingerprint.sh
scripts/prod-host-prepare.sh
infra/systemd/solarsage-db.service
```

Изменить:

```text
scripts/prod-deploy.sh
infra/systemd/solarsage-api.service
infra/systemd/solarsage-backup.service
docs/PRODUCTION_RUNBOOK.md
```

Существующие R3–R8B changes сохранить. Другие runtime-файлы не менять. No commit, push, server access, server mutation or deploy.

## 3. Pure infrastructure fingerprint

### File

```text
scripts/prod-infra-fingerprint.sh
```

Executable `100755`, Bash, `set -euo pipefail`, GRACE header/module contract/map.

Behavior:

- resolve repository root from script location, independent of current working directory;
- verify every owned path below exists as a regular file;
- compute one deterministic lowercase SHA-256 over both ordered relative path names and exact bytes;
- print exactly one 64-lowercase-hex line to stdout and no other success output;
- errors only to stderr, non-zero;
- no secrets, network, Git operations, file writes or environment reads.

Canonical ordered owned path list must be hardcoded once in this script:

```text
infra/nginx/astro.vasiliy-ivanov.ru.conf
infra/production/docker-compose.yml
infra/production/solarsage-deploy.sudoers
infra/production/solarsage-github-deploy
infra/systemd/solarsage-db.service
infra/systemd/solarsage-api.service
infra/systemd/solarsage-sidecar.service
infra/systemd/solarsage-frontend.service
infra/systemd/solarsage-backup.service
infra/systemd/solarsage-backup.timer
scripts/prod-backup.sh
scripts/prod-host-prepare.sh
scripts/prod-infra-fingerprint.sh
```

Avoid ambiguous concatenation: hash each path with a NUL separator and exact file bytes, or an equally collision-unambiguous framing. Do not rely on locale-dependent directory iteration. Set a stable locale if needed.

## 4. Canonical PostgreSQL systemd unit

### File

```text
infra/systemd/solarsage-db.service
```

Unit contract:

```ini
[Unit]
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/solarsage-astro
ExecStart=/usr/bin/docker compose --env-file /opt/solarsage-astro/.env.production -f /opt/solarsage-astro/infra/production/docker-compose.yml up -d --wait db
ExecReload=/usr/bin/docker compose --env-file /opt/solarsage-astro/.env.production -f /opt/solarsage-astro/infra/production/docker-compose.yml up -d --wait db
ExecStop=/usr/bin/docker compose --env-file /opt/solarsage-astro/.env.production -f /opt/solarsage-astro/infra/production/docker-compose.yml stop -t 30 db
TimeoutStartSec=180
TimeoutStopSec=60

[Install]
WantedBy=multi-user.target
```

Use root default (do not set `User=astro`; astro intentionally is not in docker group). Add appropriate GRACE comments. No secrets in file; Compose reads env-file.

### Dependency changes

`solarsage-api.service`:

- replace Docker ordering/dependency with `solarsage-db.service`;
- preserve network and sidecar ordering;
- exact intent: `After=network-online.target solarsage-db.service solarsage-sidecar.service`, `Requires=solarsage-db.service`, `Wants=network-online.target solarsage-sidecar.service`.

`solarsage-backup.service`:

- `After=solarsage-db.service`;
- `Requires=solarsage-db.service`;
- no direct Docker dependency.

Do not weaken hardening.

## 5. Root-only host preparation script

### File and invocation

```text
scripts/prod-host-prepare.sh
```

Executable `100755`, Bash, `set -euo pipefail`, `umask 027`, GRACE contracts. Exact accepted forms:

```bash
scripts/prod-host-prepare.sh --check
scripts/prod-host-prepare.sh --apply
```

No args or any other args -> usage, exit 2. Both modes require root; non-root -> explicit failure. Use a non-blocking lock under `/run/lock` or `/tmp` so two prepares cannot race.

Constants:

```text
APP_ROOT=/opt/solarsage-astro
APP_USER=astro
APP_GROUP=astro
ENV_FILE=/opt/solarsage-astro/.env.production
DOMAIN=astro.vasiliy-ivanov.ru
FINGERPRINT_FILE=/etc/solarsage/infra-fingerprint
```

Never print `.env.production`, tokens, passwords, keys, DB URL or provider keys.

### 5.1 Common preflight in both modes

Fail closed and aggregate/clearly report:

1. OS exact Ubuntu 24.04 (`/etc/os-release`).
2. User/group `astro` exist.
3. `/opt/solarsage-astro` exists, is a Git worktree, owner `astro:astro`.
4. `.env.production` regular file, owner `astro:astro`, mode exactly 600 or 640.
5. Required commands exist:

```text
git curl cmp sha256sum python3.12 node pnpm docker nginx certbot pg_dump pg_isready systemctl visudo openssl
```

6. `docker compose version` succeeds.
7. Node version >=20.9; pnpm version exact `10.32.1`.
8. Repository templates pass before install:

```text
bash -n prod-deploy/prod-backup/wrapper/fingerprint/host-prepare
visudo -cf repo sudoers template
systemd-analyze verify all six canonical units including db
docker compose config with real env redirected to a root-only temporary file; remove it via trap; never print render
```

9. Certificate files already exist at canonical Let's Encrypt paths and `openssl x509 -checkend 1209600` succeeds (at least 14 days validity). If absent/near expiry, fail with safe instruction that R9B/Certbot must be completed; do not invoke Certbot.
10. Safe env contract in a subshell without printing values:

- `APP_ENV=production`;
- `APP_DOMAIN=astro.vasiliy-ivanov.ru`;
- `DEV_MODE=false`;
- `SESSION_COOKIE_SECURE=true`;
- non-empty POSTGRES_USER/PASSWORD/DB, TELEGRAM_BOT_TOKEN, BOT_USERNAME, GRACE_USER_SALT, LLM_PROVIDER;
- `BOT_USERNAME` normalized equals AstroGrace_Bot;
- active provider key non-empty after whitespace trim;
- `DATABASE_URL` does not contain sqlite.

Do not import application code or create venvs in host prepare.

### 5.2 Additional apply preflight

Before any mutation, repository source must be clean for tracked, staged and non-ignored untracked paths, evaluated as `astro` user. Ignored `.env.production`, build outputs, venvs and node_modules are allowed.

Do not use broad restore/reset/checkout/clean. Dirty -> fail before first mutation.

### 5.3 Apply operations — exact order

After every preflight succeeds:

1. Create directories idempotently:

```text
/var/backups/solarsage  owner astro:astro mode 0700
/opt/sweph/ephe         owner astro:astro mode 0755
/etc/solarsage          owner root:root mode 0755
```

2. Install exact canonical systemd files root:root 0644:

```text
solarsage-db.service
solarsage-sidecar.service
solarsage-api.service
solarsage-frontend.service
solarsage-backup.service
solarsage-backup.timer
```

Never glob `solarsage-*.service`. Never install `solarsage.service` or preview 3001 unit.

3. Install wrapper root:root 0755 and sudoers root:root 0440 at canonical live paths. Validate repo template before install and full `/etc/sudoers` after install.

4. Install canonical Nginx config root:root 0644 into sites-available, create/update the exact sites-enabled symlink, run `nginx -t`, then reload Nginx. Do not remove unrelated vhosts in R9A.

5. `systemctl daemon-reload`.

6. If legacy units `solarsage.service` or `solarsage-frontend-preview-3001.service` exist, disable and stop only those exact units. No wildcard.

7. Enable, but do not start/restart, canonical application units:

```text
solarsage-sidecar.service
solarsage-api.service
solarsage-frontend.service
solarsage-backup.timer
```

Do not use `--now` for these four. If any is already active, do not restart or stop it.

8. Enable and start/reload only `solarsage-db.service`; wait for systemd active and Docker health `healthy` with a bounded loop. This is infrastructure preparation, not application launch.

9. Compute repository fingerprint using `scripts/prod-infra-fingerprint.sh`. Only after every install/validation succeeds, atomically write it to `/etc/solarsage/infra-fingerprint` root:root 0644 (temporary file in same directory + `mv`).

10. Run the same read-only verification used by `--check` and print one concise `HOST PREPARE PASS` summary. Never print secrets.

No app restart, no code build, no migration, no backup, no deploy, no Git fetch/checkout.

### 5.4 Check mode

`--check` performs no mutation and verifies:

- all common preflight requirements;
- exact installed file equality (`cmp -s`) for six units, wrapper, sudoers and Nginx config;
- enabled state for db/sidecar/api/frontend/backup.timer;
- `solarsage-db.service` active;
- Docker container `solarsage-db` running and healthy;
- backup and ephemeris directories exact owner/mode;
- full sudoers valid;
- Nginx config valid;
- applied fingerprint file exists, contains exact 64 lowercase hex, equals current repository fingerprint;
- legacy and preview units are not active/enabled.

Application services are allowed to be either inactive (pre-launch) or active (existing production); check must not start/restart them.

Success stdout only concise statuses, ending `HOST PREPARE CHECK PASS`.

## 6. Deploy-side fingerprint gate

Modify `scripts/prod-deploy.sh` after exact target checkout/current SHA selection and before loading env/dependency install:

- stage `host-readiness`;
- require `/etc/solarsage/infra-fingerprint` regular readable file;
- validate file contains exactly one 64-lowercase-hex line;
- compute repository fingerprint only via `scripts/prod-infra-fingerprint.sh`;
- exact compare;
- mismatch -> fail non-zero before env load/install/build/backup/migration/restart, with instruction to run root host prepare for this exact checkout;
- do not auto-sudo or auto-apply infra.

In `--current`, same gate applies.

Update deploy module dependency/contract comments if needed. Do not disturb R8 source/SHA gates or R7 cleanup.

## 7. Runbook

Rewrite First Bootstrap to remove globs/manual scattered copies and document:

1. prerequisite versions and existing certificate for R9A;
2. clone + secure env + read-only `sudo scripts/prod-host-prepare.sh --check` (expected failure before apply is okay);
3. single preparation command `sudo scripts/prod-host-prepare.sh --apply`;
4. preparation does not launch/restart app services;
5. manual first deploy remains `scripts/prod-deploy.sh --current` as astro only after host check passes;
6. after any repository-owned infra template change, checkout target commit, rerun root `--apply`, then trigger manual pinned deployment;
7. normal code-only commits reuse matching fingerprint and only need manual deploy workflow.

Add exact `--check` command and explain fingerprint failure. Document backup/ephemeris directory provisioning and canonical DB unit. Remove old systemd glob-copy and direct Docker-as-astro instructions.

Do not yet automate or rewrite certificate issuance beyond noting R9B.

## 8. Tests

Required:

```bash
bash -n scripts/prod-infra-fingerprint.sh
bash -n scripts/prod-host-prepare.sh
bash -n scripts/prod-deploy.sh
systemd-analyze verify infra/systemd/solarsage-db.service infra/systemd/solarsage-api.service infra/systemd/solarsage-sidecar.service infra/systemd/solarsage-frontend.service infra/systemd/solarsage-backup.service infra/systemd/solarsage-backup.timer
visudo -cf infra/production/solarsage-deploy.sudoers
POSTGRES_USER=dummy POSTGRES_PASSWORD=dummy POSTGRES_DB=dummy docker compose -f infra/production/docker-compose.yml config >/tmp/r9a-compose.yml
git diff --check
```

Fingerprint regressions in temporary repo/copy:

1. same bytes from different cwd -> same 64 hex;
2. repeated run -> identical;
3. changing one owned byte -> different;
4. changing path framing/order -> different;
5. missing owned file -> non-zero/no stdout hash;
6. no secret/env access.

Host prepare safe parser/static regressions:

- no args/unknown/extra -> 2;
- non-root check/apply -> fail before mutation;
- assert exact install path list, no systemd glob;
- assert no `systemctl restart` for canonical app services and no `enable --now` for them;
- assert only db may be started/reloaded;
- assert no Git fetch/checkout/restore/reset/clean;
- assert fingerprint atomic write after validations.

Deploy fingerprint gate in temporary extracted harness:

- missing fingerprint -> fail;
- malformed fingerprint -> fail;
- mismatch -> fail;
- match -> pass;
- all failures happen before a sentinel dependency/build command.

Repeat R8 parser/wrapper/newline source regressions and R7 byte exact cleanup regressions. Run production guardrails/YAML checks. No live `--apply` in coder phase.

## 9. Handoff

Return exact files/modes, behavior, all checks, confirmation that app services were never started/restarted, and no commit/push/server access/deploy. Stop.
