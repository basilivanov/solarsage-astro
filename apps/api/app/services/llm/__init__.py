# ############################################################################
# AI_HEADER: MODULE_LLM_PACKAGE
# ROLE: LLM package init — export LLMService
# DEPENDENCIES: app.services.llm.service
# GRACE_ANCHORS: [LLM_SERVICE_EXPORT]
# ############################################################################

# START_MODULE_CONTRACT: M-LLM-PACKAGE
# purpose: Re-export LLMService from the llm package for clean imports.
# owns:
#   - apps/api/app/services/llm/__init__.py
# inputs:
#   - none (re-export only)
# outputs:
#   - LLMService class
# dependencies:
#   - M-LLM-SERVICE (service.py)
# side_effects:
#   - import-time only
# END_MODULE_CONTRACT: M-LLM-PACKAGE

# START_MODULE_MAP: M-LLM-PACKAGE
# public_entrypoints:
#   - LLMService
#   - HoraryGenerationError
#   - generate_election_narrative
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-LLM-PACKAGE

from app.services.llm.service import LLMService
from app.services.llm.client import HoraryGenerationError
from app.services.llm.election import generate_election_narrative

__all__ = ["LLMService", "HoraryGenerationError", "generate_election_narrative"]
