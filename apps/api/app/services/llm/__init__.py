# ############################################################################
# AI_HEADER: LLM_PACKAGE — llm package init, re-exports LLMService and HoraryGenerationError
# ROLE: Public API of the modular llm/ package. Importers use
#       `from app.services.llm import LLMService, HoraryGenerationError`.
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Re-export public symbols from the llm package submodules.
# inputs: (none)
# returns: LLMService, HoraryGenerationError
# side_effects: none
# emitted_logs: none
# error_behavior: none
# END_MODULE_CONTRACT

from .service import LLMService
from .horary import HoraryGenerationError

__all__ = ["LLMService", "HoraryGenerationError"]
