# Architecture — immutable production releases and asynchronous deploy

## Decision

Keep `/opt/solarsage-astro` as the private Git/source-control checkout. Do not turn it into `current`. Runtime artifacts move into immutable per-SHA release directories. This preserves existing source-readiness/Git transport while removing in-place venv/Next mutation and making code rollback atomic.

Implementation is split into slices; no production launch is part of this document.

## Filesystem layout

```text
/opt/solarsage-astro/                       source checkout + .git only
/opt/solarsage-runtime/
  releases/<40-lowercase-sha>/
    node_modules/
    .next-prod/
    apps/api/.venv/
    apps/solarsage/venv/
    release.json
  current -> releases/<sha>
  previous -> releases/<sha>

/etc/solarsage/env/...                      profile files from 70_TZ
/etc/solarsage/infra/docker-compose.yml     host-installed DB definition
/etc/solarsage/infra-fingerprint
/var/lib/solarsage/deploy/request.json
/var/lib/solarsage/deploy/status.json
/var/lib/solarsage/audit/
/var/cache/solarsage/{pnpm,pip}/
/var/backups/solarsage/
/opt/sweph/ephe/
```

Never share between releases: `.next-prod`, `node_modules`, Python venvs, source/canons or generated `next-env.d.ts`. Shared: DB volume, backups, ephemeris, secrets and explicit audit data.

Control scripts used by systemd should be installed root-owned under `/usr/local/libexec/solarsage/`; units must not execute mutable scripts from source checkout/current.

## Candidate creation

Use detached Git worktrees:

```text
git -C /opt/solarsage-astro worktree add --detach \
  /opt/solarsage-runtime/releases/<sha> <sha>
```

Candidate starts with `.release-incomplete`; `current` never points to it. Exact path/SHA validation prevents traversal/symlink attacks. Failed candidate removal uses validated `git worktree remove --force` only.

## Sanitized build before secrets

Deploy worker has no shared production EnvironmentFile. Build children run through `env -i` with trusted HOME/PATH/locale and explicit public build variables only.

Candidate phases:

1. validate lowercase SHA, private source and exact remote main;
2. create detached worktree;
3. candidate infra fingerprint vs applied host fingerprint — mismatch becomes `blocked_infra` before dependency install/secret load;
4. `pnpm install --frozen-lockfile` and both venv installs with sanitized env;
5. production guardrails/contracts/type/build;
6. restore only exact expected generated file changes and prove source cleanliness;
7. offline API configuration/canon import and sidecar/ephemeris oracle probe;
8. atomically write non-secret `release.json`, remove `.release-incomplete`.

No `.env.production` is copied/linked into source or release. See `70_TZ...` for profile execution.

## Release manifest

`release.json` is immutable and non-secret. Minimum:

```text
schema_version
release_sha
created_at_utc
source_origin_identity
infra_fingerprint
frontend_build_identity
api_package_identity
sidecar_package_identity
calculation_version
alembic_heads
migration_mode
canon/cache identity versions
complete=true
```

Manifest itself receives SHA256 and is validated by runtime runner. No credentials, URLs with auth or raw env.

## Runtime pinning

Units do not directly use unresolved `current` as WorkingDirectory. A root-owned runner:

1. resolves `current` exactly once with `readlink -f`;
2. requires path exactly `releases/<40hex>`;
3. verifies complete manifest and basename/SHA equality;
4. sets derived `RELEASE_SHA`, `SOLARSAGE_GIT_SHA`, `GRACE_SERVICE_VERSION`;
5. `cd` to the resolved release and `exec` exact binary path.

This prevents lazy imports/file reads from moving to a new tree after symlink promotion. Units use `ReadOnlyPaths=/opt/solarsage-runtime/releases`.

API/sidecar/frontend health must return exact full release SHA. Sidecar additionally returns shared calculation version; deploy asserts JSON identity, not only HTTP 200.

DB and backup/maintenance units use host-installed infra/libexec paths, not code release.

## Atomic current/previous promotion

Under global maintenance lock:

1. resolve old `current`;
2. validate complete candidate;
3. atomically set `previous` to old via temporary symlink + `mv -Tf`;
4. atomically set `current` to candidate;
5. restart sidecar, API, frontend sequentially;
6. assert exact candidate SHA/health and public HTTPS.

On health failure with no migration or expand-compatible migration:

- flip `current` back to old;
- restart old stack;
- assert old exact SHA;
- status `rolled_back`;
- retain failed candidate for forensic inspection.

