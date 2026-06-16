# ############################################################################
# AI_HEADER: LLM_SERVICE_SHIM — backward-compatible re-export shim
# ROLE: Deprecated import path `from app.services.llm_service import LLMService`.
#       All real code lives in app.services.llm package. This file is a
#       temporary shim for import compatibility.
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Re-export LLMService and HoraryGenerationError from llm/ package.
# inputs: (none — re-export only)
# returns: LLMService, HoraryGenerationError
# side_effects: none
# emitted_logs: none
# error_behavior: none
# END_MODULE_CONTRACT

from app.services.llm import LLMService, HoraryGenerationError

__all__ = ["LLMService", "HoraryGenerationError"]
