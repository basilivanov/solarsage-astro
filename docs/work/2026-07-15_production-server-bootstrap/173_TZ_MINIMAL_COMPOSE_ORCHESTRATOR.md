# TZ — minimal manual production path: OCI images + Docker Compose

## Read first

- `AGENTS.md`;
- `172_ARCH_MINIMAL_PRODUCTION_PATH_DECISION.md`;
- current `infra/production/docker-compose.yml`;
- current API/sidecar health modules and `next.config.mjs`;
- current `.github/workflows/deploy-production.yml`.

## Objective

Replace the unfinished R14 promotion/GC runtime path with one small, understandable, manually invoked Compose orchestrator. Do not extend or repair the exhaustive R14 harnesses in this slice.

The result must deploy prebuilt immutable OCI images identified by a full lowercase commit SHA. The production host must not run pnpm/pip/build or create Git worktrees.

## Canonical runtime

Keep host Nginx and the existing separate PostgreSQL compose project:

```text
Nginx 80/443 -> 127.0.0.1:3002 frontend
             -> 127.0.0.1:8000 API
API -> sidecar 127.0.0.1:18091
DB  -> 127.0.0.1:5433 (separate solarsage-prod compose project)
```

Create one canonical application compose file under `infra/production/` with services `api`, `sidecar`, `frontend` and a one-shot `migrate` profile. Do not use the old root `docker-compose.yml` or namespaced `docker-compose.prod.yml` as production source of truth. App host bindings must be loopback and canonical.

Use images `${REGISTRY}/solarsage-api:${RELEASE_SHA}`, `${REGISTRY}/solarsage-sidecar:${RELEASE_SHA}`, and `${REGISTRY}/solarsage-frontend:${RELEASE_SHA}`. No `latest`, branch tag or mutable image reference is allowed in the production file.

## Allowed implementation files

- one canonical `infra/production/docker-compose.app.yml`;
- a root-context Next.js production Dockerfile (replace the obsolete Vite/nginx recipe, retaining GRACE header);
- minimal API/sidecar image metadata changes needed to expose full `RELEASE_SHA` and calculation/ephemeris identity;
- `scripts/deploy/prod-orchestrator.sh` as the sole app deploy entrypoint;
- one small `scripts/deploy/tests/test-prod-orchestrator.sh` contract harness;
- `.github/workflows/deploy-production.yml` manual build/push/approval/SSH wiring;
- `docs/DEPLOYMENT.md` and `docs/PRODUCTION_RUNBOOK.md` only for the new commands;
- `scripts/deploy/README.md` inventory update if required.

Do not modify or add R14 promotion/authority suites, matrix inventory, GC helpers, Kubernetes manifests, Kamal configuration, Coolify/CapRover control plane or a second deploy orchestrator. Leave the frozen partial R14 files untouched and explicitly mark them non-canonical/parked.

## Orchestrator contract

`prod-orchestrator.sh` is root-owned when installed later; source version is tested only in private sandboxes. Exact CLI:

```text
prod-orchestrator.sh preflight <sha>
prod-orchestrator.sh deploy <sha> --manual-confirm
prod-orchestrator.sh rollback <sha> --manual-confirm
prod-orchestrator.sh status
prod-orchestrator.sh backup --manual-confirm
prod-orchestrator.sh restore <dump> --manual-confirm   # plan/isolated target only in this slice
```

The deploy command must:

1. require exact full SHA and explicit manual confirmation;
2. validate the root-owned env/credential file, registry/repository, Compose config and image references;
3. verify DB health on 5433 and run a pre-deploy logical backup/checksum before changing app containers;
4. `docker compose pull` exact SHA images (never build) and run `docker compose up -d --wait api sidecar frontend`;
5. query API, sidecar and frontend health and require exact full `release_sha` equal to the requested SHA; sidecar health additionally proves ephemeris/calculation identity;
6. write a small root-owned active/previous SHA record only after all health checks pass;
7. on failed health after a change, attempt one exact rollback to the recorded previous SHA, re-run all health checks, and return non-zero if rollback cannot be proven;
8. never call `docker compose down -v`, delete the DB volume, run arbitrary user-supplied shell, or mutate Nginx/systemd in the app deploy command.

`rollback` accepts only an explicit SHA already present in the recorded release allow-list or registry digest check. It uses the same `pull`/`up --wait`/health path. `status` is read-only. `backup` and `restore` are explicit manual commands and must not be implicit side effects of `status`.

Keep the script short and linear. No generic transaction engine, pointer state machine, Git worktree registry or exhaustive mutation framework belongs here.

## Image requirements

- API image must not run Alembic on ordinary container start. `migrate` is a separate one-shot profile/command and is never started automatically by `deploy` unless an explicit reviewed flag is added later.
- Frontend image must build the actual root Next.js application (Next standalone or a deterministic `next start` production image), not `apps/web`'s obsolete Vite `dist` recipe.
- API/sidecar/frontend receive `RELEASE_SHA` as a non-secret environment value or baked label and return it in their liveness payload. Preserve existing response fields where tests require them; add a stable `release_sha` field rather than deriving identity from a mutable Git checkout.
- Sidecar receives the host ephemeris directory read-only and reports exact calculation/ephemeris identity.
- No `.env`, Telegram token, OpenRouter key, DB password or SSH material is copied into an image layer.

## Secrets and DB

- Source-controlled Compose contains no secret values or defaults.
- The host supplies a root-owned `0640` env/credential source readable only by the deploy/runtime group; tests use a private temporary file with a canary and prove it never appears in image/build output or logs.
- Keep PostgreSQL in the existing `infra/production/docker-compose.yml` project and port 5433. The app stack connects to the DB over the host/declared network without recreating or deleting the DB volume.
- Minimal backup is `pg_dump -Fc` + `pg_restore --list` + SHA256 pair, followed by the existing Restic offsite command when configured. If Restic is absent, preflight fails closed; do not write a new retention engine.
- Restore in this slice is a plan plus isolated-target rehearsal. Real production restore requires a separate explicit user command and a later accepted runbook.

## Manual gate

The GitHub workflow remains `workflow_dispatch`, validates `main` and full SHA, builds/pushes immutable images, then enters the `production` environment before SSH. The SSH command is exactly `deploy <sha>` and the remote wrapper invokes only the orchestrator. No push to `main` may deploy by itself.

If GitHub plan restrictions prevent required reviewers for a private repository, manual `workflow_dispatch` plus the operator's explicit approval is the fallback; do not silently turn on automatic deployment.

## Focused verification only

The new harness should prove only:

- exact CLI/confirmation/sha validation;
- no-build/no-`latest`/canonical-port/static-secret constraints;
- compose config validation and exact image tags;
- mock `pull`, `up --wait`, health identity and one rollback attempt;
- backup command ordering and no `down -v`/DB-volume mutation;
- secret canary absence;
- deterministic exit code and no production-path mutation.

Use direct exit-code capture (`if command; then rc=0; else rc=$?; fi`), never `pipeline | tail` as an oracle. Run this focused harness twice; do not add it to the old R14 exhaustive matrix until the new path is independently accepted.

## Stop condition

After source-only implementation, run `docker compose config` against a temporary env (no daemon mutation), shell syntax, the focused harness twice and the existing application unit tests relevant to changed health/Docker code. Write a short report with exact rc and known host prerequisites. Stop for independent review.

No image push, registry mutation, production compose invocation, service restart, Nginx/systemd apply, DB migration/restore, commit or push is allowed in this slice.
