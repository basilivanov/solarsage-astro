# TZ — minimal runtime corrections for Compose orchestrator

Read `173`, `174`, and review `175`. Fix only the six blocking findings from `175`. Do not add new deployment frameworks, R14 authority/promotion work, matrix suites or generic transaction layers.

## Allowed files

- `scripts/deploy/prod-orchestrator.sh` and its existing focused harness;
- `infra/production/docker-compose.app.yml`;
- `infra/production/solarsage-github-deploy` and its existing harness only for installed-path routing;
- `scripts/deploy/prod-host-prepare.sh` and directly owned host-prepare/fingerprint tests only for byte-exact installation/check of the orchestrator + compose + state directory;
- `next.config.mjs` and the existing preview-isolation test;
- API health test contract (`test_public_surface_security.py`);
- `docs/DEPLOYMENT.md`, `docs/PRODUCTION_RUNBOOK.md`, `scripts/deploy/README.md`;
- the existing workflow only if digest documentation/output needs a narrow clarification;
- one correction report.

Do not modify the parked R14 promotion files, source-readiness workflow validator, old matrix inventory, application business logic or production host.

## Exact corrections

### Installed execution boundary

- Install source orchestrator byte-exact as `/usr/local/libexec/solarsage/prod-orchestrator`, root:root `0755`.
- Install app compose byte-exact as `/etc/solarsage/compose/docker-compose.app.yml`, root:root `0644`; directory root:root `0755`.
- Prepare `/var/lib/solarsage/orchestrator` astro:astro `0700` and keep `/var/backups/solarsage` astro-owned.
- Installed orchestrator executes as `astro`; env contract is real non-symlink root:astro `0640`.
- Forced wrapper execs only the installed orchestrator path, never mutable checkout code and no extra sudo layer.
- Host-prepare `--check` proves bytes/owner/group/mode. Source-only tests substitute private paths; do not run `--apply`.

Use the existing global maintenance lock with a simple non-blocking `flock` for mutating commands (`deploy`, `rollback`, `backup`, `restore`). Do not build another journal/state machine.

### Container networking

- Add server-only `PROD_API_REWRITE_BASE_URL` handling in `next.config.mjs` for production.
- Canonical Compose sets it exactly to `http://api:8000`.
- Default production behavior outside Compose remains `http://127.0.0.1:8000`.
- `DEV_API_REWRITE_BASE_URL` remains ignored in production.
- Extend the existing preview-isolation test with direct assertions for these three branches; no new suite.

### Digest-pinned activation

- Compose image values are required per-service variables and accept only `registry/repo@sha256:<64 lowercase hex>` at activation.
- For a requested SHA, orchestrator pulls each `:<sha>` tag once, verifies image label revision equals the exact SHA, resolves the matching RepoDigest, and exports the three digest refs to Compose.
- State record contains active/previous SHA and the three active/previous digest refs; exact metadata and field formats are validated on read.
- Successful deploy shifts the old complete active tuple to previous.
- Proven recovery after failed deploy/rollback leaves the complete record unchanged.
- Rollback uses recorded digest refs, never pulls/re-resolves the old tag.
- Same-SHA deploy or rollback is a proven no-op that preserves history.

The existing focused harness must add direct cases for label mismatch, malformed/missing RepoDigest, `up --wait` nonzero followed by one rollback, byte-identical record after proven recovery, and rollback using stored digest without old-tag pull. Do not add mutation meta-tests.

### Backup/restore

- Replace `RESTIC_PASSWORD` with `OFFSITE_RESTIC_PASSWORD_FILE`; require exact regular non-symlink readable file with expected owner/group/mode, then set `RESTIC_PASSWORD_FILE` only for the Restic process.
- Preserve local dump/checksum on Restic failure.
- Restore uses a unique safe container name; it never removes a pre-existing fixed-name container and cleans only the container it created. Add one focused collision/cleanup case.

### Contract/docs cleanup

- Update `test_public_surface_security.py` to the intentional exact four-key health contract.
- Remove active legacy deploy/port/.env instructions from `docs/DEPLOYMENT.md` rather than appending another section.
- Remove remaining active `prod-deploy.sh` and in-place build instructions from the runbook. Clearly distinguish host DB URL `127.0.0.1:5433` from container `DATABASE_URL ...@solarsage-db:5432`.
- Add one-time cutover prerequisite: old systemd app services must be stopped before Compose claims 8000/3002/18091. Do not perform it.

## Verification

Capture direct exit codes without output pipelines:

```bash
bash -n scripts/deploy/prod-orchestrator.sh scripts/deploy/tests/test-prod-orchestrator.sh infra/production/solarsage-github-deploy
docker compose --env-file <private-temp-env> -f infra/production/docker-compose.app.yml config --quiet
bash scripts/deploy/tests/test-prod-orchestrator.sh
bash scripts/deploy/tests/test-prod-orchestrator.sh
bash scripts/deploy/tests/test-prod-github-wrapper.sh
bash scripts/deploy/tests/test-prod-namespace-layout.sh
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_health.py tests/test_public_surface_security.py -q
cd apps/solarsage && source venv/bin/activate && python -m pytest tests/test_health.py -q
npx vitest run __tests__/guardrails/preview-isolation.test.ts
npx eslint app/api/release-health/route.ts
```

Also run Dockerfile `buildx --check` for all three images. Do not perform an actual image push or production action. Report the stale R14 CANON_DEPLOY result, but do not change its validator.

Stop for independent review. No production install/apply, service change, DB action, commit or push.
