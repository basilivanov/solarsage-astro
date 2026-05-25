SHELL := /bin/bash

# ----------------------------------------------------------------------
# Astro Makefile — DEV ONLY.
# Production targets (deploy / logs) are guarded until W-DEPLOY lands.
# See grace/development-plan.xml -> <future-waves> -> W-DEPLOY.
# ----------------------------------------------------------------------

.PHONY: help dev up down api web migrate db-create deploy backup logs solarsage

help:
	@echo "Dev targets:"
	@echo "  make up          - docker compose up -d (postgres + redis)"
	@echo "  make down        - docker compose down"
	@echo "  make dev         - up + hint for running services"
	@echo "  make api         - run FastAPI (apps/api) on :8000"
	@echo "  make web         - run Next.js (root app/) on :3000"
	@echo "  make migrate     - alembic upgrade head"
	@echo "  make db-create   - create role + db in Postgres (uses .env)"
	@echo ""
	@echo "Disabled until W-DEPLOY:"
	@echo "  make deploy / backup / logs / solarsage  (will exit 1)"

up:
	docker compose -f infra/docker-compose.yml up -d

down:
	docker compose -f infra/docker-compose.yml down

dev: up
	@echo ""
	@echo "Postgres + Redis are up."
	@echo "Open two terminals:"
	@echo "  1) make api        # FastAPI on :8000"
	@echo "  2) pnpm dev        # Next.js on :3000"
	@echo ""
	@echo "SolarSage is an EXTERNAL service. Start it from its own repo"
	@echo "and set SOLARSAGE_BASE_URL in .env."

api:
	$(MAKE) -C apps/api run

web:
	pnpm dev

migrate:
	$(MAKE) -C apps/api migrate

db-create:
	bash scripts/db-create.sh

# ---- Guarded: not implemented until W-DEPLOY -------------------------

deploy:
	@echo "ERROR: 'make deploy' is disabled until W-DEPLOY."
	@echo "scripts/deploy.sh is stale-guarded; see grace/development-plan.xml."
	@exit 1

backup:
	@echo "ERROR: 'make backup' is not implemented yet (W-DEPLOY)."
	@exit 1

logs:
	@echo "ERROR: 'make logs' requires systemd units that do not exist yet (W-DEPLOY)."
	@exit 1

solarsage:
	@echo "ERROR: SolarSage is an external service and runs in its own docker."
	@echo "Set SOLARSAGE_BASE_URL in .env and start it from the SolarSage repo."
	@exit 1
