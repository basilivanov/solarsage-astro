# ############################################################################
# AI_HEADER: MODULE_CLIENTS
# ROLE: HTTP clients package for external service integrations.
# GRACE_ANCHORS: [CLIENTS_PACKAGE]
# WAVE: W-3.4
# ############################################################################

# START_MODULE_CONTRACT: M-CLIENTS
# purpose: Package init for external API clients.
# owns:
#   - apps/api/app/clients/__init__.py
# inputs:
#   - none (package init)
# outputs:
#   - solarsage_client module
# dependencies:
#   - none
# side_effects:
#   - none (import-time only)
# END_MODULE_CONTRACT: M-CLIENTS

# START_MODULE_MAP: M-CLIENTS
# public_entrypoints:
#   - solarsage_client (SolarSageClient)
# semantic_blocks:
#   - CLIENTS_PACKAGE: package initialization
# END_MODULE_MAP: M-CLIENTS
