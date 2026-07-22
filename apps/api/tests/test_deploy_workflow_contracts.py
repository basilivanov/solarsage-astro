# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_DEPLOY_WORKFLOW_CONTRACTS — deploy workflow wiring.
# ROLE: Static contract proofs for .github/workflows/deploy-production.yml:
#       the artifact-acceptance migration step must run from apps/api (where
#       alembic.ini lives), never from the repo root.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-DEPLOY-WORKFLOW-CONTRACTS
# purpose: Fail closed if the artifact-acceptance migration command loses
#   its apps/api working directory (repo-root alembic exits 255 with a
#   missing script_location).
# owns:
#   - apps/api/tests/test_deploy_workflow_contracts.py
# inputs: the workflow YAML (read-only).
# outputs: assertions on the migration step wiring.
# dependencies: yaml, pathlib.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - The acceptance migration step declares working-directory: apps/api.
#   - Its run command invokes the venv alembic (no repo-root invocation).
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-DEPLOY-WORKFLOW-CONTRACTS

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy-production.yml"


def _acceptance_migration_step() -> dict:
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    steps = jobs["artifact-acceptance"]["steps"]
    for step in steps:
        if isinstance(step, dict) and step.get("name") == "Run migrations on the ephemeral acceptance DB":
            return step
    raise AssertionError("acceptance migration step not found in deploy-production.yml")


def test_acceptance_migration_runs_from_apps_api() -> None:
    step = _acceptance_migration_step()
    # The command must run from the app root where alembic.ini lives —
    # a repo-root invocation can never find the configuration.
    assert step.get("working-directory") == "apps/api"
    run = step["run"]
    assert "alembic upgrade head" in run
    assert "apps/api/.venv/bin/alembic" not in run  # no repo-root relative invocation
    assert ".venv/bin/alembic" in run
