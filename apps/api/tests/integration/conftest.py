# AI_HEADER
# module: M-TEST-INTEGRATION-CONFTEST
# wave: W-TEST-1
# purpose: Fixtures for integration tests with mocked external services

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def mock_solarsage_client():
    """Mock SolarSage client for integration tests."""
    with patch("app.services.today_service.get_solarsage_client") as mock_func:
        mock_instance = MagicMock()

        # Mock get_natal with all 12 houses
        mock_natal_response = {
            "planets": [
                {"name": "Sun", "longitude": 69.5, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"},
                {"name": "Moon", "longitude": 120.0, "latitude": 0.0, "speed": 13.0, "sign": "Leo"},
                {"name": "Mercury", "longitude": 80.0, "latitude": 0.0, "speed": 1.5, "sign": "Gemini"},
                {"name": "Venus", "longitude": 100.0, "latitude": 0.0, "speed": 1.2, "sign": "Cancer"},
                {"name": "Mars", "longitude": 200.0, "latitude": 0.0, "speed": 0.5, "sign": "Libra"},
            ],
            "houses": [
                {"number": 1, "cusp": 0.0},
                {"number": 2, "cusp": 30.0},
                {"number": 3, "cusp": 60.0},
                {"number": 4, "cusp": 90.0},
                {"number": 5, "cusp": 120.0},
                {"number": 6, "cusp": 150.0},
                {"number": 7, "cusp": 180.0},
                {"number": 8, "cusp": 210.0},
                {"number": 9, "cusp": 240.0},
                {"number": 10, "cusp": 270.0},
                {"number": 11, "cusp": 300.0},
                {"number": 12, "cusp": 330.0},
            ],
            "special_points": [],
            "house_system": "PLACIDUS",
        }
        mock_instance.get_natal = AsyncMock(return_value=mock_natal_response)

        # Mock get_transits
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
def mock_llm_service():
    """Mock LLM service for integration tests."""
    with patch("app.services.today_service.LLMService") as mock_class:
        mock_instance = MagicMock()

        mock_instance.generate_headline = AsyncMock(return_value="Test Headline")

        mock_instance.generate_reading = AsyncMock(return_value=[
            "Test reading paragraph 1.",
            "Test reading paragraph 2.",
        ])

        mock_instance.generate_notes = AsyncMock(return_value="Сегодня важно проявить гибкость и внимание к деталям.")

        mock_instance.generate_why_sections = AsyncMock(return_value=[
            {"id": "why-1", "layer": "main_theme", "title": "Главная тема дня", "blocks": [{"kind": "paragraph", "text": "Тестовое объяснение."}]},
            {"id": "why-2", "layer": "daily_layer", "title": "Быстрый слой дня", "blocks": [{"kind": "paragraph", "text": "Тестовый слой."}]},
            {"id": "why-3", "layer": "personal_activation", "title": "Почему это задевает именно тебя", "blocks": [{"kind": "paragraph", "text": "Тест."}]},
            {"id": "why-4", "layer": "period_background", "title": "Фон периода", "blocks": [{"kind": "paragraph", "text": "Тест."}]},
            {"id": "why-5", "layer": "amplifiers", "title": "Что усиливает этот день", "blocks": [{"kind": "paragraph", "text": "Тест."}]},
            {"id": "why-6", "layer": "softeners", "title": "Что смягчает этот день", "blocks": [{"kind": "paragraph", "text": "Тест."}]},
            {"id": "why-7", "layer": "manifestation_zones", "title": "Через какие сферы это проявляется", "blocks": [{"kind": "bullets", "items": ["Работа", "Отношения"]}]},
            {"id": "why-8", "layer": "astrological_meaning", "title": "Астрологический смысл дня", "blocks": [{"kind": "paragraph", "text": "Тест."}]},
            {"id": "why-9", "layer": "practical_meaning", "title": "Что это значит практически", "blocks": [{"kind": "bullets", "items": ["Совет 1"]}]},
        ])

        mock_class.return_value = mock_instance
        yield mock_instance