First release may have no previous. GC never deletes current/previous/running request and keeps at least two recent successful releases.

Manual rollback rotates symlinks through the same worker/state machine; never performs `git checkout` in live runtime.

## Migration policy

Routine deploy permits only:

- `none`;
- `expand`, explicitly backward-compatible with previous code.

Each pending Alembic head requires a reviewed repository policy record, e.g.:

```json
{"head":"0020...","mode":"expand","previous_code_compatible":true}
```

Unknown/pending migration without exact policy fails closed.

Migration sequence:

1. verified offsite/local backup while old app runs;
2. if migration pending, enable maintenance 503 flag and stop API/frontend;
3. create quick local **no-retention** pre-migration dump + provenance manifest;
4. candidate Alembic venv upgrades and verifies exact head;
5. promote/restart/health;
6. remove maintenance only after full success.

If expand migration succeeds but new code health fails, old code must remain compatible; rollback code only, schema stays expanded.

Contract/drop/rename/destructive migrations are separate maintenance operations after compatibility window and restore drill. No automatic downgrade/destructive restore. Failure stays `recovery_required` with maintenance enabled.

Nginx maintenance flag `/run/solarsage/maintenance` returns controlled 503 + `Retry-After` for app routes instead of accidental 502.

## Asynchronous deploy control plane

Long build/backup must not live inside a 45-minute GitHub SSH session.

Fixed unit:

```text
solarsage-deploy.service
Type=oneshot
User=astro
TimeoutStartSec=4h
ExecStart=/usr/local/libexec/solarsage/deploy-worker
```

Forced-command surface evolves in a separately reviewed wrapper contract:

```text
deploy <sha>           queue exact request and start unit --no-block
deploy-status <sha>    read safe status only
source-check <sha>     current readiness behavior
rollback <sha>         optional separate reviewed slice
```

Request/status files are atomic, root/astro mode-controlled and non-secret. Status stages:

```text
queued fetching source_verified blocked_infra building built backing_up
maintenance migrating promoting restarting verifying succeeded rolled_back
failed recovery_required
```

Safe fields only: request ID/action/SHA/stage/timestamps/current/previous SHA/error code/migration mode/backup manifest basename.

GitHub workflows for 2000-minute budget:

- queue workflow timeout ~5m and normally consumes <1 minute;
- separate manual status workflow ~5m;
- server does build/backup; no 2-hour hosted polling;
- CI required on protected main exact SHA; deploy does not rerun full CI;
- optional bounded 5–10m poll only if a single badge is required.

## Infra fingerprint interaction

Fingerprint includes worker/runner/unit/sudoers/tmpfiles/Nginx maintenance changes. Candidate computes its own expected fingerprint. Mismatch leaves current unchanged and status `blocked_infra`.

Host-prepare should accept explicit trusted source root for candidate templates, apply root transaction, update applied fingerprint, then operator requeues candidate.

## Implementation slices

### A. Filesystem and runtime pinning

- runtime layout/tmpfiles;
- env profiles outside checkout;
- release runner;
- update API/sidecar/frontend/DB/backup units;
- controlled first-release migration.

### B. Immutable builder and promotion

- worktree candidate + sanitized build;
- manifest/current/previous/GC;
- fingerprint block;
- exact health and automatic code rollback.

### C. Async control plane

- deploy unit/request/status worker;
- separately hardened forced wrapper/sudoers;
- queue/status workflows.

### D. Migration/maintenance

- migration policy;
- global maintenance lock;
- Nginx maintenance flag;
- pre-migration no-retention dump;
- expand rollback/contract refusal.

### E. Runbook and drills

- first deploy, normal deploy, status, rollback, blocked_infra, recovery_required;
- sandbox mutation tests and test-server rehearsal.

## Acceptance tests

- secret canary absent from fake pnpm/pip/build env/output;
- build failure leaves current unchanged;
- incomplete candidate cannot promote;
- SHA/path/symlink validation;
- double queue/idempotence/global lock;
- atomic current/previous rotation;
- runner resolves release once;
- candidate health failure restores old exact health;
- infra mismatch causes no build/secret/restart;
- pending migration without policy rejected;
- expand success + app failure rolls code back only;
- migration failure leaves old current + maintenance + recovery_required;
- SSH parent returns while systemd worker continues;
- safe status has no secrets/raw command;
- GC protects current/previous/running;
- systemd/nginx syntax and mutation harnesses.

Server-side immutable build is the pragmatic first production architecture for the current budget. Signed prebuilt artifacts can replace it later after dependency locks/artifact signing exist.
