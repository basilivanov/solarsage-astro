
# ############################################################################
# AI_HEADER: MODULE_CORE_HEALTH
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Module: health.py
# owns:
#   - apps/solarsage/solarsage/core/health.py
# inputs: Function args
# outputs: Return values
# dependencies: local modules
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - Health is ok ONLY when the pinned Swiss artifact verifies and the
#     engine probe returns FLG_SWIEPH (explicit moshier test mode excluded).
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-SIDECAR-HEALTH-LOGIC
# wave: W-3.1, W-3.2, W-SOLARSAGE-SVC
# purpose: Health check logic (ephemeris artifact validation + engine proof)

from .ephemeris_runtime import EphemerisError, EphemerisIdentity, verify_and_configure


def check_health() -> tuple[bool, str, EphemerisIdentity | None]:
    """
    Check sidecar health.

    Returns:
        (ok, error_message, identity_or_none)

    Fail-closed: any artifact/engine verification failure is unhealthy;
    a bare path-exists check is never sufficient (P0 ephemeris gate).
    """
    try:
        identity = verify_and_configure()
    except EphemerisError as exc:
        return False, str(exc), None
    return True, "", identity
