# ############################################################################
# AI_HEADER: MODULE_JOBS — installed one-shot operator jobs package.
# ROLE: Hosts single-shot jobs runnable as `python -m app.jobs.<name>` inside
#       the canonical API image (no mutable checkout, no new harness).
# ############################################################################

# START_MODULE_CONTRACT: M-JOBS-INIT
# purpose: Package init for one-shot operator jobs.
# owns:
#   - apps/api/app/jobs/__init__.py
# inputs: none
# outputs: none (namespace marker)
# dependencies: none
# side_effects: none
# emitted_logs: none
# invariants: none
# failure_policy: none
# END_MODULE_CONTRACT: M-JOBS-INIT

# START_MODULE_MAP: M-JOBS-INIT
# public_entrypoints: none
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-JOBS-INIT
