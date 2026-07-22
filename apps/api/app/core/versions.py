# ############################################################################
# AI_HEADER: MODULE_VERSIONS — canonical SolarSage V2 version identity constants.
# ROLE: Single source of truth for calculation/activation/scoring/payload versions
#       used by TodayService meta, cache keys, activation layer, and audit artifacts.
# ############################################################################

# START_MODULE_CONTRACT: M-VERSIONS
# purpose: Expose stable version strings for V1/V2 runtime, wire, cache, and
#          compatibility identity.
# owns:
#   - apps/api/app/core/versions.py
# inputs: none (module-level constants).
# outputs: CALCULATION_VERSION, ACTIVATION_LAYER_VERSION, SCORING_V2_VERSION,
#          TODAY_V1_PAYLOAD_VERSION, TODAY_V2_PREVIOUS_PAYLOAD_VERSION,
#          TODAY_V2_PAYLOAD_VERSION, TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS,
#          PREVIOUS_V2_FRONTEND_PAYLOAD_VERSION, V2_FRONTEND_PAYLOAD_VERSION,
#          V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS, TODAY_CONTENT_VERSION.
# dependencies: solarsage_contracts.versions.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - V2 calculation identity is explicit (ss-calc-*).
#   - V2 scoring identity is explicit (ss-scoring-*).
#   - Activation layer identity is explicit (al-*).
#   - Fresh V2 emits today.v2.1/frontend=3/content=10.
#   - Previous today.v2/frontend=2 remains schema-compatible for cached inputs.
# failure_policy: n/a (pure constants).
# END_MODULE_CONTRACT: M-VERSIONS

# START_MODULE_MAP: M-VERSIONS
# public_entrypoints:
#   - module constants
# semantic_blocks:
#   - SHARED_RUNTIME_VERSIONS: shared sidecar/API calculation and activation identities.
#   - TODAY_WIRE_COMPATIBILITY: current/previous payload and frontend version pairs.
#   - TODAY_CONTENT_IDENTITY: public content version used by cache and metadata.
# owned_tests:
#   - apps/api/tests/test_today_meta_versions.py
#   - apps/api/tests/test_today_cache_v2_key.py
# END_MODULE_MAP: M-VERSIONS

from __future__ import annotations

from solarsage_contracts.versions import (
    ACTIVATION_LAYER_VERSION as ACTIVATION_LAYER_VERSION,
    CALCULATION_VERSION as CALCULATION_VERSION,
)

# Scoring V2 identity
SCORING_V2_VERSION = "ss-scoring-2.0"

# Payload wire versions
TODAY_V2_PREVIOUS_PAYLOAD_VERSION = "today.v2"
TODAY_V2_PAYLOAD_VERSION = "today.v2.1"
TODAY_V2_COMPATIBLE_PAYLOAD_VERSIONS = frozenset({
    TODAY_V2_PREVIOUS_PAYLOAD_VERSION,
    TODAY_V2_PAYLOAD_VERSION,
})
TODAY_V1_PAYLOAD_VERSION = "today.v1"

# Legacy V1 calculation identity (intentionally "1" for backward compatibility)
LEGACY_CALCULATION_VERSION = "1"
LEGACY_SCORING_VERSION = 1
LEGACY_FRONTEND_PAYLOAD_VERSION = 1
PREVIOUS_V2_FRONTEND_PAYLOAD_VERSION = 2
V2_FRONTEND_PAYLOAD_VERSION = 3
V2_COMPATIBLE_FRONTEND_PAYLOAD_VERSIONS = frozenset({
    PREVIOUS_V2_FRONTEND_PAYLOAD_VERSION,
    V2_FRONTEND_PAYLOAD_VERSION,
})

# Today public content identity
TODAY_CONTENT_VERSION = 10

# LLM prompt/content identity for Today: bumped when the prompt shape or
# content policy changes so stale cached payloads never pass as current.
TODAY_LLM_PROMPT_VERSION = 3
