# R12-R1 review — backup/restore runtime safety

## Статус

R12 не принят. Исправь только перечисленные дефекты, сохрани scope и принятый R11. Commit/push/production/real backup/restore/restic init/prune запрещены.

## 1. Убрать `local` вне функции в restore

`scripts/prod-db-restore.sh` содержит top-level `local svc_state` и `local token_input`. `bash -n` это не ловит, runtime restore сломан. Вынеси restore flow в `run_restore()`/`main()`; `local` только внутри функций.

## 2. Restore lock и user boundary

- Require `id -un == astro` в backup/verify/restore/offsite scripts;
- lock restore: `/var/backups/solarsage/restore.lock` mode 0600 после проверки backup dir, не `/run`;
- backup lock в backup dir явно документировать;
- no root execution fallback.

## 3. Safe env loading — новых `source` быть не должно

Создай source-only helper `scripts/lib/prod-env-loader.sh` с функцией `prod_env_load FILE DOMAIN`:

- проверяет regular non-symlink;
- запускает non-executing Python parser на временном mode-0600 файле;
- rejects invalid/duplicate keys, export/heredoc, substitutions, control chars, backslash, shell control operators, malformed quotes;
- validates APP_ENV/domain/DEV_MODE/SESSION_COOKIE_SECURE, DB non-SQLite, BOT_USERNAME, active LLM key;
- validates `OFFSITE_BACKUP_ENABLED` only `true|false`, optional offsite paths without whitespace/control;
- emits NUL-separated `KEY=VALUE` records to private temp; shell imports via `export "$assignment"`, no `eval`/`source`;
- removes temp on success/failure/signal; never prints assignments/values.

Use helper in backup, restore, offsite-check, maintenance. Add to host inventory/bash-n/fingerprint. Existing host parser remains unchanged.

## 4. Local backup publish all-or-nothing

Current code moves final dump before checksum and can leave orphan on later failure.

Исправить:

1. require user astro, env owner `astro:astro`, backup dir real `astro:astro:700` (create only when missing; wrong type fails);
2. acquire lock before timestamp/temp paths;
3. `mktemp` dump/checksum inside backup dir, immediate 0600; no deterministic temp names;
4. pg_dump -> temp; non-empty/type check; pg_restore-list;
5. checksum temp dump to temp checksum and verify while temp;
6. publish pair with explicit partial-publish cleanup; no orphan final file;
7. post-publish checksum + pg_restore;
8. any failure before commit removes current timestamp pair and temps only;
9. commit flag only after final checks.

Restore backup unit `UMask=0077`. Add actual command dependencies (`timeout`, etc.).

## 5. Retention correctness

- dump/checksum owner `astro:astro`, mode 0600;
- report orphan old dumps and orphan checksums;
- pair deletion through private quarantine rename, then delete; restore names on rename failure where possible;
- no symlink following;
- retention failure never removes the new committed pair.

## 6. Verifier correctness

- require user astro and backup dir real `astro:astro:700`;
- require dump/checksum owner `astro:astro`, mode 0600;
- checksum file exact one line: 64 lowercase hex + whitespace + exact dump basename; reject arbitrary/`../../` filename before `sha256sum -c`;
- reject symlink paths;
- preserve latest-valid selection; safe basename/size output only.

Harness must really cover bad digest, malicious checksum filename, owner/mode, missing checksum, empty dump, symlink, invalid basename, valid pair and latest selection. Current sha mock always succeeds when file exists and does not test bad checksum — fix it or use real sha256sum.

## 7. Restore safety

- `--plan` first verifies target and prints sanitized canonical path/basename;
- use env loader, not source;
- service states: active fatal; inactive/failed/deactivating allowed; unknown/not-found fatal;
- writable restore lock before pre-restore backup;
- parse exactly one anchored `FINAL_DUMP: <canonical path>` line, then verify;
- second exact TTY confirmation;
- terminate-connections psql failure is fatal;
- use psql variable binding (`-v target_db=...`, `:'target_db'`), no direct SQL interpolation;
- cleanup trap unsets PGPASSWORD on every exit;
- no automatic app stop/start/restart or automatic rollback claim;
- bounded connection command; no arbitrary short timeout for large pg_restore.

## 8. Offsite/config integration

- loader helper everywhere; password/key/known_hosts owner+mode and real non-symlink;
- reject whitespace/control/leading `-` path values used in `sftp.args`;
- bounded timeout on network operations;
- `restic forget` also `--no-cache` because ProtectHome=true;
- host final verification must actually run offsite checker as astro or safely import boolean; root shell `${OFFSITE_BACKUP_ENABLED}` is unset and current check is dead;
- disabled offsite warning is explicit; production launch checklist requires enabled.

## 9. Systemd/GRACE

- Maintenance service/timer need AI_HEADER + module contract/map, UMask=0077, journal output, network-online ordering, explicit `Unit=`;
- no app dependencies/calls;
- host inventory/systemd/fingerprint include all new runtime files consistently.

## 10. Acceptance

- bash-n env loader, backup, verifier, restore, offsite check/maintenance and test harness;
- systemd-analyze verify all four backup units;
- run verifier harness;
- run invalid-arg tests;
- run fingerprint and `git diff --check`;
- prove no `source "$ENV_FILE"`, no top-level local, no eval/rm-rf backup/app systemctl/secret output.

Do not run real backup, restore, Restic init/prune, or production command. Handoff maps every issue to exact fix.
