# R12 — backup/restore correctness и offsite readiness

## Роль и ограничения

Ты кодер, модель `cliproxy/gemini-3-flash-agent`. Реализуй ровно этот infra slice.

Запрещено: commit/push/merge, SSH/подключение к production, чтение/печать env/secrets, запуск destructive restore, остановка/запуск app services, изменение прикладного backend/frontend.

Не трогай frozen paths: `.grace/`, `artifacts/design/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, `skills/`.

Сохраняй GRACE-разметку в новых/существенно изменённых файлах. Production application launch остаётся ручным и в R12 не выполняется.

## Цель

Получить проверяемую цепочку:

1. ежедневный локальный PostgreSQL dump создаётся атомарно и проверяется `pg_restore --list`;
2. checksum и retention не оставляют ложный «успех»;
3. отдельный read-only verifier может доказать, что dump пригоден для восстановления;
4. destructive restore имеет безопасный manual boundary и всегда создаёт pre-restore backup;
5. зашифрованная offsite-копия включается оператором через Restic (SFTP или S3-compatible), без хранения ключей в Git;
6. systemd умеет запускать backup/maintenance, но ни один unit не трогает app services.

## Canonical backup contract

- local dir: `/var/backups/solarsage`, real directory `astro:astro`, mode `0700`;
- dump name: `db-YYYYMMDDTHHMMSSZ.dump`;
- checksum: adjacent `db-...dump.sha256`;
- both final files mode `0600`, no symlinks;
- PostgreSQL: `127.0.0.1:5433`, custom format (`pg_dump -F c`);
- local retention: 14 days, but do not delete old good backups if current offsite transfer failed;
- lock: `/run/solarsage-backup.lock` (or another root-owned/non-blocking canonical lock usable by `astro`; document exact choice);
- no raw password/token/API key in stdout/journal.

## 1. `scripts/prod-backup.sh`

Сохрани обычный вызов без аргументов и добавь только:

```text
scripts/prod-backup.sh
scripts/prod-backup.sh --local-only
```

Другие args — exit 2. `--local-only` нужен для pre-restore safety backup и не должен запускать offsite transfer.

### Preflight

До dump:

- root? Скрипт запускается как `astro` через systemd, не делать root-only;
- exact env file regular non-symlink, owner `astro:astro`, mode 0600/0640;
- backup dir regular non-symlink, owner/mode exact (создать idempotently только если отсутствует);
- required commands: `pg_dump`, `pg_restore`, `pg_isready`, `sha256sum`, `stat`, `find`, `mv`, `rm`, `mktemp`, `install`, `flock`, `date`, `hostname`;
- DB readiness: bounded `pg_isready -h 127.0.0.1 -p 5433`, no infinite retries;
- validate `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`; не печатать values;
- `PGPASSWORD` только в process environment, `unset` в `EXIT` cleanup.

Существующий env parser/production contract не ослаблять. Не использовать `eval`.

### Atomic local dump

1. Acquire non-blocking lock before timestamp.
2. Create temp dump and temp checksum **inside** backup dir, mode 0600, names beginning with `.solarsage-` (not matching retention globs).
3. Run `pg_dump -h 127.0.0.1 -p 5433 -U ... -F c -d ... -f TMP_DUMP`.
4. Require regular non-symlink dump and size > 0.
5. Run `pg_restore --list TMP_DUMP` and require exit 0 before publishing.
6. `chmod 0600 TMP_DUMP`; atomic `mv -fT TMP_DUMP FINAL_DUMP`.
7. Generate checksum for the final dump to temp checksum, chmod 0600, atomic `mv -fT` to FINAL_SHA.
8. Re-run `sha256sum -c FINAL_SHA` and `pg_restore --list FINAL_DUMP` after publish.
9. Set `LOCAL_BACKUP_COMMITTED=1` only after all local checks pass.
10. On failure before commit remove only temp/current timestamp files; never delete older backups.

If offsite later fails, keep the valid local backup, exit nonzero and emit a safe event/message indicating `offsite_transfer_failed` (no secret/path credentials). Do not claim overall success.

### Retention

After local commit and successful offsite step (or `--local-only`):

- delete only matching old dump/checksum pairs older than 14 days;
- never delete a dump while its checksum remains or vice versa;
- use a safe two-pass pair list or delete pair only when both are present;
- ignore symlinks/unexpected file types and report them;
- retention failure makes script nonzero but must not remove the newly committed valid backup.

## 2. `scripts/prod-backup-verify.sh`

New read-only verifier, exact CLI:

```text
scripts/prod-backup-verify.sh --latest
scripts/prod-backup-verify.sh --file /var/backups/solarsage/db-....dump
```

No `--restore`, no mutation, no env secret output. Reject paths outside backup dir, symlinks, directories, basename not matching canonical dump pattern. For selected dump:

- adjacent checksum exists, regular, mode 0600;
- `sha256sum -c` passes;
- `pg_restore --list` passes;
- dump is non-empty and owner/mode exact;
- `--latest` selects newest valid matching pair, not merely newest filename; if none valid — nonzero;
- output only safe metadata (basename, bytes, checksum pass, restore-list pass).

Add a small temp-dir test fixture/harness using mocked `sha256sum`/`pg_restore` binaries in PATH or generated tiny custom dump if available. It must cover missing checksum, bad checksum, empty dump, symlink, invalid basename and valid pair; no `/etc`, no production env.

## 3. Safe manual restore boundary

New `scripts/prod-db-restore.sh` with **only**:

```text
scripts/prod-db-restore.sh --verify /var/backups/solarsage/db-....dump
scripts/prod-db-restore.sh --plan /var/backups/solarsage/db-....dump
scripts/prod-db-restore.sh --restore /var/backups/solarsage/db-....dump --confirm-production-db-replace
```

Rules:

- `--verify` delegates to read-only verifier;
- `--plan` is read-only and prints ordered human instructions, never SQL/write/systemctl;
- `--restore` requires exact confirmation token and an interactive TTY (`[ -t 0 ] && [ -t 1 ]`), otherwise exit 2;
- before any destructive SQL, call `prod-backup.sh --local-only` and verify the resulting dump;
- require selected dump checksum + `pg_restore --list` pass;
- require production env contract (`APP_ENV=production`, exact domain, non-SQLite DB) using the existing non-executing parser or a safe equivalent;
- require `solarsage-api.service`, `solarsage-sidecar.service`, `solarsage-frontend.service` already inactive; do **not** stop or restart them automatically;
- acquire restore lock;
- show only basename/size and ask for the exact confirmation token a second time; never show env values;
- if confirmed, use bounded `psql` to terminate connections and `pg_restore --clean --if-exists --no-owner --no-privileges` into the existing DB;
- on any failure, exit nonzero and print the pre-restore dump path basename; do not pretend automatic rollback succeeded;
- never restart app services. Operator must run post-restore migrations/health/deploy manually.

The runbook must state that a restore from an older app commit requires checking out the matching commit and that schema/data rollback is not equivalent to code rollback.

## 4. Optional encrypted offsite via Restic

Do not hardcode a provider or server. Use these env keys (values are operator-owned; never commit them):

- `OFFSITE_BACKUP_ENABLED=false|true` (default false for dev/test; production launch checklist must require true);
- `OFFSITE_RESTIC_REPOSITORY` (`sftp:...`, `s3:...`, etc.);
- `OFFSITE_RESTIC_PASSWORD_FILE` (path only, e.g. `/etc/solarsage/backup/restic-password`);
- `OFFSITE_RESTIC_SSH_KEY` (required for `sftp:` only);
- `OFFSITE_RESTIC_KNOWN_HOSTS` (required for `sftp:` only);
- `OFFSITE_RESTIC_TAG=solarsage-prod`;
- retention values: daily 14, weekly 8, monthly 12, yearly 3.

Add `scripts/prod-offsite-check.sh --check`:

- read-only, exact args, no `restic init`;
- validates `restic` exists when enabled, repository/password file paths are regular non-symlinks, owner/mode safe (`astro` readable, private files 0600 or root:astro 0640), known_hosts 0644/0600;
- for `sftp:` build an argv-safe Restic option using official `-o sftp.args=...` (no `eval`, no shell interpolation), with `-i`, `IdentitiesOnly=yes`, exact `UserKnownHostsFile`, `StrictHostKeyChecking=yes`, `BatchMode=yes`;
- run bounded `restic snapshots --latest 1` with output suppressed/filtered; no password/repository secret output;
- disabled mode returns a clear non-success readiness code or documented warning, but local backup remains functional.

In `prod-backup.sh`, after local commit:

- if `OFFSITE_BACKUP_ENABLED=true`, invoke `restic backup --no-cache` for the dump and checksum;
- verify a snapshot exists (`restic snapshots --latest 1`);
- if offsite fails, keep local files and exit nonzero;
- if false, do not invoke restic.

Add `scripts/prod-offsite-maintenance.sh --run` (exact one arg, systemd/manual only):

- when enabled: `restic forget --prune` with the canonical retention and tag, then `restic check --no-cache`;
- when disabled: exit with safe readiness warning, no mutation;
- no app service calls.

Add:

- `infra/systemd/solarsage-backup-maintenance.service` (oneshot, User=astro, hardening, no app dependencies);
- `infra/systemd/solarsage-backup-maintenance.timer` (weekly, persistent, randomized delay, after daily backup window).

Do not run maintenance in the daily backup path; prune can be long.

Restic SFTP facts to encode in comments/runbook: repository password comes from `RESTIC_PASSWORD_FILE`; SFTP custom SSH arguments use Restic `-o sftp.args=...`; repository initialization is a one-time operator action outside this task.

## 5. Systemd/host integration

Update `infra/systemd/solarsage-backup.service`:

- retain User=astro, `ProtectHome=true`, `ProtectSystem=full`, `NoNewPrivileges`, `PrivateTmp`;
- add `WorkingDirectory=/var/backups/solarsage`;
- add `ReadWritePaths=/var/backups/solarsage` only (and any explicitly required cache/state dir; prefer `--no-cache` so no extra write path);
- no app service dependencies beyond existing DB requirement.

Update `scripts/prod-os-bootstrap.sh` base packages to include `postgresql-client-16` (already), `restic`, `openssh-client` if offsite SFTP is supported. Do not add Docker group access.

Update `scripts/prod-host-prepare.sh`:

- inventory and `bash -n` new production scripts and maintenance units;
- verify systemd units with `systemd-analyze verify`;
- install/verify new maintenance unit/timer exact owner/mode;
- enable/start only backup timer and maintenance timer (never app services);
- when `OFFSITE_BACKUP_ENABLED=true`, require restic/config files and run `prod-offsite-check.sh --check` as `astro`; when false, report safe readiness warning (not secret values);
- add maintenance templates to runtime fingerprint because they affect host state;
- do not create password/key files automatically.

## 6. Runbook update

Replace unsafe restore snippet that directly sources env in an ad-hoc shell with canonical commands:

1. `scripts/prod-backup-verify.sh --latest`;
2. `scripts/prod-db-restore.sh --plan <dump>`;
3. ensure app services inactive manually;
4. `scripts/prod-db-restore.sh --restore <dump> --confirm-production-db-replace` in a TTY;
5. inspect migration head/checkout matching commit;
6. manually deploy/restart only after owner decision.

Document:

- local backup success versus offsite success are separate states;
- one-time Restic repository init and password/key placement are manual secret boundaries;
- exact file permissions and no Git storage for restic password/private key;
- weekly maintenance timer and a manual `--run` check;
- test restore drill procedure on a non-production database/server;
- RPO/RTO assumptions: local 14 days, offsite retention policy, and alert requirement when offsite is disabled/fails;
- no blanket cache invalidation; migrations/versioned cache contract controls invalidation.

## 7. Tests/evidence

Required:

```bash
bash -n scripts/prod-backup.sh
bash -n scripts/prod-backup-verify.sh
bash -n scripts/prod-db-restore.sh
bash -n scripts/prod-offsite-check.sh
bash -n scripts/prod-offsite-maintenance.sh
bash -n scripts/tests/test-prod-backup-verify.sh
systemd-analyze verify infra/systemd/solarsage-backup.service infra/systemd/solarsage-backup.timer infra/systemd/solarsage-backup-maintenance.service infra/systemd/solarsage-backup-maintenance.timer
scripts/tests/test-prod-backup-verify.sh
git diff --check
```

Also prove with `rg` that new scripts contain no `eval`, `rm -rf` on backup paths, app `systemctl stop/start/restart`, or secret printing. Do not run a real backup, Restic init, maintenance prune, restore, or production command.

## Handoff

List files, exact backup/restore/offsite state machine, tests/results, and the manual operator inputs still required (offsite destination, Restic password, SSH key/known_hosts or S3 credentials). No commit/push.
