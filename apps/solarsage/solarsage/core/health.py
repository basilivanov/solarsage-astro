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
