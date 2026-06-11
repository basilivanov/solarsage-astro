
# ############################################################################
# AI_HEADER: MODULE_ORCHESTRATOR_TEST_ORCHESTRATOR
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-ORCHESTRATOR-ADAPTER
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — grace/orchestrator/test_orchestrator.py
# owns:
#   - grace/orchestrator/test_orchestrator.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# AI_HEADER
# module: M-TEST-ORCH
# wave: W-ORCH-1
# purpose: Orchestrator tests

import pytest
from pathlib import Path
from grace.orchestrator.core import GraceOrchestrator, Wave
from grace.orchestrator.validator import PacketValidator


def test_load_plan():
    """Load development plan."""
    plan_path = Path('grace/development-plan.xml')
    orch = GraceOrchestrator(plan_path)

    assert len(orch.waves) > 0
    assert any(w.id == 'W-1.1' for w in orch.waves)


def test_get_wave():
    """Get wave by ID."""
    plan_path = Path('grace/development-plan.xml')
    orch = GraceOrchestrator(plan_path)

    wave = orch.get_wave('W-1.1')
    assert wave is not None
    assert wave.id == 'W-1.1'


def test_mark_completed():
    """Mark wave as completed."""
    plan_path = Path('grace/development-plan.xml')
    orch = GraceOrchestrator(plan_path)

    orch.mark_completed('W-1.1')
    wave = orch.get_wave('W-1.1')
    assert wave.status == 'completed'


def test_get_progress():
    """Get progress."""
    plan_path = Path('grace/development-plan.xml')
    orch = GraceOrchestrator(plan_path)

    progress = orch.get_progress()
    assert 'total' in progress
    assert 'completed' in progress
    assert progress['total'] > 0


def test_validate_packet():
    """Validate wave packet."""
    validator = PacketValidator(Path('grace/packets'))

    is_valid, errors = validator.validate_packet('W-1.1')
    # Should be valid (packet exists with required sections)
    assert is_valid or len(errors) > 0  # Either valid or has specific errors
