# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_PROMO_RUNBOOK_CONTRACT
# ROLE: Static assertion test suite for PROMO_CAMPAIGN_RUNBOOK.md and PRODUCTION_RUNBOOK.md.
# DEPENDENCIES: pytest, pathlib, re
# GRACE_ANCHORS: [TEST_PROMO_RUNBOOK_CONTRACT]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PROMO-RUNBOOK-CONTRACT
# purpose: Validate static documentation invariants for promo operations runbook, event names, CLI commands, privacy placeholders, and rollback rules.
# owns:
#   - apps/api/tests/test_promo_runbook_contract.py
# inputs: docs/PROMO_CAMPAIGN_RUNBOOK.md and docs/PRODUCTION_RUNBOOK.md
# outputs: pytest execution assertions
# dependencies: none
# side_effects: none (reads documentation files)
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TEST-PROMO-RUNBOOK-CONTRACT

# START_MODULE_MAP: M-TEST-PROMO-RUNBOOK-CONTRACT
# public_entrypoints:
#   - test_promo_runbook_exists_and_has_grace_contract
#   - test_promo_runbook_contains_exact_event_names_and_error_codes
#   - test_promo_runbook_uses_active_container_cli_invocation
#   - test_promo_runbook_privacy_placeholders_and_no_shell_eval
#   - test_promo_runbook_incident_and_rollback_rules
#   - test_production_runbook_links_to_promo_runbook
# owned_tests:
#   - apps/api/tests/test_promo_runbook_contract.py
# END_MODULE_MAP: M-TEST-PROMO-RUNBOOK-CONTRACT

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMO_RUNBOOK_PATH = REPO_ROOT / "docs" / "PROMO_CAMPAIGN_RUNBOOK.md"
PROD_RUNBOOK_PATH = REPO_ROOT / "docs" / "PRODUCTION_RUNBOOK.md"


@pytest.fixture
def promo_runbook_text() -> str:
    assert PROMO_RUNBOOK_PATH.is_file(), f"Promo runbook not found at {PROMO_RUNBOOK_PATH}"
    return PROMO_RUNBOOK_PATH.read_text(encoding="utf-8")


@pytest.fixture
def prod_runbook_text() -> str:
    assert PROD_RUNBOOK_PATH.is_file(), f"Production runbook not found at {PROD_RUNBOOK_PATH}"
    return PROD_RUNBOOK_PATH.read_text(encoding="utf-8")


def test_promo_runbook_exists_and_has_grace_contract(promo_runbook_text: str) -> None:
    assert "AI_HEADER: DOC_PROMO_CAMPAIGN_RUNBOOK" in promo_runbook_text
    assert "START_MODULE_CONTRACT: M-DOC-PROMO-CAMPAIGN-RUNBOOK" in promo_runbook_text
    assert "END_MODULE_CONTRACT: M-DOC-PROMO-CAMPAIGN-RUNBOOK" in promo_runbook_text


def test_promo_runbook_contains_exact_event_names_and_error_codes(promo_runbook_text: str) -> None:
    # Exact event names
    for event_name in (
        "promo.campaign_created",
        "promo.offer_viewed",
        "promo.redemption_succeeded",
        "promo.redemption_rejected",
        "promo.redemption_failed",
        "promo.campaign_disabled",
    ):
        assert event_name in promo_runbook_text, f"Missing event name {event_name} in runbook"

    # Exact error codes
    for error_code in (
        "INVALID_CODE",
        "CAMPAIGN_EXPIRED",
        "CAMPAIGN_FULL",
        "ALREADY_REDEEMED",
        "PROFILE_INCOMPLETE",
        "RATE_LIMITED",
    ):
        assert error_code in promo_runbook_text, f"Missing error code {error_code} in runbook"

    # Canary threshold
    assert "max_redemptions <= 5" in promo_runbook_text


def test_promo_runbook_uses_active_container_cli_invocation(promo_runbook_text: str) -> None:
    # Active container docker exec
    assert "docker exec -i solarsage-api python -m app.cli.promo_campaign" in promo_runbook_text

    # Extract code blocks
    code_blocks = re.findall(r"```(?:bash)?(.*?)```", promo_runbook_text, re.DOTALL)
    for block in code_blocks:
        assert "uvicorn" not in block
        assert "8001" not in block
        assert "eval" not in block


def test_promo_runbook_privacy_placeholders_and_no_shell_eval(promo_runbook_text: str) -> None:
    # Placeholders
    assert "<OUTPUT_TOKEN>" in promo_runbook_text or "<CAMPAIGN_NAME>" in promo_runbook_text

    # No shell eval or source
    assert not re.search(r"\beval\b", promo_runbook_text)
    assert not re.search(r"\bsource\s+", promo_runbook_text)


def test_promo_runbook_incident_and_rollback_rules(promo_runbook_text: str) -> None:
    # Disable campaign first
    assert "Disable Campaign First" in promo_runbook_text or "disable" in promo_runbook_text.lower()

    # No down-migration after redemption
    assert "down-migration" in promo_runbook_text.lower() or "down-migrations" in promo_runbook_text.lower()

    # Forbid ad-hoc DELETE / UPDATE
    assert "DELETE" in promo_runbook_text
    assert "UPDATE" in promo_runbook_text


def test_production_runbook_links_to_promo_runbook(prod_runbook_text: str) -> None:
    assert "PROMO_CAMPAIGN_RUNBOOK.md" in prod_runbook_text
