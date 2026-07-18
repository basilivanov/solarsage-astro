# Review R9A-R2 — last root automation edge cases

Дата: 2026-07-15

Apply only these final corrections. Preserve all R3–R9A-R1 behavior.

## 1. Fingerprint stdout must be transactional

The streaming group currently pipes directly to stdout. If a file disappears or `cat/stat` fails after prevalidation, `sha256sum` can still emit a hash before pipefail returns non-zero.

Capture the pipeline result in a shell variable and print it only after the pipeline succeeds:

```bash
if ! fingerprint=$( { ...framing...; } | sha256sum | cut -d' ' -f1 ); then
  exit 1
fi
printf '%s\n' "$fingerprint"
```

No temp file and no filesystem write. Missing/racing file -> non-zero and zero stdout bytes.

## 2. Common preflight must aggregate missing dependencies

After reporting missing commands/user, do not invoke dependent commands under `set -e`.

Guard checks so a clean Ubuntu failure reports all issues and exits through the aggregate `errors` path:

- only run `runuser` Git/pnpm/node checks if `runuser`, user and APP_ROOT are present;
- only run Docker compose validation if `docker` exists and compose works;
- only run systemd verification if `systemd-analyze` exists;
- only run visudo check if `visudo` exists;
- only run certificate `openssl` check if `openssl` exists;
- avoid numeric comparison on empty/malformed Node version; report invalid version safely.

Require non-empty `DATABASE_URL` in host env contract (then reject sqlite).

## 3. Exact runtime modes

Use `chmod 0755` for both scripts and `chmod 0644` for `solarsage-db.service` in the actual worktree. Verify with `stat` before handoff.

## 4. Nginx rollback must cover all states

Before candidate install, preserve:

- existing `sites-available` regular file bytes/owner/mode;
- existing `sites-enabled` symlink target;
- existing `sites-enabled` regular-file bytes/owner/mode if it is unexpectedly a regular file.

If candidate `nginx -t` fails, or `systemctl reload nginx` fails:

- restore exact previous available file state;
- restore exact previous enabled symlink or regular file state;
- attempt a reload of restored valid config;
- remove temporary backups;
- exit non-zero without writing fingerprint.

Do not silently delete a previous regular enabled file.

## 5. Fingerprint marker rollback/format

Before writing a new marker, preserve any existing marker bytes/owner/mode in a root-only temporary backup. If final verification fails after replacement, restore the previous marker exactly (or remove it if none existed), then exit non-zero.

Verification of marker must require exactly one 64-lowercase-hex line using a line-aware Bash read/array, not command substitution that accepts extra lines after stripping newlines. Check owner `root:root`, mode `0644`.

## 6. Final safety assertions

```bash
! grep -F 'mktemp' scripts/prod-infra-fingerprint.sh
! grep -F '/run/lock/solarsage-host-prepare.lock' scripts/prod-host-prepare.sh
! grep -F 'sudo -u' scripts/prod-host-prepare.sh
! grep -F 'wc -l' scripts/prod-host-prepare.sh
! grep -E 'systemctl (start|restart|stop) solarsage-(api|sidecar|frontend)' scripts/prod-host-prepare.sh
stat -c '%a' scripts/prod-infra-fingerprint.sh scripts/prod-host-prepare.sh infra/systemd/solarsage-db.service
```

The allowed `mktemp` calls in host prepare remain allowed; only the pure fingerprint script must have none.

Repeat R9A fingerprint/host-parser/marker-before-failure harnesses and all previous R8/R7 checks. No live apply, server mutation, commit or push. Handoff and stop.
