# Audit Report: Docs / Code Sync (Slice 1)

**Date:** 2026-07-25  
**Author:** Coder (opencode / gemini-3.6-flash-high)  
**Status:** Completed (READ-ONLY Research & Audit Report)  
**Target:** Reconcile all repository documentation (`docs/*.md`, `grace/*`, `PRODUCTION_RUNBOOK.md`, `AGENTS.md`) with the current `main` codebase.

---

## 1. Executive Summary

This audit evaluates all active documentation and GRACE artifacts against the `main` branch codebase.

### Key System Realities (`main` Branch):
- **Ports & Services:**
  - PostgreSQL DB: Port `5433` (container `solarsage-db`, Compose project `solarsage-prod`). Dev DB: Port `5434`.
  - API (FastAPI): Port `8000` (container `solarsage-api`, Compose project `solarsage-app`).
  - Frontend (Next.js): Port `3002` (container `solarsage-frontend`, Compose project `solarsage-app`).
  - Sidecar (SolarSage engine): Port `18091` (container `solarsage-sidecar`, Compose project `solarsage-app`).
  - Error Tracking (Bugsink): Port `18095` (container `solarsage-bugsink`, Compose project `solarsage-bugsink`, internal loopback).
  - Nginx: Ports `80` and `443` (Reverse proxy: `/api/` -> 8000, `/` -> 3002).
- **Authentication:**
  - Production: Strictly Telegram WebApp HMAC verification via `POST /api/auth/telegram`.
  - Development (`NODE_ENV=development`): Dev auth via `POST /api/auth/dev`.
- **Removed / Forbidden Services:**
  - ❌ `USE_FIXTURES` (completely removed; API required).
  - ❌ Prefect (completely removed; no systemd or compose units).
  - ❌ Manual `uvicorn` (forbidden; API runs strictly in Compose container).
  - ❌ Port 8001 as public API (forbidden; port 8001 is sidecar internal container port, host port is 18091).
- **Deployment Model:**
  - Minimal Compose path with immutable per-SHA digest-pinned OCI images + `infra/production/docker-compose.app.yml` + `/usr/local/libexec/solarsage/prod-orchestrator`.
  - Manual deployment workflow (`workflow_dispatch` on `main`).
- **Recent Slices & Features (Slices 01-20):**
  - **Named Promo Campaign Slices 01–20:** `M-API-PROMO`, `M-PROMO-CAMPAIGN-SERVICE`, `M-PROMO-ADMIN-SERVICE`, `M-PROMO-RATE-LIMITER`, `M-FRONTEND-API-PROMO`, `M-PROMO-CAMPAIGN-GATE`, `M-PROMO-CONFIRMATION-SHEET`.
  - **Prod Error Loop Slices 01–04:** `M-ERROR-TRACKING`, Bugsink container (`solarsage-bugsink`, port 18095), `scripts/prod-errors/`.
  - **Nginx Transport Privacy & Rate Limiting:** `log_format astro_privacy`, `Referrer-Policy: strict-origin`, `120r/m` rate limit on `^/api/promo/(preview|redeem)$`.
  - **Shared Credit Lock (Slice 17):** `ElectionService` uses `select_spendable_credit(..., lock=True)` with `FOR UPDATE`.

---

## 2. Top-Level Docs (`docs/*.md`) Audit Matrix & Verdicts

