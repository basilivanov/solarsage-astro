# Review R8A — restore accepted R3/R4 changes after R8 scope mistake

Дата: 2026-07-15

R8 implementation is not accepted yet. During R8 the coder ran a broad `git restore` and removed three previously accepted, still-required changes. Restore them exactly; do not reset any other file and do not change R8 behavior.

## Scope

Allowed runtime files:

```text
.github/workflows/visual-regression.yml
infra/production/docker-compose.yml
infra/systemd/solarsage-api.service
infra/production/solarsage-github-deploy
scripts/prod-deploy.sh
.github/workflows/deploy-production.yml
docs/PRODUCTION_RUNBOOK.md
```

The first three are restoration-only. Do not use `git restore` on any path. Do not touch frozen paths. No commit, push, server access, or deploy.

## 1. Restore R3 visual workflow change exactly

In `.github/workflows/visual-regression.yml`, the `Wait for server` step must be the accepted bounded curl loop, not `npx wait-on`:

```yaml
      - name: Wait for server
        shell: bash
        run: |
          for attempt in {1..120}; do
            if curl -fsS http://127.0.0.1:3002/ >/dev/null 2>&1; then
              echo "Server is ready."
              exit 0
            fi
            if [ "$attempt" -lt 120 ]; then
              sleep 1
            fi
          done
          echo "Error: server did not become ready after 120 attempts." >&2
          exit 1
```

Do not alter the manual-only trigger, Playwright install/run, artifact upload, or port 3002.

## 2. Restore R3 PostgreSQL log rotation exactly

In `infra/production/docker-compose.yml`, under service `db` and after `restart: unless-stopped`, restore:

```yaml
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Keep loopback bind, healthcheck, volume, security options, image and credentials guards unchanged.

## 3. Restore R4 API runtime setting exactly

In `[Service]` of `infra/systemd/solarsage-api.service`, immediately after `EnvironmentFile`, restore:

```ini
# Disable PostgreSQL SSL mode because DB is on loopback (127.0.0.1:5433) in Docker and doesn't require TLS,
# and ProtectHome=true prevents asyncpg from reading user client certificates (~/.postgresql/postgresql.key).
Environment="PGSSLMODE=disable"
```

Keep `ProtectHome=true`, `ProtectSystem=full`, and all other hardening unchanged.

## 4. R8 review correction

Do not change the newly implemented R8 parser/source gate/wrapper/workflow unless a check proves a real defect. The wrapper may accept only the exact safe `deploy <40 lowercase hex>` command. Do not broaden it.

Do not run any broad restore/reset/checkout/clean command. Do not “clean” unrelated worktree paths. Existing R8/R7/R3/R4 diffs are intentional.

## 5. Checks

```bash
git diff --check
bash -n scripts/prod-deploy.sh
bash -n infra/production/solarsage-github-deploy
python3 - <<'PY'
from pathlib import Path
import yaml
for p in (Path('.github/workflows/deploy-production.yml'), Path('.github/workflows/visual-regression.yml')):
    yaml.safe_load(p.read_text())
    print(f'yaml_ok: {p}')
PY
grep -F 'max-size: "10m"' infra/production/docker-compose.yml
grep -F 'max-file: "3"' infra/production/docker-compose.yml
grep -F 'Environment="PGSSLMODE=disable"' infra/systemd/solarsage-api.service
grep -F 'sleep 1' .github/workflows/visual-regression.yml
! grep -F 'npx wait-on' .github/workflows/visual-regression.yml
systemd-analyze verify infra/systemd/solarsage-api.service infra/systemd/solarsage-sidecar.service infra/systemd/solarsage-frontend.service infra/systemd/solarsage-backup.service infra/systemd/solarsage-backup.timer
```

Report the exact restored files and confirm that frozen paths and prior changes were preserved. Stop after handoff.
