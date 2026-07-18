# Report 180 — minimal host runtime convergence (TZ 179)

Status: all six blockers A–F from `179_TZ_MINIMAL_HOST_RUNTIME_CONVERGENCE.md` implemented in the minimal Compose path. Source-only; no apply/install/service/DB/registry/login/push/commit. Stopping for review.

## A. Docker authority boundary

- `infra/production/solarsage-github-deploy` deploy branch now execs exactly `/usr/bin/sudo -n -H /usr/local/libexec/solarsage/prod-orchestrator deploy <sha> --manual-confirm` (never mutable checkout).
- `infra/production/solarsage-deploy.sudoers`: the ONLY capability is the whole-argument anchored regex form `astro ALL=(root) NOPASSWD: /usr/local/libexec/solarsage/prod-orchestrator ^deploy [0-9a-f]{40} --manual-confirm$` (sudo 1.9.15; the argument string as a whole must match — no wildcard/literal args; `visudo -cf` parsed OK). Old systemd-restart aliases and the parked release-authority alias removed. The routing test asserts the exact `^...$` line and the absence of restart/release-authority/wildcard aliases.
- Orchestrator shebang is deterministic `#!/bin/bash`.
- Runbook owner commands now use root sudo (`sudo /usr/local/libexec/solarsage/prod-orchestrator ...`); the GitHub wrapper exposes only `deploy`. `astro` is never granted docker-group membership.
- `test-prod-github-wrapper.sh` updated for the new dispatch form (sudo `-n -H` mock, exec-target validators, substitution proofs, self-test anchors): 56 product cases + 10 self-tests green.

## B. Fresh/reboot maintenance lock

- New `infra/production/tmpfiles.d/solarsage.conf`: standard tmpfiles rule `f /run/solarsage-maintenance.lock 0660 root astro - -`.
- host-prepare installs it byte-exact root:root `0644` to `/etc/tmpfiles.d/solarsage.conf`, runs `systemd-tmpfiles --create` on apply (fail-closed), registers it in `PROD_TX_PATHS`, and `verify_host_state` proves bytes/metadata of the declaration plus the lock file (`root:astro 0660`). `systemd-tmpfiles` added to required commands. No custom state machine.

## C. Host verify + canonical daily backup

- `verify_host_state`: `ENABLED_UNITS` now only `solarsage-db.service` + `solarsage-backup.timer`; `DISABLED_UNITS` requires api/sidecar/frontend and `solarsage-backup-maintenance.timer` to be disabled, evaluated static-aware (captured `is-enabled` output; only `enabled`/`enabled-runtime` is an error, so a static oneshot `solarsage-backup-maintenance.service` is not misread as enabled); `PARKED_INACTIVE_UNITS` additionally requires the maintenance timer/service to be not active. Host preparation never starts/stops/restarts app units and never enables/starts the parked path.
- `infra/systemd/solarsage-backup.service` rewritten: `User=root`, `ExecStart=/usr/local/libexec/solarsage/prod-orchestrator backup --manual-confirm` (no mutable checkout, no profile engine); daily timer stays enabled/active. Parked backup-maintenance timer/service is disabled (never enabled/started) by host-prepare; old backup scripts parked; no backup data deleted.
- `test-prod-profile-consumer-cutover.sh`: backup unit assertions updated (root + installed orchestrator ExecStart, no parked references); systemd-analyze verification uses a sandbox-staged unit copy (staged orchestrator ExecStart + sibling DB unit) — honest static proof without installing.

## D. Executable migration command

- New `prod-orchestrator migrate <sha> --manual-confirm`: exact SHA, maintenance lock, env/DB/restic/compose preflight, digest resolve/verify, pre-migration backup, runs ONLY the one-shot `migrate` profile with pinned digest env. No app up, no release record mutation; migrations never automatic.
- Harness OC25: exact order (backup → restic → pulls → inspects → migrate run), pinned digests, no `up -d --wait`, no record write, failure path rc 78, CLI gates, canary absence.
- Runbook section 5 now documents the orchestrator migrate command (the unexecutable direct-compose form removed).

## E. Private registry auth

- Runbook step 7.5: one-time standard root Docker login for private GHCR with a read-only `read:packages` credential entered interactively via `--password-stdin` (never in Git/logs); the root orchestrator uses `/root/.docker/config.json`; preflight/pull fail closed on auth errors.

## F. Restore cleanup correctness

- `created=0` is now set only after a successful `docker rm`; on failure the EXIT trap retries and emits one generic warning (`Warning: rehearsal cleanup failed`) without secrets.
- Harness OC26: injected `rm` failure → rc 78 with `rehearsal container cleanup failed` plus the generic trap warning; canary absent.

## Stale text (pre-work)

