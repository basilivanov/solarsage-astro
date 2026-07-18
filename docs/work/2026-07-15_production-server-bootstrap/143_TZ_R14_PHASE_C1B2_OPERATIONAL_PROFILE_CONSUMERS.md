# R14 Phase C1B2 — operational consumers cut over to installed profiles

## Dependency and boundary

C1B1 is accepted independently in
`142_REVIEW_R14_PHASE_C1B1_ACCEPTED_INDEPENDENT.md`.

This is the operational-consumer half of C1B. It removes the checkout
`.env.production` dependency from systemd/Compose/backup/offsite/restore/host
preflight paths and makes those paths use the immutable installed generation.

It deliberately does **not** finish the deploy/build secret boundary. The
legacy `scripts/prod-deploy.sh`, `scripts/check_prod_guard.sh`, frontend build
flow and Telegram test-data fallback are C1B3 and must remain out of scope here.
The deprecated `scripts/lib/prod-env-loader.sh` therefore remains temporarily
for the still-unmigrated deploy path; do not delete it in C1B2.

Read completely before editing:

- `AGENTS.md`;
- `70_TZ_ENV_PROFILES_AND_SECRET_BOUNDARY.md`;
- `73_TZ_CANONICAL_DATABASE_IDENTITY.md` (C2 remains separate);
- `77_ARCH_IMMUTABLE_RELEASE_DEPLOY.md`;
- `79_ARCH_GLOBAL_MAINTENANCE_STATE_MACHINE.md`;
- `142_REVIEW_R14_PHASE_C1B1_ACCEPTED_INDEPENDENT.md`;
- all current target scripts, units and their test harnesses.

## Mandatory coder protocol

- Work directly in the current interactive pane.
- **No subagents, Task, explorer, delegation or parallel agents.**
- No commit or push.
- No production host/service/database/Docker/Nginx/SSH/GitHub/Restic/Telegram
  operation, no systemd start/restart/reload and no network.
- All runtime proof uses synthetic profile generations and fake commands under
  private `/tmp` directories. A `docker compose config` parse is allowed only
  with synthetic env and no daemon; no `docker compose up`.
- Never read or print a real source/profile file, token, password, private key,
  checkout `.env.production` or production URL.
- Preserve unrelated dirty-worktree changes.
- Keep GRACE markers/contracts/maps in every new or substantially changed file.
- Stop after this phase and provide a full handoff; do not begin C1B3/C2.

## Architectural decisions (do not improvise)

### 1. Runtime source boundary

Operational runtime code may read only the selected installed profile through
`scripts/prod-env-run.sh` or a systemd `EnvironmentFile` pointing at
`/etc/solarsage/env/current/<profile>.env`.

It must never:

- source/dot/eval a profile or source file;
- call `prod_env_load`;
- read `/opt/solarsage-astro/.env.production`;
- fall back to any checkout-relative env file;
- export the complete source profile into a caller shell.

`/etc/solarsage/env/source.env` is still operator input for the profile
generator/check only. It is not a runtime consumer input.

### 2. Compose serialization trap — use the runner, not `--env-file current/db.env`

Generated `*.env` files use the canonical systemd `EnvironmentFile` quoting.
Docker Compose's dotenv parser is not byte-equivalent for escaped `$`, quotes,
backslashes and `#`.

Independent synthetic probe (no daemon) proved:

```text
docker compose --env-file generated/db.env config
special-password round-trip: false
```

Therefore **never** write:

```text
docker compose --env-file /etc/solarsage/env/current/db.env ...
```

For DB Compose commands use the C1B1 runner, which decodes the profile into the
child environment, and disable Compose's automatic checkout `.env` discovery:

```text
/opt/solarsage-astro/scripts/prod-env-run.sh db -- \
  /usr/bin/docker compose --env-file /dev/null \
  -f /opt/solarsage-astro/infra/production/docker-compose.yml <verb> db
```

`--env-file /dev/null` is intentional: shell env supplied by the runner is the
only DB input, while `/dev/null` prevents a checkout `.env` from being loaded.
The runner child contains only the DB profile plus its fixed base/markers.

### 3. Manual operational scripts use a profile context bridge

Scripts that can be run manually or called by another script must have one
small, explicit context bridge. Add:

