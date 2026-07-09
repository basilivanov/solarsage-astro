# ############################################################################
# AI_HEADER: MODULE_VERSIONS — canonical SolarSage V2 version identity constants.
# ROLE: Single source of truth for calculation/activation/scoring/payload versions
#       used by TodayService meta, cache keys, activation layer, and audit artifacts.
# ############################################################################

# START_MODULE_CONTRACT: M-VERSIONS
# purpose: Expose stable version strings for V1/V2 runtime identity.
# owns:
#   - apps/api/app/core/versions.py
# inputs: none (module-level constants).
# outputs: CALCULATION_VERSION, ACTIVATION_LAYER_VERSION, SCORING_V2_VERSION,
#          TODAY_V2_PAYLOAD_VERSION, TODAY_V1_PAYLOAD_VERSION, LEGACY_CALCULATION_VERSION.
# dependencies: none.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - V2 calculation identity is explicit (ss-calc-*).
#   - V2 scoring identity is explicit (ss-scoring-*).
#   - Activation layer identity is explicit (al-*).
# failure_policy: n/a (pure constants).
# END_MODULE_CONTRACT: M-VERSIONS

from __future__ import annotations

# V2 calculation identity (sidecar activation + V2 path)
CALCULATION_VERSION = "ss-calc-1.1.0"

# Activation layer schema/identity
ACTIVATION_LAYER_VERSION = "al-1.0"

# Scoring V2 identity
SCORING_V2_VERSION = "ss-scoring-2.0"

# Payload wire versions
TODAY_V2_PAYLOAD_VERSION = "today.v2"
TODAY_V1_PAYLOAD_VERSION = "today.v1"

# Legacy V1 calculation identity (intentionally "1" for backward compatibility)
LEGACY_CALCULATION_VERSION = "1"
LEGACY_SCORING_VERSION = 1
LEGACY_FRONTEND_PAYLOAD_VERSION = 1
V2_FRONTEND_PAYLOAD_VERSION = 2
