# Local commit — production bootstrap code

Дата: 2026-07-15

Архитектор принял R2. Сделать один локальный commit, без push и без server mutations.

## Exact stage scope

```text
.github/workflows/ci.yml
.github/workflows/visual-regression.yml
.github/workflows/deploy-production.yml
docs/PRODUCTION_RUNBOOK.md
docs/work/2026-07-15_production-server-bootstrap/
infra/nginx/astro.vasiliy-ivanov.ru.conf
infra/production/docker-compose.yml
infra/systemd/solarsage-api.service
infra/systemd/solarsage-sidecar.service
infra/systemd/solarsage-frontend.service
infra/systemd/solarsage-backup.service
infra/systemd/solarsage-backup.timer
scripts/prod-backup.sh
scripts/prod-deploy.sh
```

Не добавлять frozen paths:

```text
.grace/
artifacts/design/
docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md
grace.db
skills/
```

Перед commit:

```bash
git diff --check
git diff --cached --check
git diff --cached --name-only
```

Commit:

```bash
git commit -m "feat(ops): add production deployment stack"
```

После commit подтвердить:

- branch `infra/production-bootstrap`;
- parent `f1804dadcde85270d70e2529e6d0e04ba9b56ca0`;
- tracked worktree clean;
- push not performed;
- frozen paths remain untracked.

Вернуть exact commit SHA и остановиться.
