# Report TZ 176 — minimal runtime corrections for Compose orchestrator

Status: all six blocking findings from `175_REVIEW_TZ173_REJECTED_MINIMAL_RUNTIME_BLOCKERS.md` corrected per `176_TZ_TZ173_MINIMAL_RUNTIME_CORRECTIONS.md`. Source-only; no production action taken. Stopping for independent review.

## Finding 1 — installed execution boundary

- `scripts/deploy/prod-orchestrator.sh` env contract is now real non-symlink `root:astro 0640` via `validate_secret_file` (identity constants `ORCH_ENV_OWNER/ORCH_ENV_GROUP` default `root`/`astro`; sandbox harness overrides them — documented test seam, production defaults unchanged).
- `infra/production/solarsage-github-deploy` execs only the installed path `/usr/local/libexec/solarsage/prod-orchestrator deploy <sha> --manual-confirm`; never mutable checkout code, no extra sudo layer; contract comments updated.
- `scripts/deploy/prod-host-prepare.sh`: `--apply` installs the orchestrator byte-exact root:root `0755` to `/usr/local/libexec/solarsage/prod-orchestrator`, the app compose byte-exact root:root `0644` to `/etc/solarsage/compose/docker-compose.app.yml` (dir root:root `0755`), prepares `/var/lib/solarsage/orchestrator` `astro:astro 0700`; both files registered in `PROD_TX_PATHS`. `verify_host_state` proves bytes (`cmp -s`) + owner/group/mode for both files and all three directories. `/var/backups/solarsage` stays astro-owned.
- `test-prod-host-offsite-routing.sh` extended with structural assertions for every new install/verify line. `--apply` was NOT run.
- Mutating commands (`deploy`/`rollback`/`backup`/`restore`) now hold a simple non-blocking `flock` on the existing `/run/solarsage-maintenance.lock` (rc `75` busy); no journal/state machine.

## Finding 2 — container networking

- `next.config.mjs`: production uses server-only `PROD_API_REWRITE_BASE_URL` when set, else canonical `http://127.0.0.1:8000`; `DEV_API_REWRITE_BASE_URL` remains ignored in production.
- `infra/production/docker-compose.app.yml` sets frontend `PROD_API_REWRITE_BASE_URL: http://api:8000` exactly.
- `__tests__/guardrails/preview-isolation.test.ts` extended in place with 4 direct behavioral branch assertions (eval of `rewrites()` under controlled env): compose override, localhost fallback, dev-override ignored in production, dev-override honored outside production.

## Finding 3 — up --wait failure + record semantics

- `activate_with_digests` captures `up -d --wait` rc without failing the script; any post-change failure enters the one exact rollback attempt.
- Record is a validated 8-field tuple (active/previous SHA + 3 digest refs each; exact formats validated on read).
- Successful deploy shifts the old complete active tuple to previous.
- Proven recovery after failed deploy/rollback leaves the complete record byte-identical (proven in harness via `cmp`).
- Same-SHA deploy/rollback is a proven no-op preserving history (no pull/up, record unchanged).

## Finding 4 — digest-pinned activation

- Compose images are required per-service vars `${API_IMAGE}/${SIDECAR_IMAGE}/${FRONTEND_IMAGE}`; orchestrator accepts only `registry/repo@sha256:<64 lowercase hex>`.
- Deploy pulls each `:<sha>` tag once, verifies OCI label `org.opencontainers.image.revision` equals the exact SHA, resolves the matching RepoDigest (repo part must equal the expected repository), validates compose config references the resolved digests exactly, then activates.
- Rollback uses recorded digest refs; never pulls/re-resolves the old tag.
- Harness cases: label mismatch (OC18), malformed RepoDigest (OC19), up --wait nonzero + one proven rollback (OC20), rollback without old-tag pull (OC11).

## Finding 5 — backup/restore secret and collision contract

- `RESTIC_PASSWORD` replaced by `OFFSITE_RESTIC_PASSWORD_FILE`; the password file is validated as regular non-symlink readable `root:astro 0640`; `RESTIC_PASSWORD_FILE` is exported only for the Restic process (harness proves it is absent from the `pg_dump` environment).
- Restic failure preserves the local dump+checksum and the error message says so (OC13B).
- Restore uses unique name `solarsage-restore-rehearsal-$$`; never removes a pre-existing fixed-name container; cleans only the container it created (OC15 collision/cleanup case with a pre-existing container registry proof).

## Finding 6 — contracts/docs cleanup

- `apps/api/tests/test_public_surface_security.py` updated to the intentional exact 4-key health contract `{status, version, git_sha, release_sha}`.
- `docs/DEPLOYMENT.md` rewritten around the canonical path; legacy deploy/port-5432/8001/3000/plaintext-`.env` instructions removed.
- `docs/PRODUCTION_RUNBOOK.md`: remaining active `prod-deploy.sh` and in-place build/worktree instructions removed; host DB URL `127.0.0.1:5433` vs container `DATABASE_URL ...@solarsage-db:5432` explicitly distinguished; one-time cutover prerequisite added (stop/disable old systemd app services before Compose claims 8000/3002/18091 — documented only, not performed).

## Verification (direct rc, no pipelines as oracles)

| Check | rc |
|---|---|
| `bash -n` orchestrator + harness + wrapper + host-prepare (+routing test) | 0 |
| `docker compose --env-file /tmp/orch176-test.env -f infra/production/docker-compose.app.yml config --quiet` | 0 (digest refs, loopback, no latest) |
| `test-prod-orchestrator.sh` run 1 | 0 — 24/24 |
| `test-prod-orchestrator.sh` run 2 | 0 — 24/24, output byte-identical |
| `test-prod-github-wrapper.sh` | 0 — 56 product + 10 self-tests |
| `test-prod-namespace-layout.sh` | 0 |
| `test-prod-host-offsite-routing.sh` | 0 |
| API pytest `test_health.py test_public_surface_security.py` | 5 passed |
| Sidecar pytest `test_health.py` | 2 passed |
| `npx vitest run __tests__/guardrails/preview-isolation.test.ts` | 6 passed |
| `npx eslint app/api/release-health/route.ts` | 0 |
| `docker buildx build --check` api / sidecar / frontend Dockerfiles | 0 / 0 / 0 (no warnings) |
| `py_compile` changed API/sidecar modules | 0 |

## Stale contract (reported, validator untouched per directive)

- `test-prod-source-readiness-workflow.sh` → `CANON_DEPLOY` fails rc=13 (`E_JOB_COUNT jobs.count`): the R14 one-job structural contract does not cover the TZ173 two-job build/push → approval → SSH workflow. Validator not modified; parked for a separate decision.

## Known host prerequisites (not performed)

- `prod-host-prepare.sh --apply` (installs orchestrator/compose/state dir), `/etc/solarsage/app.env` (`root:astro 0640`), `OFFSITE_RESTIC_PASSWORD_FILE` target file, restic binary, docker group membership for `astro`, `/opt/sweph/ephe`, one-time stop/disable of old systemd app services before the first Compose deploy.
- Current host lacks `restic` and `/etc/solarsage/app.env` (expected later host-preflight failure, checks not weakened).

## Explicit non-actions

No `--apply`/install, no production compose invocation, no service change, no DB action, no image build/push, no commit/push. Parked R14 files, source-readiness validator, old matrix inventory and application business logic untouched.
