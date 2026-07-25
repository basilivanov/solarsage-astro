"""Unit tests for SynastryService orchestration."""

import pytest
from app.services.synastry_service import SynastryService


def test_synastry_service_import():
    assert SynastryService is not None
