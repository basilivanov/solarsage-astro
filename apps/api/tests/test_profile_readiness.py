# ############################################################################
# AI_HEADER: MODULE_TESTS_PROFILE_READINESS
# ROLE: Unit tests for base onboarding and strict natal profile readiness helpers and 409 exception shape.
# DEPENDENCIES: pytest, fastapi, app.db.models, app.services.profile_service, app.services.natal_context_service
# GRACE_ANCHORS: [PROFILE_READINESS_TESTS]
# WAVE: W-NAMED-PROMO-CAMPAIGN
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-PROFILE-READINESS
# purpose: Validate base onboarding missing_onboarding_fields, strict natal missing_profile_fields, is_profile_complete, 409 exception shape, zero coordinates handling, and profile_hash immutability.
# owns:
#   - apps/api/tests/test_profile_readiness.py
# inputs: UserProfile mock instances
# outputs: Pytest execution assertions
# dependencies:
#   - app.db.models (UserProfile)
#   - app.services.profile_service (missing_onboarding_fields)
#   - app.services.natal_context_service (NatalContextService)
# side_effects: none (pure function unit tests)
# failure_policy: raise assertions
# END_MODULE_CONTRACT: M-TESTS-PROFILE-READINESS

# START_MODULE_MAP: M-TESTS-PROFILE-READINESS
# public_entrypoints:
#   - test_missing_onboarding_fields_individual
#   - test_missing_profile_fields_individual
#   - test_gender_none_individual
#   - test_base_complete_unknown_time
#   - test_invalid_gender_handling
#   - test_complete_profile
#   - test_zero_coordinates_are_valid
#   - test_validate_profile_completeness_http_409_shape
#   - test_onboarded_user_with_missing_birth_time_does_not_mutate
#   - test_compute_profile_hash_regression
# owned_tests:
#   - apps/api/tests/test_profile_readiness.py
# END_MODULE_MAP: M-TESTS-PROFILE-READINESS

import uuid
import pytest
from datetime import date, time
from decimal import Decimal as D
from fastapi import HTTPException

from app.db.models import UserProfile
from app.services.profile_service import missing_onboarding_fields
from app.services.natal_context_service import NatalContextService


def create_complete_profile() -> UserProfile:
    return UserProfile(
        user_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        first_name="Test",
        gender="female",
        is_onboarded=True,
        birthday=date(1990, 1, 1),
        birth_time=time(12, 0, 0),
        birth_city="Moscow",
        birth_lat=D("55.75"),
        birth_lon=D("37.62"),
        birth_tz="Europe/Moscow",
    )


def test_missing_onboarding_fields_individual():
    """Test missing_onboarding_fields identifies each base field individually in deterministic order."""
    # None profile
    assert missing_onboarding_fields(None) == ["birthday", "birth_city", "gender"]

    # Missing birthday
    p1 = create_complete_profile()
    p1.birthday = None
    assert missing_onboarding_fields(p1) == ["birthday"]

    # Missing birth_city (falsy only)
    p2 = create_complete_profile()
    p2.birth_city = None
    assert missing_onboarding_fields(p2) == ["birth_city"]

    p2_empty = create_complete_profile()
    p2_empty.birth_city = ""
    assert missing_onboarding_fields(p2_empty) == ["birth_city"]

    # Whitespace-only birth_city is historically truthy for base onboarding
    p2_space = create_complete_profile()
    p2_space.birth_city = "   "
    assert missing_onboarding_fields(p2_space) == []

    # Missing gender
    p3 = create_complete_profile()
    p3.gender = None
    assert missing_onboarding_fields(p3) == ["gender"]


def test_missing_profile_fields_individual():
    """Test missing_profile_fields identifies each strict natal field individually in deterministic order."""
    # None profile
    assert NatalContextService.missing_profile_fields(None) == [
        "birthday",
        "birth_time",
        "birth_lat",
        "birth_lon",
        "birth_tz",
        "gender",
    ]

    # Test each field individually
    fields_to_clear = ["birthday", "birth_time", "birth_lat", "birth_lon", "birth_tz"]
    for field in fields_to_clear:
        p = create_complete_profile()
        setattr(p, field, None)
        assert NatalContextService.missing_profile_fields(p) == [field]


def test_gender_none_individual():
    """Test gender=None individually returns ['gender']."""
    p = create_complete_profile()
    p.gender = None
    assert NatalContextService.missing_profile_fields(p) == ["gender"]


def test_base_complete_unknown_time():
    """Base complete + unknown birth_time -> base helper is complete, natal helper returns missing birth_time."""
    p = create_complete_profile()
    p.birth_time = None

    assert missing_onboarding_fields(p) == []
    assert NatalContextService.missing_profile_fields(p) == ["birth_time"]
    assert NatalContextService.is_profile_complete(p) is False


def test_invalid_gender_handling():
    """Invalid gender (e.g. 'other' or 'unknown') is reported as missing 'gender' for both helpers."""
    p = create_complete_profile()
    p.gender = "other"

    assert missing_onboarding_fields(p) == ["gender"]
    assert NatalContextService.missing_profile_fields(p) == ["gender"]
    assert NatalContextService.is_profile_complete(p) is False


def test_complete_profile():
    """Fully populated profile returns empty missing lists and True for completion."""
    p = create_complete_profile()

    assert missing_onboarding_fields(p) == []
    assert NatalContextService.missing_profile_fields(p) == []
    assert NatalContextService.is_profile_complete(p) is True


def test_zero_coordinates_are_valid():
    """Zero coordinates (lat=0, lon=0) are valid and NOT reported as missing."""
    p = create_complete_profile()
    p.birth_lat = D("0.0")
    p.birth_lon = D("0.0")

    assert NatalContextService.missing_profile_fields(p) == []
    assert NatalContextService.is_profile_complete(p) is True


def test_validate_profile_completeness_http_409_shape():
    """_validate_profile_completeness raises HTTPException 409 with exact detail shape."""
    p = create_complete_profile()
    p.birth_time = None
    p.birth_tz = None

    with pytest.raises(HTTPException) as exc_info:
        NatalContextService._validate_profile_completeness(p)

    err = exc_info.value
    assert err.status_code == 409
    assert err.detail == {
        "message": "Profile is incomplete",
        "missingFields": ["birth_time", "birth_tz"],
    }


def test_onboarded_user_with_missing_birth_time_does_not_mutate():
    """Profile with is_onboarded=True and birth_time=None returns missing_fields=['birth_time'] and does not mutate profile."""
    p = create_complete_profile()
    p.is_onboarded = True
    p.birth_time = None

    missing = NatalContextService.missing_profile_fields(p)

    assert missing == ["birth_time"]
    assert p.is_onboarded is True
    assert p.birth_time is None


def test_compute_profile_hash_regression():
    """compute_profile_hash output remains deterministic and matches exact canonical hash b9b22d3a769a575d."""
    p = create_complete_profile()
    hash_val = NatalContextService.compute_profile_hash(p)

    assert hash_val == "b9b22d3a769a575d"
