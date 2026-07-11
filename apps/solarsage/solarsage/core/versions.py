# ############################################################################
# AI_HEADER: MODULE_SIDECAR_VERSIONS — sidecar-local version identity constants.
# ROLE: Sidecar package cannot import API constants; keep literals in sync via
#       contract tests that compare expected values.
# ############################################################################

from __future__ import annotations

# Must match apps/api/app/core/versions.py CALCULATION_VERSION
CALCULATION_VERSION = "ss-calc-1.2.0"

# Must match apps/api/app/core/versions.py ACTIVATION_LAYER_VERSION
ACTIVATION_LAYER_VERSION = "al-1.1"
