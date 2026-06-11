# ############################################################################
# AI_HEADER: MODULE_SERVICES
# ROLE: Services package init
# GRACE_ANCHORS: [SERVICES_PACKAGE]
# ############################################################################

# START_MODULE_CONTRACT: M-SERVICES
# purpose: Package init for all service modules.
# owns:
#   - apps/api/app/services/__init__.py
# inputs:
#   - none (package init)
# outputs:
#   - service module exports
# dependencies:
#   - none
# side_effects:
#   - none (import-time only)
# END_MODULE_CONTRACT: M-SERVICES

# START_MODULE_MAP: M-SERVICES
# public_entrypoints:
#   - all service modules
# semantic_blocks:
#   - SERVICES_PACKAGE: package initialization
# END_MODULE_MAP: M-SERVICES

"""M-AUTH-TG / M-PROFILE service package marker."""
