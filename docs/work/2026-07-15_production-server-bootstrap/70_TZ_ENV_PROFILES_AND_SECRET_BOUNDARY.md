# Production env profiles — process boundary and secret-safe build contract

## Why this is a separate launch gate

Read-only audit `69_AUDIT_PRODUCTION_READINESS_GAPS.md` found a P0: `prod-env-loader.sh` accepts arbitrary variable names and exports every assignment. In addition, API/sidecar systemd units and Docker Compose bypass the loader by reading the shared `.env.production` directly, while Next.js automatically reads a root `.env.production` during build. Fixing only a Bash export allowlist would therefore be incomplete.

This task is architecture + implementation contract. Production apply/deploy, network, SSH, real secrets, commit and push are forbidden. Values must never be read or printed in tests or docs.

## Canonical decision

The checkout must not contain a production secret file. Operator-managed source configuration lives outside the repository:

```text
/etc/solarsage/env/source.env             root:astro 0640
/etc/solarsage/env/api.env                root:astro 0640
/etc/solarsage/env/sidecar.env            root:astro 0640
/etc/solarsage/env/db.env                 root:astro 0640
/etc/solarsage/env/backup.env              root:astro 0640
/etc/solarsage/env/migration.env           root:astro 0640
/etc/solarsage/env/frontend-build.env      root:astro 0640, public values only
/etc/solarsage/env/deploy-control.env      root:astro 0640
```

`source.env` is the only operator input. Profiles are generated atomically by a dedicated non-executing generator after validation. Do not silently fall back to `/opt/solarsage-astro/.env.production`; a regular root `.env.production` in the checkout must fail production guardrails because Next.js would load it automatically.

During migration, support an explicit test-only `--env-file`/path parameter for sandbox fixtures. Production defaults must point to `/etc/solarsage/env/*`, never a checkout-relative secret file.

## Global exact key registry

Unknown keys are errors, not ignored. The registry is split by consumer.

### API profile

Required/security keys:

```text
APP_ENV APP_DOMAIN DATABASE_URL TELEGRAM_BOT_TOKEN DEV_MODE
SESSION_COOKIE_SECURE CORS_ALLOWED_ORIGINS GRACE_USER_SALT LLM_PROVIDER
```

Exactly one active provider key:

```text
OPENROUTER_API_KEY | ANTHROPIC_API_KEY
```

Allowed explicit functional keys:

```text
APP_VERSION INITDATA_MAX_AGE_SECONDS SESSION_COOKIE_NAME SESSION_TTL_SECONDS
SOLARSAGE_URL LLM_MODEL LLM_MAX_TOKENS OPENROUTER_BASE_URL
OPENROUTER_APP_NAME OPENROUTER_SITE_URL GEONAMES_USERNAME GRACE_ENV
GRACE_SERVICE_VERSION NATAL_REPORT_ENABLED SOLARSAGE_V2_ENABLED
SOLARSAGE_V2_DUAL_RUN
```

`POSTGRES_*`, bot username, offsite/restic, frontend and sidecar keys do not enter API profile.

### Sidecar profile

```text
SOLARSAGE_EPHEMERIS_PATH
SOLARSAGE_CALCULATION_VERSION
SOLARSAGE_GIT_SHA
```

Do not pass Telegram, database, LLM, backup or GitHub secrets to sidecar. Host/port are command-owned by the systemd unit; legacy collector-only `SOLARSAGE_BASE_URL`, `SOLARSAGE_API_KEY`, `SOLARSAGE_REPO`, `SOLARSAGE_SWISSEPH_DIR`, `SWISSEPH_EPHE_PATH`, `SE_EPHE_PATH` are not production sidecar server keys.

### Database profile

```text
POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB
```

### Migration profile

```text
DATABASE_URL PGSSLMODE
```

`PGSSLMODE=disable` is command-owned and must be generated/validated, not accepted arbitrarily from source.env.

### Backup/restore and offsite profiles

Database:

```text
POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB
```

Offsite:

```text
OFFSITE_BACKUP_ENABLED OFFSITE_RESTIC_REPOSITORY
OFFSITE_RESTIC_PASSWORD_FILE OFFSITE_RESTIC_TAG
OFFSITE_RESTIC_SSH_KEY OFFSITE_RESTIC_KNOWN_HOSTS
```

SFTP keys are required only for `sftp:` repository. `PGPASSWORD`, `RESTIC_PASSWORD_FILE`, `RESTIC_REPOSITORY` and `PROD_OFFSITE_RESTIC_ARGS` are derived command-local values, never source keys.

### Frontend build profile

Only public values:

```text
NEXT_PUBLIC_API_URL NEXT_PUBLIC_API_BASE_URL
NEXT_PUBLIC_GRACE_LOG_SHIPPING NEXT_PUBLIC_LOG_LEVEL
NEXT_PUBLIC_GRACE_SERVICE_VERSION
```

Safety values are either absent or exact production-safe values; reject demo/fixture/preview flags. `NODE_ENV=production` and `APP_ENV=production` are command-owned. Do not pass `TELEGRAM_BOT_TOKEN`, DB, LLM, JWT, salt, offsite or any unknown `NEXT_PUBLIC_*`/`VITE_*` key to build.

### Deploy-control profile

Only non-secret identity/path values required by orchestration:

```text
BOT_USERNAME SOLARSAGE_EPHEMERIS_PATH POSTGRES_USER POSTGRES_DB
```

Password and provider keys must not be globally exported merely for deploy-control checks.

## Loader API

