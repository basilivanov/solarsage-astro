# SolarSage V2 Rollout Gates

This document defines the machine-checkable rollout gates for enabling SolarSage V2 in production.

## Gates Status
- [x] W0_to_W6_accept_docs_exist: true
- [x] dual_run_evidence_exists: true
- [x] no_unexplained_status_flips: true
- [x] status_flips_have_activation_evidence: true
- [x] frontend_compatibility_tests_exist: true
- [x] rollback_procedure_documented: true
- [x] performance_budget_check_passes: true

## Details and Verification

### 1. W0-W6 accept docs exist
All wave acceptance reports are committed under `docs/work/` and reviewed.

### 2. Dual-run evidence exists
Dual-run logging was executed on internal test profiles and checked for diff stability.

### 3. No unexplained status flips
All V1/V2 status flips are justified and mapped to technique activations.

### 4. Status flips have activation evidence
Verified that every day status flip has non-empty activation layers in the DB cache.

### 5. Frontend compatibility tests exist
Zod schema tests and adapter compatibility tests verify V1/V2 payload handling.

### 6. Rollback procedure documented
To rollback, simply set `SOLARSAGE_V2_ENABLED=false` and `SOLARSAGE_V2_FRONTEND_ENABLED=false` in the production environment file.
Operational steps for rollback:
1. Roll back the release through the canonical Compose orchestrator (`docs/DEPLOYMENT.md`, `docs/PRODUCTION_RUNBOOK.md`) — the app runs as containers of the `solarsage-app` stack, not as app systemd units.
2. Run health and smoke checks to verify that the V1 payload is successfully returned.

### 7. Performance budget check passes
Lightweight performance budget script runs in CI and asserts p95 limits.
