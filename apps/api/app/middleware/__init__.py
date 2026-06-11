# ############################################################################
# AI_HEADER: MODULE_MIDDLEWARE
# ROLE: Middleware package for request/response processing.
# GRACE_ANCHORS: [MIDDLEWARE_PACKAGE]
# ############################################################################

# START_MODULE_CONTRACT: M-MIDDLEWARE
# purpose: Middleware package init — exports middleware modules.
# owns:
#   - apps/api/app/middleware/__init__.py
# inputs:
#   - none (package init)
# outputs:
#   - middleware module exports
# dependencies:
#   - none
# side_effects:
#   - none (import-time only)
# invariants:
#   - empty init is acceptable for namespace packages
# failure_policy:
#   - N/A
# END_MODULE_CONTRACT: M-MIDDLEWARE

# START_MODULE_MAP: M-MIDDLEWARE
# public_entrypoints:
#   - middleware.correlation (CorrelationMiddleware)
# semantic_blocks:
#   - MIDDLEWARE_PACKAGE: package initialization
# END_MODULE_MAP: M-MIDDLEWARE