- 178 report section 2 and runbook lines ~115/~161 confirmed disable-only (`systemctl disable` without `--now`, no stop by host-prepare; manual stop only as the owner's one-time cutover step).

## Docs synchronization (final pre-acceptance pass)

- `docs/DEPLOYMENT.md`: all orchestrator commands now root-runner (`sudo /usr/local/libexec/solarsage/prod-orchestrator ...`), `migrate` added, daily automated backup documented with manual fallback.
- `docs/PRODUCTION_RUNBOOK.md` Appendix A no longer calls the canonical `solarsage-backup.timer`/`.service` old/parked — only the maintenance timer/service and the old backup scripts are parked.
- Registry CI configuration clarified in both docs and the workflow contract: `REGISTRY_NAMESPACE` must be a **repository-level Actions variable** (e.g. `ghcr.io/OWNER`, no tag) because the `build` job has no `environment`; setup via Settings → Secrets and variables → Actions → Variables or `gh variable set/get`; the four deploy secrets remain in the `production` environment. The stale one-job workflow validator (`CANON_DEPLOY` rc=13, `E_JOB_COUNT`) is unchanged by directive and remains reported.

## Verification (direct rc)

| Check | rc |
|---|---|
| `test-prod-orchestrator.sh` run 1 | 0 — 28/28 |
| `test-prod-orchestrator.sh` run 2 | 0 — 28/28, output byte-identical |
| `bash -n` orchestrator/harness/host-prepare/routing-test/wrapper | 0 |
| `visudo -cf infra/production/solarsage-deploy.sudoers` (whole-argument regex) | parsed OK |
| `docker compose --env-file <temp> -f infra/production/docker-compose.app.yml config --quiet` | 0 |
| `test-prod-github-wrapper.sh` | 0 — 56 product + 10 self-tests |
| `test-prod-host-offsite-routing.sh` | 0 (incl. exact sudoers regex assertion; block matchers indentation-agnostic `/^ *)/` after an over-capture fragility fix) |
| `test-prod-profile-consumer-cutover.sh` | 0 |
| `test-prod-namespace-layout.sh` | 0 |

No buildx check (no Dockerfile changes in this slice). The stale two-job `CANON_DEPLOY` source-readiness validator remains parked/non-canonical and is NOT a release gate for the minimal Compose path.

## Addendum — clean-host blocker fix (profile-engine removal from active host prep)

A clean host following the new runbook has only `/etc/solarsage/app.env`, but `prod-host-prepare.sh --check/--apply` still required the parked profile engine (`prod-env-prepare.sh --check`, `prod-env-run.sh db`), and `infra/systemd/solarsage-db.service` launched the DB through the old profile runner — so host preparation and DB start failed on a clean host. Fixed narrowly:

- `infra/systemd/solarsage-db.service` is now self-contained: ExecStart/Reload/Stop invoke `/usr/bin/docker compose --env-file /etc/solarsage/app.env -f /opt/solarsage-astro/infra/production/docker-compose.yml ...` directly; GRACE contract updated (input = `/etc/solarsage/app.env` root:astro 0640; no profile runner). `systemd-analyze verify` of the DB unit passes on this host.
- `prod-host-prepare.sh` active preflight no longer invokes the parked `prod-env-prepare.sh --check`. It now performs a read-only canonical env check: `/etc/solarsage/app.env` real non-symlink `root:astro 0640` plus presence of exactly the required DB keys (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) without printing values.
- The DB compose config preflight now runs `/usr/bin/docker compose --env-file /etc/solarsage/app.env ... config` directly (no `runuser`, no `prod-env-run.sh`).
- The old offsite/profile integration block was removed from active preflight (offsite readiness belongs to the canonical orchestrator preflight: restic binary + password file contract). Parked legacy scripts/units were not deleted and the active path no longer requires `source.env` or generated `current/*.env` profiles.
- `test-prod-host-offsite-routing.sh` and `test-prod-profile-consumer-cutover.sh` assertions updated in place (new DB ExecStart trio, app.env preflight presence, direct DB compose config check, absence of parked runner invocations). Both suites green.

Verification for this addendum (direct rc): orchestrator harness 28/28 twice byte-identical; `bash -n` 0; host-routing 0; profile-cutover 0; github-wrapper 0; namespace-layout 0; `compose config --quiet` 0; `systemd-analyze verify` DB unit 0 (backup unit verified via the existing sandbox-staged path since the orchestrator binary is a host-prepare install prerequisite). No `--apply`/install/service/DB action was performed.

### Install-order follow-up (systemd-analyze in common preflight)

The common preflight `systemd-analyze verify` loop previously validated `solarsage-backup.service` before the orchestrator binary it references is installed — so `--apply` self-blocked on a clean host (`Command ... is not executable`). The loop now verifies all other units unchanged, and handles the backup unit minimally: if the installed `/usr/local/libexec/solarsage/prod-orchestrator` already exists it verifies the unit as-is; otherwise it verifies a temporary unit copy whose ExecStart points at the repository source `scripts/deploy/prod-orchestrator.sh` (with the sibling DB unit staged for dependency resolution), in a `mktemp -d` sandbox with no installation or runtime mutation. Verified standalone: staged backup unit and DB unit both pass `systemd-analyze verify` on this host. No verification semantics for the other units were weakened; runtime/backup behavior unchanged.

## Addendum — completion audit (A–D, isolated verification only)

### A. Frontend build/runtime rewrite identity — proven and fixed

- **Proof (pre-fix):** repo artifact `.next-prod/routes-manifest.json` (built 2026-07-13) contained destination `http://127.0.0.1:8000/api/:path*`; an isolated docker build of the then-current recipe (`solarsage-frontend-audit:prefix`, image `sha256:b0e3c7a5...`) inspected via `docker run --rm --network none --entrypoint cat` confirmed the same destination baked into the image manifest — inside the frontend container this loops back to itself, not to the Compose `api` service.
- **Fix:** `apps/web/Dockerfile` builder stage now defines non-secret `ARG PROD_API_REWRITE_BASE_URL=http://api:8000` and exports it before `RUN pnpm build` (contract updated); the deploy workflow passes the same build arg explicitly; runtime Compose env and the local fallback (`http://127.0.0.1:8000` when unset outside Compose) are retained; no secrets involved.
- **Proof (fixed):** rebuilt image (`solarsage-frontend-audit:fixed`, image `sha256:3562ade2...`) inspected the same way — destination is now `http://api:8000/api/:path*`.
- `__tests__/guardrails/preview-isolation.test.ts` (existing suite, no new harness) gained one static assertion that the Dockerfile builder sets the build arg/env before `RUN pnpm build`: 7/7 green.

### B. Fresh-host runbook order corrected

`docs/PRODUCTION_RUNBOOK.md` 3.1 reordered: (1) os-bootstrap → (2) operator directories/files with exact safe `install -d`/`install -m` commands (`/etc/solarsage`, `/etc/solarsage/keys`, `/etc/solarsage/backup`, `app.env`, restic password file, `root:astro 0640`, no secret values in commands) → (3) DNS → (4) cert-prepare → (5) `prod-host-prepare.sh --apply/--check` → (6) `prod-github-access.sh --apply` then `--preflight` (checkout `ssh-keygen` command documented before registration when the key is missing) → (7) first backup → (7.5) GHCR root login → (8) deploy. The wrapper validation in github-access now runs after host-prepare installs the wrapper. The private source-readiness gate remains explicit. github-access installs no second wrapper/orchestrator. Post-review cleanup: section 3.1 code fences verified balanced; idempotent `sudo install -d -o astro -g astro -m 0700 /home/astro/.ssh` added before `ssh-keygen`; GRACE module IDs unified to a single `M-DOC-PRODUCTION-RUNBOOK` (START/END contract/map hyphen/underscore mismatch fixed). Docs safety pass: `/dev/null` installs for `app.env` and `restic-password` are guarded by `if [ ! -e ... ]` (existing secrets never overwritten, `root:astro 0640` preserved), and `ssh-keygen` runs only when the checkout key is absent.

### C. Existing-user OS convergence

`prod-os-bootstrap.sh --apply` now removes `astro` from the `docker` group when present (root-only, idempotent via `gpasswd -d`; fresh users unaffected), so the final `verify_os_state` no longer fails after mutations on existing-user hosts. `gpasswd` added to required commands; contract invariant records that no Docker deploy privilege is ever granted to astro and that the current SSH session must reconnect for supplementary group refresh.

### D. Verification results (direct rc)

| Check | rc / result |
|---|---|
| `bash -n` os-bootstrap, host-prepare | 0 |
| `test-prod-orchestrator.sh` ×2 | 0 — 28/28, byte-identical |
| `test-prod-host-offsite-routing.sh` | 0 |
| `test-prod-profile-consumer-cutover.sh` | 0 |
| `test-prod-github-wrapper.sh` | 0 — 56+10 |
| `test-prod-namespace-layout.sh` | 0 |
| `npx vitest run __tests__/guardrails/preview-isolation.test.ts` | 7/7 passed |
| `docker buildx build --check` api / sidecar / frontend | 0 / 0 / 0 (no warnings) |
| Frontend image build + manifest inspection (prefix / fixed) | proof recorded above |

API/sidecar image builds were not run (only `buildx --check`); their Dockerfiles were untouched in this audit and full builds would exceed the practical cycle. No push/login/apply/restart/DB/migrate/commit was performed. Local audit images were removed after inspection.

## Explicit non-actions

No `--apply`/install, no service change, no DB action, no registry login/push, no commit/push. The systemd-tmpfiles parse was validated by a non-root create attempt (permission-denied as expected; nothing created). R14 files, stale workflow validator, old matrix and application business logic untouched.
