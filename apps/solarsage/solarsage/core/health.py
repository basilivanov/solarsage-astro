
# ############################################################################
# AI_HEADER: MODULE_CORE_HEALTH
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/solarsage/core/health.py
# owns:
#   - apps/solarsage/solarsage/core/health.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# AI_HEADER
# module: M-SIDECAR-HEALTH-LOGIC
# wave: W-3.1, W-3.2, W-SOLARSAGE-SVC
# purpose: Health check logic (ephemeris validation + probe calculation)

import os
import swisseph as swe

from .config import settings


def check_health() -> tuple[bool, str]:
    """
    Check sidecar health.

    Returns:
        (ok, error_message)

    W-3.1: Check ephemeris path exists.
    W-3.2: Add probe calculation (SUN on now).
    W-SOLARSAGE-SVC: Use swisseph directly (no calculator dependency).
    """
    # Check ephemeris path
    if not os.path.exists(settings.ephemeris_path):
        return False, f"Ephemeris path not found: {settings.ephemeris_path}"

    # W-3.2: Probe calculation
    try:
        jd = swe.julday(2026, 5, 30, 12.0)  # Fixed date for probe
        result = swe.calc_ut(jd, swe.SUN)
        lon = result[0][0]

        # Check that longitude is reasonable (0-360)
        if not (0 <= lon <= 360):
            return False, "Probe calculation failed (invalid longitude)"
    except Exception as e:
        return False, f"Probe calculation failed: {str(e)}"

    return True, ""