```text
scripts/lib/prod-profile-context.sh
```

Public function contract:

```bash
prod_profile_require EXPECTED_PROFILE SCRIPT_PATH [ARG...]
```

Exact behavior:

1. `EXPECTED_PROFILE` must be one of the seven registered profiles; otherwise
   fail with a safe nonzero code.
2. If both command-owned markers are present and valid:
   - `SOLARSAGE_ENV_PROFILE == EXPECTED_PROFILE`;
   - `SOLARSAGE_ENV_GENERATION` matches `^gen-[0-9a-f]{32}$`;
   then return success without changing the environment.
3. Otherwise `exec` the canonical sibling wrapper exactly as:

   ```text
   SCRIPT_DIR/prod-env-run.sh EXPECTED_PROFILE -- SCRIPT_PATH [ARG...]
   ```

   Preserve argv boundaries; never use `sh -c`, `eval`, `source` of an env
   file, command-string reconstruction or a hidden fallback.
4. If the wrapper is missing/symlink/non-executable, fail closed.
5. Do not print marker values or any environment value.

This marker is an execution-context guard, not a cryptographic identity claim;
the runner's canonical path/current-generation validation and required profile
keys remain the actual boundary. The bridge exists so old direct invocations
automatically re-enter through the runner instead of silently using ambient
variables.

Use the bridge at the top of exactly these scripts, before any DB/Restic or
service side effect:

- `scripts/prod-backup.sh` → `backup`;
- `scripts/prod-offsite-check.sh` → `backup`;
- `scripts/prod-offsite-maintenance.sh` → `backup`;
- `scripts/prod-db-restore.sh` → `backup`.

After the bridge succeeds, these scripts may use only variables from the
selected backup profile and their fixed command-owned values. Remove their
legacy env-file metadata checks, `ENV_FILE`, `DOMAIN`, loader sourcing and
`prod_env_load` calls. Keep all existing backup/restore/offsite safety logic,
locks, signal handling, provenance and no-secret diagnostics unchanged.

Nested calls (`maintenance → offsite-check`, `restore → backup --local-only`)
must inherit the valid backup context and must not recursively spawn runners.

## Exact consumer changes

### A. API unit

Modify `infra/systemd/solarsage-api.service`:

```ini
EnvironmentFile=/etc/solarsage/env/current/api.env
Environment="PGSSLMODE=disable"
```

Remove every checkout `.env.production` reference. Retain user/group,
working directory, fixed API command, hardening, port 8000 and existing
command-owned `PATH`. Do not add DB/offsite/frontend keys.

### B. Sidecar unit

Modify `infra/systemd/solarsage-sidecar.service`:

```ini
EnvironmentFile=/etc/solarsage/env/current/sidecar.env
```

Remove checkout env references. Retain only command-owned `PYTHONPATH`, host,
port and existing hardening. Do not add API/Telegram/DB/LLM/backup keys.

### C. DB unit

Modify `infra/systemd/solarsage-db.service` to execute all three Compose verbs
through the profile runner:

```ini
ExecStart=/opt/solarsage-astro/scripts/prod-env-run.sh db -- /usr/bin/docker compose --env-file /dev/null -f /opt/solarsage-astro/infra/production/docker-compose.yml up -d --wait db
ExecReload=/opt/solarsage-astro/scripts/prod-env-run.sh db -- /usr/bin/docker compose --env-file /dev/null -f /opt/solarsage-astro/infra/production/docker-compose.yml up -d --wait db
ExecStop=/opt/solarsage-astro/scripts/prod-env-run.sh db -- /usr/bin/docker compose --env-file /dev/null -f /opt/solarsage-astro/infra/production/docker-compose.yml stop -t 30 db
```

Do not add `EnvironmentFile` here and do not use a checkout or current profile
as Compose `--env-file`. The runner is the DB profile boundary. Preserve
WorkingDirectory, Docker dependency, timeouts and oneshot semantics.

### D. Backup and maintenance units

Modify both:

- `infra/systemd/solarsage-backup.service`;
- `infra/systemd/solarsage-backup-maintenance.service`.

Their `ExecStart` must invoke the wrapper with `backup` and the exact absolute
script path:

