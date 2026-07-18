# Review TZ 173 — minimal Compose path rejected on runtime blockers

## Verdict

**Direction accepted, implementation rejected.** OCI images + Docker Compose + one orchestrator is the correct simplification. The current source is not yet a runnable production path. This review intentionally does not reopen the R14 exhaustive matrix.

## Independent evidence

- `bash -n`, changed Python `py_compile`, and `docker compose config --quiet` — rc `0`.
- `test-prod-orchestrator.sh` — rc `0`, 17/17.
- `test-prod-github-wrapper.sh` — rc `0`, 56 product cases + 10 self-tests.
- API focused review (`test_health.py` + `test_public_surface_security.py`) — rc `1`: public surface still requires exactly `{status, version, git_sha}` and rejects the new `release_sha` field.
- Sidecar health tests — rc `0`, 2 passed.
- A root-owned `root:astro 0640` env file, which the docs require, is rejected by the orchestrator when it runs as `astro`: rc `78`, `Error: env/credential file owner mismatch`.
- `NODE_ENV=production` evaluation of `next.config.mjs` still returns `http://127.0.0.1:8000/api/:path*`; inside the frontend container this points to the frontend container itself, not Compose service `api`.

## Blocking findings

### 1. Workflow/host execution path cannot work

The forced wrapper runs `/opt/solarsage-astro/scripts/deploy/prod-orchestrator.sh` directly as SSH user `astro`. The script requires the env file owner to equal `id -u`, while docs require `root:astro 0640`. Host preparation installs neither a root-owned orchestrator nor the application compose file and has no canonical state-directory preparation. The wrapper also executes mutable checkout code.

Required minimal boundary: host preparation installs the orchestrator root:root `0755` under `/usr/local/libexec/solarsage/`, the compose file root:root `0644` under `/etc/solarsage/compose/`, and prepares an `astro:astro 0700` state directory. The installed orchestrator runs as `astro`, accepts only root:astro `0640` env, and the root-owned forced wrapper execs only the installed path. No new Python authority or sudo layer is needed.

### 2. Frontend container cannot reach API

`next.config.mjs` hardcodes the production rewrite to `127.0.0.1:8000`. In the Compose frontend container, `/api/*` therefore loops back to itself. Add a server-only production internal URL (exact `http://api:8000` in canonical Compose) while preserving the current localhost default for the legacy/non-container runtime and continuing to ignore the dev override in production.

### 3. Normal `up --wait` failure bypasses rollback

`activate_sha` calls `compose up -d --wait ... || fail`. Docker Compose returns non-zero when a changed service does not become healthy; that exits the entire script before the fallback branch. This is the most common post-change failure and must enter the one rollback attempt.

Additionally, after a proven failed deploy/rollback the code overwrites `previous` with the failed target. A proven recovery must leave the pre-operation record byte-equivalent. Same-SHA deploy/rollback must not erase the prior stable history.

### 4. SHA tags are not immutable authority

The workflow inspects pushed digests but discards them; the server later pulls mutable `:<sha>` tags. A tag can be replaced, so rollback by tag is not immutable.

Minimal correction: pull the SHA tag, verify OCI label `org.opencontainers.image.revision` equals the requested full SHA, resolve the resulting repository digest, and run Compose with required per-service `repo@sha256:<64hex>` references. Store active/previous SHA plus all three digest references; rollback uses the stored digests and never re-resolves an old tag.

### 5. Backup/restore secret and collision contract regressed

The new env requires plaintext `RESTIC_PASSWORD`, while the accepted secret boundary and runbook use `OFFSITE_RESTIC_PASSWORD_FILE`. Reuse the password-file contract and export `RESTIC_PASSWORD_FILE` only for Restic.

Restore unconditionally executes `docker rm -f solarsage-restore-rehearsal`, which can delete a pre-existing container. Use a unique validated name and fail/cleanup only the exact container created by this invocation. Add a direct focused case; no new harness file.

### 6. Active contracts/docs are contradictory

- `apps/api/tests/test_public_surface_security.py` is red after the intentional health shape change.
- `docs/PRODUCTION_RUNBOOK.md` still instructs the parked `prod-deploy.sh`, in-place build/worktree cleanup, and host-form `DATABASE_URL=127.0.0.1:5433` for the container app.
- `docs/DEPLOYMENT.md` still leads with legacy deploy, ports 5432/8001/3000 and plaintext `.env` instructions.

Update these existing contracts to one canonical Compose path. Do not touch the stale R14 one-job workflow validator; document it as parked until the minimal path is accepted.

## Secondary readiness note

The current host has no `restic` and no `/etc/solarsage/app.env`; this is an expected later host-preflight failure, not a reason to weaken checks. A one-time cutover runbook must stop the old systemd app services before Compose takes 8000/3002/18091. No production action is authorized now.

## Explicit non-actions

No image build/push, production Compose invocation, service restart, Nginx/systemd apply, DB migration/restore, commit or push occurred during review.
