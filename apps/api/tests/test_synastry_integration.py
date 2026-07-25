"""Integration tests for synastry feature."""

import pytest
from app.db.models import (
    SynastryAspectDetail,
    SynastryCreditSpend,
    SynastryFeedback,
    SynastryPartner,
    SynastryReport,
)


def test_synastry_models_exist():
    assert SynastryPartner.__tablename__ == "synastry_partners"
    assert SynastryReport.__tablename__ == "synastry_reports"
    assert SynastryAspectDetail.__tablename__ == "synastry_aspect_details"
    assert SynastryFeedback.__tablename__ == "synastry_feedback"
    assert SynastryCreditSpend.__tablename__ == "synastry_credit_spends"