```text
/opt/solarsage-astro/scripts/prod-env-run.sh backup -- /opt/solarsage-astro/scripts/prod-backup.sh
/opt/solarsage-astro/scripts/prod-env-run.sh backup -- /opt/solarsage-astro/scripts/prod-offsite-maintenance.sh --run
```

Do not add a shared source file or loader. Keep User=astro, group, working
directory, timers, timeouts, `KillMode`/hardening and writable paths. The
wrapper's fixed env is the only profile input.

### E. Backup/offsite/restore scripts

Apply the context bridge exactly once at the top of each target script. Remove:

- `ENV_FILE=/opt/solarsage-astro/.env.production`;
- source/dot of `scripts/lib/prod-env-loader.sh`;
- owner/mode checks for the checkout env file;
- all `prod_env_load` calls and loader comments;
- any fallback to ambient source env.

Keep:

- CLI parsing and exact exit codes;
- DB host/port flags and `PGPASSWORD` child-scope cleanup;
- Restic argv construction and credential-file checks;
- backup/restore locks and state-machine behavior;
- restore's interactive/confirmation and service-state guards;
- no raw secret/URL output.

`prod-offsite-runtime.sh` remains a pure helper over already-present backup
profile variables; it must not load or source env data.

### F. Host-preparation checks

Modify `scripts/prod-host-prepare.sh` only for this consumer boundary:

1. Remove `ENV_FILE=/opt/solarsage-astro/.env.production` and all direct file
   metadata/loader checks.
2. In read-only preflight, invoke the canonical profile check:

   ```text
   /opt/solarsage-astro/scripts/prod-env-prepare.sh --check
   ```

   This is an operator/profile-generation check, not a runtime secret export.
   Never call `--apply` from host-prepare.
3. Replace offsite flag loading with:

   ```text
   runuser -u astro -- /opt/solarsage-astro/scripts/prod-env-run.sh backup -- \
     /opt/solarsage-astro/scripts/prod-offsite-check.sh --preflight
   ```

   rc `3` means explicitly disabled and is handled as the existing warning;
   all other nonzero errors remain fatal. Do not print the flag value.
4. Replace Compose config validation with the DB runner and `--env-file
   /dev/null`; redirect only synthetic/config output as the old guard did and
   never log it.
5. Preserve root transaction, unit installation, fingerprint, Nginx,
   fail2ban, ephemeris and rollback behavior. Do not change deploy sequence.

No production apply or systemd reload is allowed in tests.

## Files in scope

Create:

1. `scripts/lib/prod-profile-context.sh`;
2. `scripts/tests/test-prod-profile-consumer-cutover.sh`.

Modify:

3. `infra/systemd/solarsage-api.service`;
4. `infra/systemd/solarsage-sidecar.service`;
5. `infra/systemd/solarsage-db.service`;
6. `infra/systemd/solarsage-backup.service`;
7. `infra/systemd/solarsage-backup-maintenance.service`;
8. `scripts/prod-backup.sh`;
9. `scripts/prod-offsite-check.sh`;
10. `scripts/prod-offsite-maintenance.sh`;
11. `scripts/prod-db-restore.sh`;
12. `scripts/prod-host-prepare.sh`;
13. `scripts/lib/prod-offsite-runtime.sh` only if needed to remove stale
    loader assumptions;
14. relevant existing backup/offsite/restore/unit/host tests;
15. `docs/PRODUCTION_RUNBOOK.md` operational profile/consumer sections;
16. `scripts/prod-infra-fingerprint.sh` and host inventory for the new helper
    and every changed infra consumer.

Explicitly out of scope (C1B3):

- `scripts/prod-deploy.sh` consumer/build rewrite;
- `scripts/check_prod_guard.sh` root `.env.production` fail-closed change;
- `scripts/generate-telegram-test-initdata.py` fallback removal;
- frontend build/install secret boundary;
- immutable release worker, migration policy and maintenance state machine;
- C2 DB URL identity/SQLAlchemy parity;
- production launch/rehearsal.

## Static consumer contract test

`test-prod-profile-consumer-cutover.sh` must be self-contained and synthetic.
It must fail closed and cover:

