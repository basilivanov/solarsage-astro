# ############################################################################
# AI_HEADER: TEST_LLM_SERVICE
# ROLE: Unit tests for LLM service (mocked Anthropic API).
# DEPENDENCIES: pytest, unittest.mock, app.services.llm_service
# GRACE_ANCHORS: [TEST_HEADLINE_GENERATION, TEST_READING_GENERATION]
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-LLM-SERVICE
# purpose: Test LLM service headline and reading generation with mocked API.
# owns:
#   - apps/api/tests/test_llm_service.py
# inputs:
#   - sample AstroSignal fixtures
# outputs:
#   - pytest test results
# dependencies:
#   - pytest, pytest-asyncio
#   - unittest.mock (for mocking Anthropic client)
#   - M-LLM-SERVICE
# invariants:
#   - all tests use mocked Anthropic client (no real API calls)
#   - tests verify structure, not content quality
# failure_policy:
#   - test failure → CI fails
# non_goals:
#   - no integration tests with real API (deferred)
#   - no prompt quality evaluation (deferred)
# END_MODULE_CONTRACT

# START_MODULE_MAP: M-TEST-LLM-SERVICE
# public_entrypoints:
#   - test_generate_headline
#   - test_generate_reading
# semantic_blocks:
#   - TEST_HEADLINE_GENERATION: mock API and verify headline structure
#   - TEST_READING_GENERATION: mock API and verify reading structure
# owned_tests: (self)
# END_MODULE_MAP

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm_service import LLMService
from app.schemas.normalization import AstroSignal


# START_BLOCK: TEST_FIXTURES
@pytest.fixture
def sample_signals():
    """Sample AstroSignal fixtures for testing."""
    return [
        AstroSignal(
            type="aspect",
            planet="Sun",
            target_planet="Jupiter",
            aspect_type="trine",
            orb=1.0,
            strength=0.9,
        ),
        AstroSignal(
            type="aspect",
            planet="Moon",
            target_planet="Venus",
            aspect_type="sextile",
            orb=2.0,
            strength=0.7,
        ),
        AstroSignal(
            type="aspect",
            planet="Mars",
            target_planet="Saturn",
            aspect_type="square",
            orb=3.0,
            strength=0.5,
        ),
    ]
# END_BLOCK: TEST_FIXTURES


# START_BLOCK: TEST_HEADLINE_GENERATION
@pytest.mark.asyncio
async def test_generate_headline(sample_signals):
    """LLM generates headline from day_status and top signals."""
    # Mock OpenRouter response
    mock_response_json = {
        "choices": [
            {"message": {"content": "День, когда удача на твоей стороне"}}
        ]
    }

    with patch("app.services.llm_service.httpx.AsyncClient") as mock_client_class:
        # Create mock response
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_response_json)
        mock_response.raise_for_status = MagicMock()

        # Create mock client
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        # Setup async context manager
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        service = LLMService()
        headline = await service.generate_headline("supportive", sample_signals)

        # Verify structure
        assert isinstance(headline, str)
        assert len(headline) > 0
        assert headline == "День, когда удача на твоей стороне"

        # Verify API was called once
        mock_client.post.assert_called_once()

        # Verify call parameters
        call_args = mock_client.post.call_args
        assert "openrouter.ai" in call_args.args[0]
        assert call_args.kwargs["json"]["model"] == "openai/gpt-4o-mini"
        assert call_args.kwargs["json"]["max_tokens"] == 100
        assert len(call_args.kwargs["json"]["messages"]) == 1
        assert call_args.kwargs["json"]["messages"][0]["role"] == "user"
        assert "supportive" in call_args.kwargs["json"]["messages"][0]["content"]
# END_BLOCK: TEST_HEADLINE_GENERATION


# START_BLOCK: TEST_READING_GENERATION
@pytest.mark.asyncio
async def test_generate_reading(sample_signals):
    """LLM generates reading paragraphs from scoring results."""
    # Mock OpenRouter response with multiple paragraphs
    mock_response_json = {
        "choices": [
            {"message": {"content": "Параграф 1.\n\nПараграф 2.\n\nПараграф 3."}}
        ]
    }

    with patch("app.services.llm_service.httpx.AsyncClient") as mock_client_class:
        # Create mock response
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_response_json)
        mock_response.raise_for_status = MagicMock()

        # Create mock client
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        # Setup async context manager
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        service = LLMService()
        paragraphs = await service.generate_reading(
            "supportive",
            sample_signals,
            {"career": 2, "relationships": 1},
        )

        # Verify structure
        assert isinstance(paragraphs, list)
        assert len(paragraphs) == 3
        assert all(isinstance(p, str) for p in paragraphs)
        assert paragraphs[0] == "Параграф 1."
        assert paragraphs[1] == "Параграф 2."
        assert paragraphs[2] == "Параграф 3."

        # Verify API was called once
        mock_client.post.assert_called_once()

        # Verify call parameters
        call_args = mock_client.post.call_args
        assert "openrouter.ai" in call_args.args[0]
        assert call_args.kwargs["json"]["model"] == "openai/gpt-4o-mini"
        assert call_args.kwargs["json"]["max_tokens"] == 500
        assert len(call_args.kwargs["json"]["messages"]) == 1
        assert call_args.kwargs["json"]["messages"][0]["role"] == "user"
        assert "supportive" in call_args.kwargs["json"]["messages"][0]["content"]
        assert "career" in call_args.kwargs["json"]["messages"][0]["content"]
# END_BLOCK: TEST_READING_GENERATION


# START_BLOCK: TEST_MAX_PARAGRAPHS
@pytest.mark.asyncio
async def test_generate_reading_max_paragraphs(sample_signals):
    """LLM reading is capped at 3 paragraphs."""
    # Mock response with 5 paragraphs
    mock_response_json = {
        "choices": [
            {"message": {"content": "P1.\n\nP2.\n\nP3.\n\nP4.\n\nP5."}}
        ]
    }

    with patch("app.services.llm_service.httpx.AsyncClient") as mock_client_class:
        # Create mock response
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_response_json)
        mock_response.raise_for_status = MagicMock()

        # Create mock client
        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        # Setup async context manager
        mock_client_class.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        service = LLMService()
        paragraphs = await service.generate_reading(
            "steady",
            sample_signals,
            {"career": 0, "relationships": 0},
        )

        # Verify max 3 paragraphs
        assert len(paragraphs) == 3
        assert paragraphs == ["P1.", "P2.", "P3."]
# END_BLOCK: TEST_MAX_PARAGRAPHS