| Document File | Status Verdict | Details & Required Fixes |
|---|---|---|
| `docs/00_Обзор_продукта.md` | **OK** | Fully aligns with product mission, core value, and Today screen design. |
| `docs/01_MVP_экраны_и_навигация.md` | **OK** | Accurately describes MVP screens, routes, and bottom navigation model. |
| `docs/02_Today_screen.md` | **OK** | Accurately describes Today screen structure and top flags inline expansion. |
| `docs/03_Почему_так_у_меня.md` | **OK** | Accurately describes inline "Why for me" structure and sections. |
| `docs/04_SolarSage_нормализация_скоринг_кеширование.md` | **OK** | Form of calculation pipeline and caching remains canonical. |
| `docs/05_API_contracts_и_TodayPayload.md` | **SUPERSEDED** | Historical specification superseded by Pydantic models in `apps/api/app/schemas/*` and generated contracts. Has banner. |
| `docs/06_Натальная_карта_контракт_и_фронт.md` | **OK** | Accurately describes natal chart payload versioning and section block structure. |
| `docs/07_Backend_architecture_draft.md` | **STALE-task-queue-redis-mentions** | Mentions Celery/RQ/Dramatiq/arq/Redis task queues which are not used in current `main` architecture. Needs note. |
| `docs/08_Frontend_current_state_and_alignment.md` | **OK** | Accurately describes frontend v0 alignment, routes, and Zod validation. |
| `docs/09_Project_transfer_context.md` | **OK** | Accurate project summary, MVP scope, access control rules, and horary summary. |
| `docs/10_GRACE_Project_Agent_Guide.md` | **OK** | Active agent onboarding guide and GRACE reading order. |
| `docs/11_SolarSage_rewrite_TZ.md` | **SUPERSEDED** | Historical ТЗ for SolarSage sidecar rewrite. Add historical banner. |
| `docs/12_Microcopy_dictionary_TZ.md` | **SUPERSEDED** | Historical ТЗ for microcopy dictionary. Add historical banner. |
| `docs/13_Evening_checkin_TZ.md` | **SUPERSEDED** | Historical ТЗ for evening checkin. Add historical banner. |
| `docs/14_SolarSage_scoring_rewrite_TZ.md` | **SUPERSEDED** | Historical ТЗ for scoring rewrite. Add historical banner. |
| `docs/15_CI_без_GitHub_Actions_из_v0.md` | **STALE-prefect-vercel-github-actions-mentions** | Outdated claim of no `.github/workflows/` (workflows now exist) and mentions of Vercel/Prefect. Needs updating in Slice 3. |
| `docs/15_SolarSage_v2_activation_audit_TZ.md` | **SUPERSEDED** | Historical ТЗ for activation audit. Add historical banner. |
| `docs/16_Horary_questions_TZ.md` | **SUPERSEDED** | Historical ТЗ for horary feature wave. Add historical banner. |
| `docs/17_Natal_landing_and_generation_TZ.md` | **SUPERSEDED** | Historical ТЗ for natal report landing and generation. Add historical banner. |
| `docs/18_GRACE_оркестратор_подключение_TZ.md` | **SUPERSEDED** | Historical ТЗ for GRACE orchestrator adapter. Add historical banner. |
| `docs/19_Profile_three_locations_TZ.md` | **SUPERSEDED** | Historical ТЗ for 3-locations profile. Add historical banner. |
| `docs/20_YooKassa_payment_TZ.md` | **SUPERSEDED** | Historical ТЗ for YooKassa billing integration. Add historical banner. |
| `docs/21_MVP_blockers_TZ.md` | **SUPERSEDED** | Historical ТЗ for MVP blockers cleanup. Add historical banner. |
| `docs/ADR-001_Headless_Testing.md` | **OK** | Accurately documents decision on headless testing. |
| `docs/DEPLOY.md` | **SUPERSEDED** | Replaced by `PRODUCTION_RUNBOOK.md`. Already contains historical banner. |
| `docs/DEPLOYMENT.md` | **STALE-missing-bugsink** | Active deployment guide; needs port 18095 Bugsink sidecar addition. |
| `docs/FAILURE_HANDLING_CANON.md` | **OK** | Active failure handling policy canon. |
| `docs/GRACE_CANON.md` | **OK** | Active policy baseline canon for GRACE methodology. |
| `docs/MANIFEST.md` | **STALE-docs-index** | Documentation manifest index missing recent runbooks and slice docs. |
| `docs/MANUAL_TESTING_CHECKLIST.md` | **OK** | Manual testing checklist. |
| `docs/monitoring-setup.md` | **STALE-internal-routes-prod-visibility** | Describes extended health and metrics endpoints; needs note that `policy.internal_routes_enabled = False` in prod. |
| `docs/ORCHESTRATOR.md` | **OK** | Accurately describes `scripts/grace-orch` CLI wave tracker. |
| `docs/PRODUCTION_RUNBOOK.md` | **OK** | Primary production runbook (updated with Bugsink §2.3 and promo link §3.5). |
| `docs/PROMO_CAMPAIGN_RUNBOOK.md` | **OK** | Primary operational runbook for named promo campaigns. |
| `docs/README_Структура_документации.md` | **STALE-structure-index** | Documentation index needs links to new runbooks (`PROMO_CAMPAIGN_RUNBOOK.md`). |
| `docs/SOLARSAGE_ARCHITECTURE.md` | **OK** | Internal architecture specification for SolarSage sidecar. |
| `docs/visual-regression-testing.md` | **OK** | Visual regression testing guide. |
| `docs/zhanna_natal_friendly_v3.md` | **SUPERSEDED** | Historical natal copy document. Add historical banner. |

---

## 3. GRACE Infrastructure (`grace/*`) Audit Matrix & Verdicts

