# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PROD_COMPOSE_CONTRACTS
# ROLE: Static contract tests for the canonical production compose file.
# DEPENDENCIES: pytest
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROD-COMPOSE-CONTRACTS
# purpose: Prove the canonical production compose declares GEONAMES_USERNAME
#   as a hard requirement (fail-closed :? interpolation, never an empty
#   default) so the P0 geo outage class cannot silently redeploy, and the
#   runbook no longer marks it optional.
# owns:
#   - apps/api/tests/test_prod_compose_contracts.py
# inputs: repo files (read-only)
# outputs: pytest assertions
# dependencies: none
# side_effects: none
# emitted_logs: n/a (tests)
# invariants:
#   - no docker/compose execution; pure static contract proof
# failure_policy: assertion failure on contract violation
# END_MODULE_CONTRACT: M-TEST-PROD-COMPOSE-CONTRACTS

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE = REPO_ROOT / "infra" / "production" / "docker-compose.app.yml"
RUNBOOK = REPO_ROOT / "docs" / "PRODUCTION_RUNBOOK.md"


def test_compose_requires_geonames_username_fail_closed() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert "GEONAMES_USERNAME: ${GEONAMES_USERNAME:?" in text, (
        "compose must require GEONAMES_USERNAME via :? interpolation"
    )
    assert "GEONAMES_USERNAME: ${GEONAMES_USERNAME:-}" not in text, (
        "compose must not default GEONAMES_USERNAME to empty"
    )


def test_runbook_lists_geonames_username_as_required() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "**GEONAMES_USERNAME**" in text
    assert "Optional keys: `APP_VERSION`, `LLM_MODEL`, `GEONAMES_USERNAME`" not in text
