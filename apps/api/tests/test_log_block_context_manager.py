
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_LOG_BLOCK_CONTEXT_MANAGER
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for log_block_context_manager.py behavior
# owns:
#   - apps/api/tests/test_log_block_context_manager.py
# inputs: Mocks, fixtures
# outputs: Assertion results
# dependencies: local modules
# side_effects: n/a (tests)
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-LOG-BLOCK-CONTEXT-MANAGER
# wave: W-1.6
# purpose: Test log_block context manager for context variables scoping.

from __future__ import annotations

from app.core.logging import (
    build_envelope,
    log_block,
    bind_log_context,
    clear_log_context,
    slice_var,
    module_var,
    block_var,
)


def test_log_block_overrides_and_restores_context():
    """log_block must override context variables inside block and restore them after."""
    clear_log_context()
    bind_log_context(
        correlation_id="corr-1",
        slice="W-OUTER",
        module="M-OUTER",
        block="OUTER_BLOCK",
    )

    # Outer context check
    env = build_envelope("system.startup")
    assert env["slice"] == "W-OUTER"
    assert env["module"] == "M-OUTER"
    assert env["block"] == "OUTER_BLOCK"

    # Inner context override
    with log_block(slice="W-INNER", module="M-INNER", block="INNER_BLOCK"):
        env_inner = build_envelope("system.startup")
        assert env_inner["slice"] == "W-INNER"
        assert env_inner["module"] == "M-INNER"
        assert env_inner["block"] == "INNER_BLOCK"

    # Restoration check
    env_restored = build_envelope("system.startup")
    assert env_restored["slice"] == "W-OUTER"
    assert env_restored["module"] == "M-OUTER"
    assert env_restored["block"] == "OUTER_BLOCK"


def test_log_block_partial_override():
    """log_block must allow partial overrides without resetting other context variables."""
    clear_log_context()
    bind_log_context(
        correlation_id="corr-1",
        slice="W-OUTER",
        module="M-OUTER",
        block="OUTER_BLOCK",
    )

    with log_block(block="PARTIAL_BLOCK"):
        env = build_envelope("system.startup")
        assert env["slice"] == "W-OUTER"
        assert env["module"] == "M-OUTER"
        assert env["block"] == "PARTIAL_BLOCK"

    env_restored = build_envelope("system.startup")
    assert env_restored["block"] == "OUTER_BLOCK"
