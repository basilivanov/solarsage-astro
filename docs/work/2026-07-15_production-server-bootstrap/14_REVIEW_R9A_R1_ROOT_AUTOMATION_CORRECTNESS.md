# Review R9A-R1 — root automation correctness

Дата: 2026-07-15

R9A architecture is accepted, implementation is not. Fix the blockers below without changing the design or touching other files.

## Scope

```text
scripts/prod-infra-fingerprint.sh
scripts/prod-host-prepare.sh
scripts/prod-deploy.sh
infra/systemd/solarsage-db.service
infra/systemd/solarsage-api.service
infra/systemd/solarsage-backup.service
docs/PRODUCTION_RUNBOOK.md
```

Preserve R3–R8B. No commit/push/server access/live apply/deploy. No restore/reset/checkout/clean.

## 1. Fingerprint must be pure and write nothing

Current `prod-infra-fingerprint.sh` uses `mktemp` and writes framed data to disk, contradicting its contract and R9A.

Required:

1. First prevalidate the entire ordered file list before producing any stdout.
2. After all files exist as regular files, stream framed path/size/content records directly through a pipe/group into `sha256sum`; no temp file, redirection target, `mktemp`, trap or filesystem write.
3. `set -o pipefail` must make any framing/read failure non-zero.
4. Missing file -> non-zero and no stdout hash.
5. Success -> exactly one 64-lowercase-hex line.
6. Correct dependency comments (`bash`, `sha256sum`, `stat`; plus any actual command used).

Keep deterministic ordered paths and collision-unambiguous NUL framing.

Set working modes now:

```text
scripts/prod-infra-fingerprint.sh 0755
scripts/prod-host-prepare.sh       0755
infra/systemd/solarsage-db.service 0644
```

## 2. Parser and root-only lock

Argument validation must happen before root check:

- no args/unknown/extra -> exit 2 even for non-root;
- valid `--check`/`--apply` as non-root -> root-required exit 1.

Do not use a lock path under world-writable `/run/lock`, where an unprivileged stale file can interfere. After root validation use:

```text
/run/solarsage-host-prepare.lock
```

`/run` is root-owned. Open once and `flock -n`; do not replace/truncate an inode after lock acquisition. No `mkdir /run/lock`.

## 3. Run Git/tool checks in the real runtime context

Root Git against astro-owned repo currently triggers `dubious ownership`.

- All repository Git checks must use `runuser -u astro -- git -C /opt/solarsage-astro ...`.
- Apply dirty gate must be NUL-safe for non-ignored untracked names; no `wc -l` representation.
- Do not use `sudo -u`; use root's `runuser` and add it to prerequisites.

pnpm/Corepack selects the package-manager version from the current project. Validate exact pnpm as the runtime user and from `APP_ROOT`, for example:

```bash
runuser -u astro -- bash -c 'cd /opt/solarsage-astro && pnpm --version'
```

Do the Node check in a stable PATH/runtime context too. Add all actually used commands to prerequisites, including `bash`, `flock`, `getent`, `stat`, `install`, `runuser`, `systemd-analyze` and others used by the script.

## 4. Env contract must fail predictably and never parse secrets with xargs

Current assignment under `set -e` can terminate before `report_error`, and `xargs` treats quotes/backslashes in secret values as syntax.

Required:

- run env validator in an explicit `if ...; then ... else report_error ... fi` flow so failure is reported and aggregated;
- provide a stable minimal PATH to `env -i`;
- use Bash whitespace trimming, not `xargs`/echo pipelines, for provider and key checks;
- require non-empty `DATABASE_URL` before checking it is non-SQLite;
- normalize only a leading `@` from BOT_USERNAME, not every `@` character;
- never print secret values; failure output may name only the failed variable/contract.

## 5. Use exact installs and safe rollback

Replace repository-to-system `cp + chown + chmod` sequences with `install -o ... -g ... -m ...` for units, wrapper, sudoers and Nginx.

