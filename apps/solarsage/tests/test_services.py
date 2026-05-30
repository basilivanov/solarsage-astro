# AI_HEADER
# module: M-TEST-SOLARSAGE-SERVICES
# wave: W-SOLARSAGE-SVC
# purpose: Service module tests

import pytest
from datetime import datetime, date

from solarsage.services.natal import NatalService
from solarsage.services.transits import TransitsService


def test_natal_service():
    """
    Test natal chart calculation.

    W-SOLARSAGE-SVC: Verify NatalService works.
    """
    service = NatalService()

    chart = service.calculate_natal_chart(
        date_str="1990-01-01",
        time_str="12:00",
        tz_str="UTC",
        latitude=55.75,
        longitude=37.62,
    )

    # Verify chart structure
    assert chart.birth_datetime == datetime(1990, 1, 1, 12, 0)
    assert chart.latitude == 55.75
    assert chart.longitude == 37.62

    # Verify positions
    assert chart.positions is not None
    assert len(chart.positions) > 0
    assert all('name' in p for p in chart.positions)
    assert all('longitude' in p for p in chart.positions)
    assert all('sign' in p for p in chart.positions)

    # Verify houses
    assert chart.houses is not None
    assert len(chart.houses) == 12
    assert all('number' in h for h in chart.houses)
    assert all('cusp' in h for h in chart.houses)

    # Verify special points
    assert chart.special_points is not None
    assert len(chart.special_points) >= 4  # ASC, MC, ARMC, Vertex
    assert any(sp['name'] == 'ASC' for sp in chart.special_points)
    assert any(sp['name'] == 'MC' for sp in chart.special_points)

    # Verify house system
    assert chart.house_system in ['PLACIDUS', 'WHOLE_SIGN']


def test_transits_service():
    """
    Test transits calculation.

    W-SOLARSAGE-SVC: Verify TransitsService works.
    """
    service = TransitsService()

    # Mock natal positions (Sun at 280°, Moon at 120°)
    natal_positions = [
        {'name': 'Sun', 'longitude': 280, 'latitude': 0, 'speed': 1.0, 'sign': 'Capricorn'},
        {'name': 'Moon', 'longitude': 120, 'latitude': 0, 'speed': 13.0, 'sign': 'Cancer'},
    ]

    transits = service.calculate_transits(
        date_str="2024-01-01",
        time_str="12:00",
        tz_str="UTC",
        natal_positions=natal_positions,
    )

    # Verify transits structure
    assert isinstance(transits, list)

    # If transits found, verify structure
    if len(transits) > 0:
        transit = transits[0]
        assert hasattr(transit, 'planet')
        assert hasattr(transit, 'aspect')
        assert hasattr(transit, 'natal_planet')
        assert hasattr(transit, 'orb')
        assert hasattr(transit, 'date')
        assert transit.date == date(2024, 1, 1)


def test_natal_service_high_latitude():
    """
    Test natal chart at high latitude (should use Whole Sign houses).

    W-SOLARSAGE-SVC: Verify house system selection.
    """
    service = NatalService()

    chart = service.calculate_natal_chart(
        date_str="1990-01-01",
        time_str="12:00",
        tz_str="UTC",
        latitude=65.0,  # High latitude
        longitude=25.0,
    )

    # Should use Whole Sign at high latitude
    assert chart.house_system == 'WHOLE_SIGN'


def test_transits_service_aspects():
    """
    Test that TransitsService detects major aspects.

    W-SOLARSAGE-SVC: Verify aspect detection.
    """
    service = TransitsService()

    # Verify aspect definitions
    assert 'conjunction' in service.ASPECTS
    assert 'opposition' in service.ASPECTS
    assert 'trine' in service.ASPECTS
    assert 'square' in service.ASPECTS
    assert 'sextile' in service.ASPECTS

    # Verify aspect angles
    assert service.ASPECTS['conjunction'][0] == 0
    assert service.ASPECTS['opposition'][0] == 180
    assert service.ASPECTS['trine'][0] == 120
    assert service.ASPECTS['square'][0] == 90
    assert service.ASPECTS['sextile'][0] == 60
