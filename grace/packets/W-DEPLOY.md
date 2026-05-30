# AI_HEADER
# module: M-DEPLOY-PACKET
# wave: W-DEPLOY
# purpose: Wave packet documenting deployment surface implementation

# W-DEPLOY — Re-derive authoritative deployment surface

## Decision

Docker Compose deployment with 4 services: db (PostgreSQL), api (FastAPI), solarsage (FastAPI), frontend (Nginx). Production-ready with health checks and migrations.

**Architecture:**
- PostgreSQL 15 with health checks and persistent volumes
- API service with automatic migrations on startup
- SolarSage sidecar service
- Frontend built with Vite, served via Nginx with API proxy
- Environment-based configuration via .env
- Automated deployment script with health verification

## Acceptance Criteria

- [x] docker-compose.yml with all services
- [x] Dockerfile for api, solarsage, frontend
- [x] nginx.conf for frontend reverse proxy
- [x] .env.example template with production defaults
- [x] scripts/deploy.sh deployment script (executable)
- [x] docs/DEPLOYMENT.md documentation
- [x] Health checks for all services
- [x] Database migrations run on startup

## Evidence

- File: `/opt/solarsage-astro/docker-compose.yml` — Service orchestration with health checks
- File: `/opt/solarsage-astro/apps/api/Dockerfile` — API image with migrations
- File: `/opt/solarsage-astro/apps/solarsage/Dockerfile` — SolarSage image
- File: `/opt/solarsage-astro/apps/web/Dockerfile` — Frontend multi-stage build
- File: `/opt/solarsage-astro/apps/web/nginx.conf` — Nginx config with API proxy
- File: `/opt/solarsage-astro/.env.example` — Environment template (updated from dev to production)
- File: `/opt/solarsage-astro/scripts/deploy.sh` — Deployment script (replaced stale version)
- File: `/opt/solarsage-astro/docs/DEPLOYMENT.md` — Complete deployment guide

## Negative Tests

- [ ] Deploy without .env → error "❌ .env file not found"
- [ ] API starts before db ready → waits for health check (depends_on with condition)
- [ ] Missing environment variable → Docker Compose fails with clear error
- [ ] Health check fails → deployment script exits with code 1
- [ ] Migration fails → API container fails to start

## Implementation Notes

**Replaced stale deploy.sh:**
- Old script referenced non-existent systemd units and VDS deployment
- New script uses Docker Compose with health checks and proper error handling

**Environment variables:**
- Updated .env.example from dev to production defaults
- Added AI_HEADER and W-DEPLOY attribution
- Preserved GRACE observability variables (GRACE_USER_SALT, GRACE_LOG_DEBUG)

**Health checks:**
- Database: pg_isready with 10s interval
- API: curl to /api/health endpoint
- SolarSage: curl to /v1/health endpoint

**Security considerations:**
- All secrets in .env (not committed)
- Database password via environment variable
- JWT_SECRET and GRACE_USER_SALT must be changed in production