Replace the current “source and export every assignment” contract with two explicit operations:

```text
prod_env_validate <source-file> <profile-or-all>
prod_env_emit <source-file> <profile> <output-file>
prod_env_run <source-file> <profile> -- <command> [args...]
```

Requirements:

- parser never executes shell, `source`, `eval`, heredoc or substitutions;
- exact key registry and profile membership enforced;
- duplicate/unknown/malformed keys fail before any profile file is replaced;
- active LLM provider key logic is fail-closed;
- output profile is written mode `0640`, owner/group checked, via temp + same-filesystem rename;
- no values in diagnostics, audit or errors;
- `prod_env_run` uses a fresh `env -i` child with only a fixed safe base and profile keys;
- caller shell is never polluted with arbitrary source keys;
- derived variables (`PGPASSWORD`, `RESTIC_*`) exist only in the smallest child scope and are unset on exit.

Use `python3.12` for parsing only if it is already a canonical host dependency. Output assignments must be encoded safely for systemd EnvironmentFile and shell child execution; do not write raw unescaped values that systemd could reinterpret.

## Hard denylist, even before profile filtering

Reject exact names and prefixes that control interpreters, loaders, Git, SSH, Docker, proxy and certificate behavior:

```text
BASH_ENV ENV PATH IFS CDPATH GLOBIGNORE SHELLOPTS BASHOPTS BASH_XTRACEFD
PS4 PROMPT_COMMAND HISTFILE HOME USER LOGNAME SHELL PWD OLDPWD TMPDIR TMP TEMP
LD_* DYLD_* GLIBC_TUNABLES MALLOC_* PYTHON* PIP_* VIRTUAL_ENV CONDA_*
NODE_OPTIONS NODE_PATH NPM_CONFIG_* npm_config_* PNPM_* COREPACK_*
GIT_* SSH_* DOCKER_* COMPOSE_* RESTIC_* PG* HTTP_PROXY HTTPS_PROXY ALL_PROXY
NO_PROXY SSL_CERT_* REQUESTS_CA_BUNDLE CURL_CA_BUNDLE NODE_EXTRA_CA_CERTS XDG_*
GITHUB_* PROD_SSH_* VITE_* REACT_APP_*
```

Known legitimate exceptions must be explicit profile keys, not wildcard acceptance. Until cloud auth is specified, reject arbitrary `AWS_*`/provider variables too.

## Systemd/Compose boundary changes

Update these consumers to profile files, never `source.env`:

- `infra/systemd/solarsage-api.service` → `EnvironmentFile=/etc/solarsage/env/api.env`;
- `infra/systemd/solarsage-sidecar.service` → sidecar profile only;
- `infra/systemd/solarsage-db.service` → `docker compose --env-file /etc/solarsage/env/db.env`;
- backup/maintenance/restore units or scripts → explicit backup/offsite profiles;
- deploy migration/preflight → `prod_env_run` profile child;
- frontend build → generated public profile through `env -i`.

Do not add a shared `EnvironmentFile` to frontend. Do not let API/sidecar inherit DB/offsite/Telegram keys they do not consume.

Before build, fail if checkout contains a regular `.env.production` or other production secret file. Update `check_prod_guard.sh`, `prod-deploy.sh` and runbook accordingly. Dev/test fixture paths must remain explicit and never enter production runtime.

## Fixed child environment

Every external child launched after validation must receive an explicit base, at minimum:

```text
HOME=/home/astro
PATH=/home/astro/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
LANG=C.UTF-8
LC_ALL=C.UTF-8
GIT_TERMINAL_PROMPT=0
```

Add `TZ=UTC` where timestamp semantics require it. Do not blindly unset `HOME` (SSH config/pnpm need it), `PATH` (pnpm may be under `/home/astro/.local/bin`) or locale. Do not inherit arbitrary proxy/custom CA values without a separate audited contract.

The forced wrapper may additionally use a clean `env -i` for target dispatch, preserving only trusted HOME/PATH/locale. Do not change verb/sha contract while doing so.

## Required test matrix

Extend `scripts/tests/test-prod-env-loader.sh` and source-loader/deploy harnesses with sandbox-only cases:

1. unknown key `BASH_ENV`, `PATH`, `NODE_OPTIONS`, `LD_PRELOAD`, `PYTHONPATH`, `GIT_DIR`, `GIT_CONFIG_*`, `SSH_ASKPASS`, `HTTP_PROXY` → non-zero, no profile/output mutation;
2. exact profile membership and no cross-profile key leakage;
3. provider inactive key, duplicate key, malformed value, substitution, control char;
4. source file symlink/FIFO/directory/wrong owner/mode/no-final-LF;
5. generated profile atomic write failure and cleanup;
6. API/sidecar/db/backup/frontend profile output contains no forbidden or unknown names;
7. root checkout `.env.production` presence fails production guard;
8. build mock sees public profile only and a canary secret never appears in env/stdout/stderr;
9. systemd/compose static consumers reference correct profile path, not source.env;
10. fixed child PATH/HOME/locale and no inherited dangerous variables;
11. `prod_env_run` leaves caller environment unchanged after success/failure;
12. no raw secret values in diagnostics or temporary artifacts.

Each mutation must be applied to a sandbox copy and fail through the same validator. Do not use production env overrides to make a test green.

## Acceptance

Coder runs syntax/unit/harness checks only, from fresh shells, with no production/network/SSH/commit/push. Architect independently inspects profile allowlists and runs the suite twice. This task is not complete until systemd/Compose references and root `.env.production` behavior are covered by tests and runbook evidence.