### Sudoers

- validate repo template before mutation;
- preserve an existing live policy in a root-only temporary backup;
- install candidate;
- validate full `/etc/sudoers`;
- on failure restore exact previous policy, or remove candidate only if there was no previous file;
- fail non-zero. Never leave the host with a deleted previously-working policy.

### Nginx

- preserve existing live config/symlink state before replacement;
- install candidate and exact symlink;
- run `nginx -t`;
- on failure restore previous config/symlink state and fail;
- reload only after successful test.

Temporary backups must be mode 0600/root and removed by trap/cleanup. Do not print their contents.

## 6. DB apply must really apply compose and fail before marker

`systemctl start` is a no-op for an already-active oneshot. Required:

- if `solarsage-db.service` active -> `systemctl reload solarsage-db.service`;
- otherwise -> `systemctl start solarsage-db.service`;
- only this DB service may start/reload;
- bounded Docker/systemd health timeout is a hard error, not warning;
- remove unused sourcing of `POSTGRES_USER`/`POSTGRES_DB` from the wait loop;
- DB failure must occur before any fingerprint marker write.

## 7. Fingerprint marker must be the final committed state

Current code writes marker before the shared verification, so a failed enable/mode/symlink check can leave a false current marker.

Refactor verification into a reusable function or equivalent:

1. After apply operations and DB health, verify all installed state except the fingerprint marker.
2. If any verification fails, exit without replacing existing marker.
3. Atomically write new marker only after step 1 succeeds.
4. Run full verification including marker equality.
5. Only then print `HOST PREPARE PASS`.

`--check` runs full verification directly and performs no persistent configuration mutation.

Verification must additionally prove owner/mode for installed units, wrapper, sudoers, Nginx config and exact sites-enabled symlink target—not only file bytes.

## 8. Host check/apply safety

Preserve:

- no start/restart/stop of canonical API/sidecar/frontend;
- exact app `enable` without `--now`;
- exact legacy stop/disable only;
- no Git network or checkout operations;
- certificate check only, no Certbot;
- no build/migration/backup/deploy.

Use `install -d` for owned directories.

## 9. Deploy fingerprint gate exactness

Keep stage/order. Use the executable fingerprint script directly rather than `bash script` after ensuring mode 0755. Validate applied marker as one exact 64-hex record; do not accept extra lines/bytes. No env load before the gate.

## 10. Runbook completion

Use absolute commands in bootstrap examples.

Document the missing operational invariant:

- for code-only commit with unchanged fingerprint: manual Deploy Production is enough;
- for a commit changing any fingerprint-owned path: checkout/fetch that exact target on the host without launching app, run root `prod-host-prepare.sh --apply`, confirm `--check`, then trigger the pinned manual deploy;
- a fingerprint mismatch is intentional fail-closed protection.

Remove duplicate manual repository-owned wrapper/sudoers installation from transport section or mark it strictly as emergency explanation. Normal path must be host prepare. Keep only external key/GitHub-environment steps as manual.

List exact prerequisite versions/commands instead of “required commands must be installed”.

## 11. Checks

Repeat all R9A checks plus:

- fingerprint script contains no `mktemp`, temp output file or write redirection;
- missing owned file in temporary complete copy -> non-zero and zero stdout bytes;
- no args parser -> 2; valid mode non-root -> 1;
- no `/run/lock/solarsage-host-prepare.lock`;
- no `sudo -u`, `wc -l` untracked gate, or repository install via `cp`;
- pnpm check explicitly runs from `APP_ROOT` as astro;
- DB active branch uses reload, inactive uses start;
- DB health failure cannot reach marker write (sentinel harness/static control-flow proof);
- canonical app services have no start/restart/stop calls;
- installed owner/mode/symlink checks exist;
- marker is written after pre-marker verification.

Do not run live `--apply`. Return detailed handoff and stop.
