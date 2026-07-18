# Report TZ 173 — minimal Compose/OCI orchestrator (source-only)

Status: implemented per `173_TZ_MINIMAL_COMPOSE_ORCHESTRATOR.md` + `172_ARCH_MINIMAL_PRODUCTION_PATH_DECISION.md`. Source-only; no production action taken. Stopping for independent review.

## Changed files

### New
- `infra/production/docker-compose.app.yml` — canonical app stack: `api` (127.0.0.1:8000), `sidecar` (127.0.0.1:18091→8001, `/opt/sweph/ephe:ro`), `frontend` (127.0.0.1:3002), one-shot `migrate` profile; images `${REGISTRY}/solarsage-*:${RELEASE_SHA}`; joins external `solarsage-prod_default` DB network; no secret values, no `latest`, loopback-only.
- `scripts/deploy/prod-orchestrator.sh` — sole app deploy entrypoint: `preflight|deploy|rollback|status|backup|restore` with exact SHA + `--manual-confirm` gates; pre-deploy `pg_dump -Fc` + `pg_restore --list` + SHA256 + Restic; `pull` + `up -d --wait` (never build); three-way exact `release_sha` health proof (sidecar additionally ephemeris/calculation identity); root-owned active/previous record; one exact rollback attempt; `restore` = plan + isolated throwaway-postgres rehearsal only. No `down -v`, no DB volume/Nginx/systemd mutation.
- `scripts/deploy/tests/test-prod-orchestrator.sh` — 17 focused contract cases (CLI/confirm/SHA validation, env-file mode/owner, registry/compose/image checks, exact pull→up order, health identity, proven + unproven rollback, allow-list rollback, read-only status, backup ordering, restore rehearsal + checksum gate, static no-build/no-latest/loopback, canary absence, deterministic rc).
- `app/api/release-health/route.ts` — frontend `GET /api/release-health` → `{status, release_sha}` from runtime env; does not shadow the `/api/health` backend proxy.

### Modified
- `apps/web/Dockerfile` — replaced obsolete Vite/nginx recipe with root-context Next.js production image (pnpm frozen lockfile, `next build` → `next start -p 3002`, `RELEASE_SHA` build-arg label).
- `apps/api/Dockerfile` — removed Alembic from ordinary start (migrate is the one-shot compose profile); `ARG/ENV/LABEL RELEASE_SHA`.
- `apps/api/app/core/config.py` — `release_sha` setting (`RELEASE_SHA`, default `unknown`).
- `apps/api/app/api/health.py` — payload `{status, version, git_sha, release_sha}`; contract updated.
- `apps/api/tests/test_health.py` — exact 4-key shape.
- `apps/solarsage/Dockerfile` — `ARG/ENV SOLARSAGE_RELEASE_SHA/LABEL`.
- `apps/solarsage/solarsage/core/config.py`, `schemas/health.py`, `api/health.py` — `release_sha` end-to-end; `apps/solarsage/tests/test_health.py` — assertion.
- `.github/workflows/deploy-production.yml` — `workflow_dispatch`-only; `build` job (main+SHA+private guards, registry login, buildx build/push of three SHA-tagged images, digest proof) → `deploy` job gated by `production` environment, SSH exactly `deploy $GITHUB_SHA`.
- `infra/production/solarsage-github-deploy` — `deploy <sha>` now execs only `prod-orchestrator.sh deploy <sha> --manual-confirm` (manual-gate requirement); `source-check` routing unchanged.
- `scripts/deploy/tests/test-prod-github-wrapper.sh` — mechanical follow-up to the routing change (canonical target, expected argv `deploy <sha> --manual-confirm`, self-test anchors/line numbers).
- `docs/DEPLOYMENT.md`, `docs/PRODUCTION_RUNBOOK.md` — new commands only; R14 scripts marked parked/non-canonical.
- `scripts/deploy/README.md` — inventory + compat entries for the two new files; explicit "Non-canonical (parked R14)" section.

## Verification (exact rc)

| Check | rc |
|---|---|
| `bash -n` orchestrator + harness + wrapper | 0 |
| `py_compile` changed API/sidecar modules | 0 |
| `docker compose --env-file /tmp/orch-test.env -f infra/production/docker-compose.app.yml config --quiet` | 0 (images exact full SHA; 3 loopback bindings; no `latest`) |
| `test-prod-orchestrator.sh` run 1 | 0 — 17/17 |
| `test-prod-orchestrator.sh` run 2 | 0 — 17/17, output byte-identical to run 1 |
| `test-prod-github-wrapper.sh` | 0 — 56 product cases + 10 self-tests |
| `test-prod-namespace-layout.sh` | 0 (README inventory covers new files) |
| `apps/api` pytest `tests/test_health.py` | 3 passed |
| `apps/solarsage` pytest `tests/test_health.py` | 2 passed |
| `npx eslint app/api/release-health/route.ts` | 0 |

## Known stale / parked (explicitly not fixed in this slice)

- `test-prod-source-readiness-workflow.sh` → `CANON_DEPLOY` fails rc=13 (`E_JOB_COUNT jobs.count`). The R14 structural contract expects the old single-job deploy workflow; the TZ173 manual gate requires the two-job build/push → approval → SSH shape. Left unchanged per user directive; needs a separate contract decision.
- `test-prod-release-promotion.sh` remains red at setup (frozen mid-TZ171, parked, non-canonical).
- `run-deploy-matrix.sh` not run and the new orchestrator harness intentionally not added to the R14 matrix until independent acceptance.
- Frontend image build not executed (no docker build in this slice); recipe validated statically only.

## Host prerequisites for a later rollout (not performed)

- `/etc/solarsage/app.env` root-owned `0640` with `REGISTRY`, `POSTGRES_USER/PASSWORD/DB`, `DATABASE_URL` (container form `@solarsage-db:5432`), `APP_DOMAIN`, `TELEGRAM_BOT_TOKEN`, `GRACE_USER_SALT`, `CORS_ALLOWED_ORIGINS`, `OPENROUTER_API_KEY`, `RESTIC_REPOSITORY`, `RESTIC_PASSWORD`.
- Docker Compose v2, PostgreSQL client tools (`pg_dump/pg_restore/pg_isready/psql`), Restic on the host; `/opt/sweph/ephe` present for the sidecar read-only mount.
- CI: `vars.REGISTRY_NAMESPACE`; `production` environment secrets `PROD_HOST/PROD_USER/PROD_SSH_PRIVATE_KEY/PROD_KNOWN_HOSTS`; `packages: write` via `GITHUB_TOKEN`.
- DB project `solarsage-prod` running (port 5433) before any orchestrator command.

## Explicit non-actions

No image push, registry mutation, production compose invocation, service restart, Nginx/systemd apply, DB migration/restore, real backup/restore, commit or push. Frozen R14 partial files were not modified.