1. exact target-file inventory and regular/non-symlink checks;
2. no literal `/opt/solarsage-astro/.env.production`, no
   `prod_env_load`, no `source ...env` and no `--env-file ...current/*.env` in
   the target units/scripts/host-preflight (the legacy loader/deploy files are
   explicitly excluded and listed in the test);
3. API exact `EnvironmentFile=current/api.env` and no cross-profile file;
4. sidecar exact `EnvironmentFile=current/sidecar.env` and no source env;
5. DB all three commands contain runner `db`, `--env-file /dev/null`, canonical
   compose file and `db`, with no checkout/current `--env-file`;
6. backup/maintenance ExecStart exact runner `backup` argv;
7. context bridge expected profile per script and no duplicate bridge;
8. host-prepare calls `prod-env-prepare --check`, runner offsite preflight and
   runner DB Compose config, never loader/source;
9. `systemd-analyze verify` for every changed unit when available, using only
   repository fixtures and no install/start/reload;
10. Bash/Python syntax, GRACE contract/map markers and fingerprint inventory.

Every structural assertion should use stable paths/argv/attributes, not an
incidental natural-language string.

## Dynamic synthetic profile proof

In the same harness or a separate clearly owned block:

- create a root:astro-style sandbox generation using C1A install-set (synthetic
  values only);
- use a copied wrapper with exact one-line canonical path substitution;
- use fake `docker`, `pg_dump`, `pg_restore`, `pg_isready`, `restic`,
  `systemctl`, `runuser` and credential files;
- prove DB Compose receives the decoded special password through the runner and
  `--env-file /dev/null` round-trips it exactly (compare a hash/boolean, never
  print the value);
- prove direct backup/offsite/restore invocation re-enters the wrapper once,
  receives only backup keys and preserves argv;
- prove nested maintenance/check and restore/backup calls do not recurse;
- prove a checkout `.env.production` fixture cannot affect any migrated
  consumer (create a canary only in a private sandbox; never the repository
  root);
- prove missing current/profile/runner/marker fails before fake DB/Restic
  command execution;
- prove no source token/password appears in stdout/stderr, argv logs, filenames
  or leftovers.

Do not call live systemd, Docker daemon, database or Restic.

## Existing regression harness migration

Update old backup/offsite/restore tests additively:

- remove mock `prod_env_load` and `.env.production` assumptions for migrated
  scripts;
- provide synthetic profile context through a copied runner or explicit
  marker+variables in the test child;
- retain all existing failure injection, lock, signal, Restic argv, restore
  confirmation and no-side-effect assertions;
- no test may make a production script green by defining a forbidden global
  source path or a production override.

Do not delete old tests or lower case counts.

## Acceptance commands

Run from repository root with true exit codes, no `tail` masking:

```bash
bash -n \
  scripts/lib/prod-profile-context.sh \
  scripts/prod-backup.sh \
  scripts/prod-offsite-check.sh \
  scripts/prod-offsite-maintenance.sh \
  scripts/prod-db-restore.sh \
  scripts/prod-host-prepare.sh \
  scripts/tests/test-prod-profile-consumer-cutover.sh

systemd-analyze verify \
  infra/systemd/solarsage-api.service \
  infra/systemd/solarsage-sidecar.service \
  infra/systemd/solarsage-db.service \
  infra/systemd/solarsage-backup.service \
  infra/systemd/solarsage-backup-maintenance.service

bash scripts/tests/test-prod-profile-consumer-cutover.sh
bash scripts/tests/test-prod-profile-consumer-cutover.sh
bash scripts/tests/test-prod-backup-offsite.sh
bash scripts/tests/test-prod-backup-state-machine.sh
bash scripts/tests/test-prod-backup-units.sh
bash scripts/tests/test-prod-db-restore-safety.sh
bash scripts/tests/test-prod-offsite-check.sh
bash scripts/tests/test-prod-offsite-maintenance.sh
bash scripts/tests/test-prod-host-offsite-routing.sh
bash scripts/tests/test-prod-deploy-source-loader.sh
bash scripts/prod-infra-fingerprint.sh
git diff --check
```

The handoff must include exact changed files, static no-bypass counts, systemd
verify rc, synthetic Compose password hash comparison, context recursion proof,
all test rc/case counts, stale process/temp scan and explicit remaining C1B3/C2
items. Stop after handoff. Do not commit, push or apply production.