| GRACE File | Status Verdict | Details & Required Fixes for Slice 2 |
|---|---|---|
| `grace/canon.yaml` | **OK** | Active adoption policy and slice registry path declaration. |
| `grace/knowledge-graph.xml` | **STALE-missing-new-modules** | Missing 8 new modules from recent waves: `M-API-PROMO`, `M-PROMO-CAMPAIGN-SERVICE`, `M-PROMO-ADMIN-SERVICE`, `M-PROMO-RATE-LIMITER`, `M-FRONTEND-API-PROMO`, `M-PROMO-CAMPAIGN-GATE`, `M-PROMO-CONFIRMATION-SHEET`, `M-ERROR-TRACKING`. |
| `grace/IMPLEMENTATION_STATUS.md` | **STALE-outdated-wave-count** | Dated 2026-05-31 (53 waves). Missing `W-NAMED-PROMO-CAMPAIGN`, `W-PROD-ERROR-LOOP`, `W-FRONTEND-OBSERVABILITY`, `W-HORARY`, `W-ELECTION`. Needs updating in Slice 2. |
| `grace/README.md` | **STALE-slice-table-missing-promo** | Slice registry table is missing `SLICE-PROMO-CAMPAIGN` and `SLICE-ERROR-TRACKING`. |
| `grace/ROLES.md` | **OK** | Agent role contracts. |
| `grace/development-plan.xml` | **STALE-missing-new-waves** | Missing waves for promo campaigns, prod error loop, horary, and election. |
| `grace/development-plan.patch.md` | **SUPERSEDED** | Historical patch log. |
| `grace/development-plan.canon-log.patch.md` | **SUPERSEDED** | Historical patch log. |
| `grace/requirements.xml` | **STALE-prefect-mentions** | Invariant `INV-ORCHESTRATOR-ADAPTER` mentions Prefect (which was removed). Needs updating. |
| `grace/technology.xml` | **STALE-prefect-redis-mentions** | Stack section contains `<queue>arq + Redis</queue>` and `<agent-orchestration>Prefect...</agent-orchestration>`. Needs removal of Prefect/Redis and addition of Bugsink (port 18095). |
| `grace/frontend.paths` | **STALE-missing-promo-paths** | Missing `components/promo/**/*.tsx` and `lib/api/promo.ts`. |
| `grace/verification-matrix.md` | **OK** | Already updated with `UC-PROMO-REDEEM`. |

---

## 4. Discrepancy Inventory & Priority Fixes

### Priority Fixes for Slice 2 (`grace/` artifacts):
1. **`grace/knowledge-graph.xml`**:
   - Register 8 new modules:
     - `M-API-PROMO` (`apps/api/app/api/promo.py`)
     - `M-PROMO-CAMPAIGN-SERVICE` (`apps/api/app/services/promo_campaign_service.py`)
     - `M-PROMO-ADMIN-SERVICE` (`apps/api/app/services/promo_admin_service.py`)
     - `M-PROMO-RATE-LIMITER` (`apps/api/app/services/promo_rate_limiter.py`)
     - `M-FRONTEND-API-PROMO` (`lib/api/promo.ts`)
     - `M-PROMO-CAMPAIGN-GATE` (`components/promo/promo-campaign-gate.tsx`)
     - `M-PROMO-CONFIRMATION-SHEET` (`components/promo/promo-confirmation-sheet.tsx`)
     - `M-ERROR-TRACKING` (`apps/api/app/services/error_tracking.py`)
2. **`grace/IMPLEMENTATION_STATUS.md`**:
   - Update wave completion log with recent completed waves (`W-NAMED-PROMO-CAMPAIGN`, `W-PROD-ERROR-LOOP`, `W-FRONTEND-OBSERVABILITY`, `W-HORARY`, `W-ELECTION`).
3. **`grace/technology.xml`**:
   - Remove Prefect and arq/Redis queue references.
   - Add Bugsink error tracking container (`solarsage-bugsink`, port 18095).
4. **`grace/requirements.xml`**:
   - Clean up Prefect references in `INV-ORCHESTRATOR-ADAPTER`.
5. **`grace/frontend.paths`**:
   - Add `components/promo/**/*.tsx` and `lib/api/promo.ts`.

---

### Priority Fixes for Slice 3 (`docs/` artifacts):
1. **Add Historical Banners (`SUPERSEDED`)** to feature ТЗ docs:
   - `docs/11_SolarSage_rewrite_TZ.md`
   - `docs/12_Microcopy_dictionary_TZ.md`
   - `docs/13_Evening_checkin_TZ.md`
   - `docs/14_SolarSage_scoring_rewrite_TZ.md`
   - `docs/15_SolarSage_v2_activation_audit_TZ.md`
   - `docs/16_Horary_questions_TZ.md`
   - `docs/17_Natal_landing_and_generation_TZ.md`
   - `docs/18_GRACE_оркестратор_подключение_TZ.md`
   - `docs/19_Profile_three_locations_TZ.md`
   - `docs/20_YooKassa_payment_TZ.md`
   - `docs/21_MVP_blockers_TZ.md`
   - `docs/zhanna_natal_friendly_v3.md`
