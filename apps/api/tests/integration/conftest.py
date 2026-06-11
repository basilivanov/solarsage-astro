
# ############################################################################
# AI_HEADER: MODULE_INTEGRATION_CONFTEST
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/integration/conftest.py
# owns:
#   - apps/api/tests/integration/conftest.py
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
# module: M-TEST-INTEGRATION-CONFTEST
# wave: W-TEST-1
# purpose: Fixtures for integration tests — only external HTTP mocked

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def mock_solarsage_client():
    """Mock SolarSage client for integration tests."""
    with patch("app.clients.solarsage_client.get_solarsage_client") as mock_func, \
         patch("app.services.natal_context_service.get_solarsage_client", mock_func), \
         patch("app.services.today_service.get_solarsage_client", mock_func), \
         patch("app.services.horary_service.get_solarsage_client", mock_func):
        mock_instance = MagicMock()

        mock_natal_response = {
            "planets": [
                {"name": "Sun", "longitude": 69.5, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"},
                {"name": "Moon", "longitude": 120.0, "latitude": 0.0, "speed": 13.0, "sign": "Leo"},
                {"name": "Mercury", "longitude": 80.0, "latitude": 0.0, "speed": 1.5, "sign": "Gemini"},
                {"name": "Venus", "longitude": 100.0, "latitude": 0.0, "speed": 1.2, "sign": "Cancer"},
                {"name": "Mars", "longitude": 200.0, "latitude": 0.0, "speed": 0.5, "sign": "Libra"},
            ],
            "houses": [
                {"number": 1, "cusp": 0.0, "sign": "Aries"},
                {"number": 2, "cusp": 30.0, "sign": "Taurus"},
                {"number": 3, "cusp": 60.0, "sign": "Gemini"},
                {"number": 4, "cusp": 90.0, "sign": "Cancer"},
                {"number": 5, "cusp": 120.0, "sign": "Leo"},
                {"number": 6, "cusp": 150.0, "sign": "Virgo"},
                {"number": 7, "cusp": 180.0, "sign": "Libra"},
                {"number": 8, "cusp": 210.0, "sign": "Scorpio"},
                {"number": 9, "cusp": 240.0, "sign": "Sagittarius"},
                {"number": 10, "cusp": 270.0, "sign": "Capricorn"},
                {"number": 11, "cusp": 300.0, "sign": "Aquarius"},
                {"number": 12, "cusp": 330.0, "sign": "Pisces"},
            ],
            "special_points": [],
            "house_system": "PLACIDUS",
        }
        mock_instance.get_natal = AsyncMock(return_value=mock_natal_response)

        mock_transits_response = {
            "planets": [
                {"name": "Sun", "longitude": 150.0, "latitude": 0.0, "speed": 1.0, "sign": "Virgo"},
            ],
            "special_points": [],
        }
        mock_instance.get_transits = AsyncMock(return_value=mock_transits_response)

        mock_func.return_value = mock_instance
        yield mock_instance


@pytest.fixture(autouse=True)
def mock_httpx():
    """Block ALL HTTP calls — LLM falls through to placeholder.
    SemanticService, ScoringService, NormalizationService run REAL code.
    Only external HTTP (OpenRouter, DeepSeek) is blocked."""
    with patch("httpx.AsyncClient") as mock_class:
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("No external HTTP in tests"))
        mock_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_class.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_client
