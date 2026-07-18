# Review R2 — SHA context and final deployment semantics

Дата: 2026-07-15

R1 gates зелёные. Перед приёмкой исправить только два точечных момента.

## 1. `OLD_SHA` вычисляется до `cd`

В `scripts/prod-deploy.sh` сейчас `OLD_SHA=$(git rev-parse HEAD ...)` выполняется до:

```bash
cd /opt/solarsage-astro
```

Если script вызван из `/home/astro` (как будет через forced SSH command), `OLD_SHA` становится `unknown` даже при исправном git checkout.

Переместить вычисление `OLD_SHA` после успешного `cd /opt/solarsage-astro` и до git fetch/checkout. Не менять формат handoff и не печатать secrets.

## 2. Добавить bounded SSH transport timeout в deploy workflow

В `.github/workflows/deploy-production.yml` к `ssh` добавить:

```text
-o ConnectTimeout=15
-o ServerAliveInterval=30
-o ServerAliveCountMax=3
```

Это не меняет безопасность host-key verification, но предотвращает бесконечно зависший GitHub runner.

После этого повторить:

```bash
bash -n scripts/prod-deploy.sh scripts/prod-backup.sh
git diff --check
systemd-analyze verify infra/systemd/solarsage-*.service infra/systemd/solarsage-backup.timer
POSTGRES_USER=astro POSTGRES_PASSWORD=dummy POSTGRES_DB=astro \
  docker compose -f infra/production/docker-compose.yml config >/tmp/solarsage-prod-compose.yml
python3 scripts/check_logging_guardrails.py
bash scripts/check_prod_guard.sh
apps/api/.venv/bin/python -m pytest apps/api/tests/test_health.py -q
```

Commit/push/server mutations по-прежнему запрещены. После handoff остановиться.