2. **`docs/15_CI_без_GitHub_Actions_из_v0.md`**:
   - Update text: GitHub Actions workflows are now active in `.github/workflows/`. Remove Vercel/Prefect references.
3. **`docs/07_Backend_architecture_draft.md`**:
   - Add note that Redis/Celery task queues were replaced by internal asyncio background tasks and background task functions.
4. **`docs/DEPLOYMENT.md`**:
   - Add Bugsink sidecar port 18095 to ports table and compose files.
5. **`docs/MANIFEST.md` & `docs/README_Структура_документации.md`**:
   - Update document index with links to `PROMO_CAMPAIGN_RUNBOOK.md` and Bugsink documentation.

---

## 5. Candidate Files for GRACE Markers Backfill (Slice 4)

The following active files in `apps/api/app/`, `lib/`, and `components/` are missing `MODULE_MAP`, `START_BLOCK`, or `owned_tests` annotations and are prioritized for Slice 4 backfill (max 5 files per iteration):

### Priority Group 1 (Backend Core Services & APIs):
1. `apps/api/app/api/access.py`
2. `apps/api/app/api/checkin.py`
3. `apps/api/app/services/checkin_service.py`
4. `apps/api/app/services/canon_service.py`
5. `apps/api/app/services/activation_layer_service.py`

### Priority Group 2 (Frontend Core Services & Libs):
6. `lib/today.ts`
7. `lib/profile.ts`
8. `lib/access.ts`
9. `lib/calendar.ts`
10. `lib/chat.ts`

### Priority Group 3 (Frontend Screen Components):
11. `components/profile/profile-screen.tsx`
12. `components/onboarding/onboarding-flow.tsx`
13. `components/calendar/calendar-screen.tsx`
14. `components/readings/readings-screen.tsx`
15. `components/app-shell.tsx`

---

## 6. Top-10 Most Critical Discrepancies Summary

1. **`grace/knowledge-graph.xml` Missing Promo & Error Loop Modules:**
   - 8 newly implemented core modules (`M-API-PROMO`, `M-PROMO-CAMPAIGN-SERVICE`, `M-PROMO-ADMIN-SERVICE`, `M-PROMO-RATE-LIMITER`, `M-FRONTEND-API-PROMO`, `M-PROMO-CAMPAIGN-GATE`, `M-PROMO-CONFIRMATION-SHEET`, `M-ERROR-TRACKING`) are missing from the project knowledge graph.
2. **`grace/IMPLEMENTATION_STATUS.md` Outdated Wave Count:**
   - Shows 53/53 waves from 2026-05-31, ignoring `W-NAMED-PROMO-CAMPAIGN`, `W-PROD-ERROR-LOOP`, `W-FRONTEND-OBSERVABILITY`, `W-HORARY`, `W-ELECTION`.
3. **Outdated Prefect / Task Queue References in `grace/technology.xml` and `grace/requirements.xml`:**
   - Mentions arq/Redis queues and Prefect orchestrator execution, whereas Prefect and Redis were removed from production stack.
4. **Outdated Claims on GitHub Actions in `docs/15_CI_без_GitHub_Actions_из_v0.md`:**
   - Asserts no `.github/workflows/` exist, whereas active workflows (`e2e.yml`, `visual-regression.yml`, `deploy.yml`) are now used.
5. **Unmarked Historical Feature ТЗ (Docs 11-21):**
   - Feature specs (11, 12, 13, 14, 15_v2, 16, 17, 18, 19, 20, 21) lack explicit `SUPERSEDED` banners, causing potential confusion between initial design intent and final post-refactoring implementation.
6. **Missing Bugsink Sidecar in `docs/DEPLOYMENT.md`:**
   - `docs/DEPLOYMENT.md` lists sidecar 18091 but does not list port 18095 (`solarsage-bugsink`).
7. **`docs/07_Backend_architecture_draft.md` Celery/Redis Queue Mentions:**
   - Recommends Celery/RQ/Dramatiq/arq and Redis, which contradicts the single-process asyncio background task model.
8. **Missing `components/promo/` Paths in `grace/frontend.paths`:**
   - `grace/frontend.paths` whitelist excludes `components/promo/**/*.tsx` and `lib/api/promo.ts`.
9. **`docs/monitoring-setup.md` Production Endpoint Visibility:**
   - Documents `/api/health/extended` and `/api/metrics` without clarifying that `policy.internal_routes_enabled = False` hides them in production.
10. **`docs/README_Структура_документации.md` & `docs/MANIFEST.md` Index Drift:**
    - Documentation indexes do not list the newly added operational runbooks (`PROMO_CAMPAIGN_RUNBOOK.md`) or Bugsink error loop documentation.
