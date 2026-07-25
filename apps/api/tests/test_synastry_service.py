"""Unit tests for SynastryService orchestration."""

import pytest
from app.services.synastry_service import SynastryService


def test_synastry_service_import():
    assert SynastryService is not None


def test_synastry_service_methods():
    methods = [
        "create_partner_and_report",
        "run_report_pipeline",
        "get_aspect_drilldown",
        "submit_feedback",
        "delete_partner",
    ]
    for method in methods:
        assert hasattr(SynastryService, method)
