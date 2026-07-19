# ############################################################################
# AI_HEADER: TESTS_CONFTEST — explicit fixtures for engine modes.
# ROLE: Non-production Moshier mode is an explicit opt-in fixture for the
#       calculation suites; production fail-closed tests do not use it.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-CONFTEST
# purpose: Provide the explicit `moshier_mode` fixture that marks a test
#   module as a NON-production approximation-engine suite. Nothing here sets
#   process env or weakens the production contract globally; production
#   fail-closed behavior is proven separately in test_ephemeris_runtime.py.
# owns:
#   - apps/solarsage/tests/conftest.py
# inputs: none.
# outputs: pytest fixtures.
# dependencies: solarsage.core.ephemeris_runtime.
# side_effects: monkeypatched settings per test using the fixture.
# emitted_logs: none.
# invariants:
#   - moshier_mode keeps app_env at non-production values.
#   - no global environment mutation at import time.
# failure_policy: n/a.
# END_MODULE_CONTRACT: M-TESTS-CONFTEST

import pytest

from solarsage.core import ephemeris_runtime as rt


@pytest.fixture()
def moshier_mode(monkeypatch):
    # Explicit non-production approximation-engine mode for calculation
    # suites that do not need the pinned Swiss artifact. Identity is reset
    # around each test so modes never leak between tests.
    monkeypatch.setattr(rt.settings, "ephemeris_allow_moshier", True)
    monkeypatch.setattr(rt.settings, "app_env", "development")
    rt._reset_identity_for_tests()
    yield
    rt._reset_identity_for_tests()
