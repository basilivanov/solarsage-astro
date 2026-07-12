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

# ---- Real API proof (W3B) --------------------------------------------

PROOF_DATE ?= 2026-07-08
PROOF_OUT ?= /tmp/solarsage-v2-real-api-proof.json
PROOF_TRANSPORT ?= asgi
PROOF_BASE_URL ?= http://127.0.0.1:8000

unexport DATE OUT TRANSPORT BASE_URL
unexport PROOF_DATE PROOF_OUT PROOF_TRANSPORT PROOF_BASE_URL

ifneq ($(strip $(value DATE)),)
PROOF_RUN_DATE := $(value DATE)
else
PROOF_RUN_DATE := $(value PROOF_DATE)
endif

ifneq ($(strip $(value OUT)),)
PROOF_RUN_OUT := $(value OUT)
else
PROOF_RUN_OUT := $(value PROOF_OUT)
endif

ifneq ($(strip $(value TRANSPORT)),)
PROOF_RUN_TRANSPORT := $(value TRANSPORT)
else
PROOF_RUN_TRANSPORT := $(value PROOF_TRANSPORT)
endif

ifneq ($(strip $(value BASE_URL)),)
PROOF_RUN_BASE_URL := $(value BASE_URL)
else
PROOF_RUN_BASE_URL := $(value PROOF_BASE_URL)
endif

export PROOF_RUN_DATE PROOF_RUN_OUT PROOF_RUN_TRANSPORT PROOF_RUN_BASE_URL

.PHONY: prove-today-v2-real
prove-today-v2-real:
	@APP_ENV=development DEV_MODE=false \
	SOLARSAGE_V2_ENABLED=true \
	SOLARSAGE_V2_DUAL_RUN=false \
	SOLARSAGE_V2_FRONTEND_ENABLED=false \
	PYTHONPATH=apps/api \
	apps/api/.venv/bin/python scripts/prove_today_v2_real_api.py \
		--transport "$${PROOF_RUN_TRANSPORT}" \
		--base-url "$${PROOF_RUN_BASE_URL}" \
		--date "$${PROOF_RUN_DATE}" \
		--out "$${PROOF_RUN_OUT}"

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

.PHONY: audit-day audit-day-live audit-day-freeze audit-downstream-v2 audit-golden

# Prefer explicit mode targets. Bare audit-day fails fast so frozen baseline
# is never silently treated as live production proof.
audit-day:
	@echo "ERROR: choose audit-day-live or audit-day-freeze explicitly."
	@echo "  make audit-day-live  USER_ID=... DATE=YYYY-MM-DD"
	@echo "  make audit-day-freeze USER_ID=... DATE=YYYY-MM-DD"
	@exit 1

audit-day-live:
	apps/api/.venv/bin/python scripts/audit_today.py --mode live-production --user-id $(USER_ID) --date $(DATE) --out artifacts/audit/$(DATE)

audit-day-freeze:
	apps/api/.venv/bin/python scripts/audit_today.py --mode frozen-baseline --user-id $(USER_ID) --date $(DATE) --out artifacts/audit/$(DATE)

audit-downstream-v2:
	apps/api/.venv/bin/python scripts/audit_downstream_v2.py --user-id $(USER_ID) --date $(DATE) --out artifacts/audit/$(DATE)/downstream

audit-golden:
	python3 scripts/check_audit_golden.py
