# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_BILLING_REBILL_JOB — rebill job logging contract.
# ROLE: Proves the operator job emits canonical structured events (never raw
#       print): kill-switch skip, attempts summary, redacted failure — and
#       keeps the exit-code contract.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BILLING-REBILL-JOB
# purpose: Directed tests for apps/api/app/jobs/billing_rebill.py.
# owns:
#   - apps/api/tests/test_billing_rebill_job.py
# inputs: monkeypatched settings/SessionLocal/BillingService.
# outputs: exit-code + emitted-event assertions.
# dependencies: app.jobs.billing_rebill, app.core.config.settings.
# side_effects: none (fd-captured stdout only).
# emitted_logs: none.
# invariants:
#   - Kill-switch first: disabled recurrent -> billing.rebill_skipped, exit 0.
#   - Completed run -> billing.rebill_completed with numeric attempts payload.
#   - Unexpected failure -> redacted system.error (kind only), exit 1.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-BILLING-REBILL-JOB

from __future__ import annotations

import json

from app.core.config import settings
from app.jobs import billing_rebill


def _emitted_events(capfd) -> list[dict]:
    out, _ = capfd.readouterr()
    events = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return [e for e in events if "event" in e]


def test_kill_switch_disabled_emits_rebill_skipped(capfd, monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", False)

    rc = billing_rebill.main()

    assert rc == 0
    events = _emitted_events(capfd)
    assert [e["event"] for e in events] == ["billing.rebill_skipped"]
    skip = events[0]
    assert skip["module"] == "M-JOBS-BILLING-REBILL"
    assert skip["block"] == "REBILL_JOB"
    assert skip["slice"] == "W-6.1"
    # The envelope hashes the bound correlation id (h1_...), never raw.
    assert skip["correlation_id"]


def test_completed_run_emits_attempts_summary(capfd, monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class _FakeBillingService:
        def __init__(self, session):
            pass

        async def rebill_due_subscriptions(self) -> int:
            return 3

    monkeypatch.setattr("app.db.session.SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr("app.services.billing_service.BillingService", _FakeBillingService)

    rc = billing_rebill.main()

    assert rc == 0
    events = _emitted_events(capfd)
    assert [e["event"] for e in events] == ["billing.rebill_completed"]
    completed = events[0]
    assert completed["payload"] == {"attempts": 3}
    assert completed["module"] == "M-JOBS-BILLING-REBILL"


def test_unexpected_failure_emits_redacted_system_error(capfd, monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_recurrent_enabled", True)

    class _FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    class _BoomService:
        def __init__(self, session):
            pass

        async def rebill_due_subscriptions(self) -> int:
            raise RuntimeError("database secret connection details here")

    monkeypatch.setattr("app.db.session.SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr("app.services.billing_service.BillingService", _BoomService)

    rc = billing_rebill.main()

    assert rc == 1
    events = _emitted_events(capfd)
    assert [e["event"] for e in events] == ["system.error"]
    failure = events[0]
    assert failure["level"] == "error"
    assert failure["error"] == {"kind": "RuntimeError"}
    # The raw exception message (potential internals/PII) never reaches the log.
    assert "database secret" not in json.dumps(failure)
