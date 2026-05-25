# ############################################################################
# AI_HEADER: MODULE_API_HEALTH
# ROLE: HTTP surface for liveness/version probe used by uptime checks and CI smoke.
# DEPENDENCIES: fastapi, app.core.config
# GRACE_ANCHORS: [HEALTH_PAYLOAD]
# ############################################################################

# START_MODULE_CONTRACT: M-API-BOOT.health
# purpose: Expose GET /api/health returning the canonical liveness payload
#   {status, version, git_sha}. Co-owned by M-API-BOOT as its public surface.
# owns:
#   - apps/api/app/api/health.py
# inputs:
#   - settings.app_version, settings.git_sha (from M-CONFIG)
# outputs:
#   - APIRouter mounting GET /api/health -> dict[str, str]
# dependencies:
#   - M-CONFIG
# side_effects:
#   - none (read-only handler)
# invariants:
#   - response shape is EXACTLY {status, version, git_sha}, all string-typed
#   - shape is part of the W-1.1 exit criterion; changes require ops coordination
# failure_policy:
#   - cannot fail under normal operation; failures bubble as HTTP 500
# non_goals:
#   - DB readiness, dependency probes, deep diagnostics
# END_MODULE_CONTRACT: M-API-BOOT.health

# START_MODULE_MAP: M-API-BOOT.health
# public_entrypoints:
#   - router
#   - health
# semantic_blocks:
#   - HEALTH_PAYLOAD: assembles and returns the {status, version, git_sha} dict
# owned_tests:
#   - apps/api/tests/test_health.py
# END_MODULE_MAP: M-API-BOOT.health

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/api/health")
async def health() -> dict[str, str]:
    # START_FUNCTION_CONTRACT: M-API-BOOT.health.health
    # purpose: Return a minimal JSON document used by uptime checks, CI smoke,
    #   and human verification of which build is currently deployed.
    # inputs: none (HTTP GET, no params, no body)
    # returns: dict with EXACTLY three string keys: status, version, git_sha
    # side_effects: none (git_sha resolution is delegated to M-CONFIG and is
    #   effectively idempotent within a process)
    # emitted_logs: none in W-1.1
    # error_behavior: cannot fail under normal operation; any failure is a
    #   bug in M-CONFIG and must surface as 500
    # END_FUNCTION_CONTRACT: M-API-BOOT.health.health

    # START_BLOCK: HEALTH_PAYLOAD
    return {
        "status": "ok",
        "version": settings.app_version,
        "git_sha": settings.git_sha,
    }
    # END_BLOCK: HEALTH_PAYLOAD
