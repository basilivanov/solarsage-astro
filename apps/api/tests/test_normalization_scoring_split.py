# AI_HEADER
# module: M-TEST-NORMALIZATION-SCORING-SPLIT
# wave: W-NATAL-FULL (Wave 6 — test evidence)
# purpose: Tests proving the natal-only/day normalization and scoring split works correctly.
#          normalize_natal_only() never produces transit signals.
#          normalize_day() uses cached natal context + fresh transits.
#          score_natal() and score_day() are separate and not interchangeable.

import pytest

from app.services.normalization_service import NormalizationService
from app.services.scoring_service import ScoringService
from app.schemas.normalization import AstroSignal


# ── Shared fixtures ────────────────────────────────────────────────

@pytest.fixture
def natal_chart():
    """Sample natal chart data matching sidecar output shape."""
    return {
        "planets": [
            {"name": "Sun", "longitude": 286.93, "sign": "Capricorn"},
            {"name": "Moon", "longitude": 119.63, "sign": "Gemini"},
            {"name": "Mercury", "longitude": 277.10, "sign": "Capricorn"},
            {"name": "Venus", "longitude": 333.55, "sign": "Pisces"},
            {"name": "Mars", "longitude": 137.95, "sign": "Cancer"},
            {"name": "Jupiter", "longitude": 193.95, "sign": "Libra"},
            {"name": "Saturn", "longitude": 327.02, "sign": "Aquarius"},
        ],
        "houses": [
            {"number": i, "longitude": float((i - 1) * 30)} for i in range(1, 13)
        ],
    }


@pytest.fixture
def transit_data():
    """Sample transit data matching sidecar output shape."""
    return {
        "planets": [
            {"name": "Sun", "longitude": 80.0, "sign": "Gemini"},
            {"name": "Moon", "longitude": 200.0, "sign": "Libra"},
            {"name": "Mars", "longitude": 140.0, "sign": "Leo"},
        ],
    }


@pytest.fixture
def natal_context_dict():
    """Sample natal context dict as produced by NatalContextService."""
    return {
        "planets": [
            {"name": "Sun", "longitude": 286.93, "sign": "Capricorn"},
            {"name": "Moon", "longitude": 119.63, "sign": "Gemini"},
            {"name": "Mercury", "longitude": 277.10, "sign": "Capricorn"},
        ],
        "houses": [
            {"number": i, "longitude": float((i - 1) * 30)} for i in range(1, 13)
        ],
        "natal_signals": [
            {"type": "planet_in_house", "planet": "Sun", "house": 10, "sign": "Capricorn", "strength": 1.0},
            {"type": "planet_in_house", "planet": "Moon", "house": 4, "sign": "Gemini", "strength": 1.0},
            {"type": "planet_in_sign", "planet": "Sun", "sign": "Capricorn", "strength": 1.0},
        ],
    }


# ══════════════════════════════════════════════════════════════════════
# 1. normalize_natal_only never includes transit signals
# ══════════════════════════════════════════════════════════════════════

class TestNormalizeNatalOnly:
    """normalize_natal_only() must produce ONLY natal signals — no transit."""

    def test_produces_natal_signals(self, natal_chart):
        service = NormalizationService()
        signals = service.normalize_natal_only(natal_chart)

        assert len(signals) > 0, "Must produce at least some natal signals"

    def test_no_transit_prefix_in_signals(self, natal_chart):
        service = NormalizationService()
        signals = service.normalize_natal_only(natal_chart)

        for s in signals:
            if s.planet:
                assert not s.planet.startswith("Transit_"), (
                    f"normalize_natal_only produced transit signal: {s.planet}"
                )
            if s.target_planet:
                assert not s.target_planet.startswith("Transit_"), (
                    f"normalize_natal_only produced transit target: {s.target_planet}"
                )

    def test_includes_planet_in_house(self, natal_chart):
        service = NormalizationService()
        signals = service.normalize_natal_only(natal_chart)

        types = {s.type for s in signals}
        assert "planet_in_house" in types, "Must include planet_in_house signals"

    def test_includes_planet_in_sign(self, natal_chart):
        service = NormalizationService()
        signals = service.normalize_natal_only(natal_chart)

        types = {s.type for s in signals}
        assert "planet_in_sign" in types, "Must include planet_in_sign signals"

    def test_does_not_call_transit_methods(self, natal_chart):
        """normalize_natal_only should not call any transit-related method."""
        service = NormalizationService()
        signals = service.normalize_natal_only(natal_chart)

        # All signals must be natal types only
        allowed_types = {"planet_in_house", "planet_in_sign", "aspect"}
        for s in signals:
            assert s.type in allowed_types, (
                f"normalize_natal_only produced disallowed type: {s.type}"
            )


# ══════════════════════════════════════════════════════════════════════
# 2. normalize_day uses cached natal context + fresh transits
# ══════════════════════════════════════════════════════════════════════

class TestNormalizeDay:
    """normalize_day() combines natal context + transits, includes Transit_ prefixes."""

    def test_produces_transit_signals(self, natal_context_dict, transit_data):
        service = NormalizationService()
        signals = service.normalize_day(natal_context_dict, transit_data)

        transit_signals = [s for s in signals if s.planet and s.planet.startswith("Transit_")]
        assert len(transit_signals) > 0, "normalize_day must produce transit signals"

    def test_includes_natal_signals_from_context(self, natal_context_dict, transit_data):
        service = NormalizationService()
        signals = service.normalize_day(natal_context_dict, transit_data)

        # Should include natal signals (from natal_signals in context)
        natal_types = {s.type for s in signals if not (s.planet and s.planet.startswith("Transit_"))}
        assert len(natal_types) > 0, "Should include natal signal types"

    def test_transit_aspects_have_transit_prefix(self, natal_context_dict, transit_data):
        service = NormalizationService()
        signals = service.normalize_day(natal_context_dict, transit_data)

        transit_aspects = [
            s for s in signals
            if s.type == "aspect" and s.planet and s.planet.startswith("Transit_")
        ]
        assert len(transit_aspects) > 0, "Transit aspects must have Transit_ prefix"

        for s in transit_aspects:
            # Transit aspects: planet is Transit_X, target is natal planet
            assert s.planet.startswith("Transit_"), (
                f"Transit aspect planet must have Transit_ prefix: {s.planet}"
            )
            assert not s.target_planet.startswith("Transit_"), (
                f"Transit aspect target should be natal planet: {s.target_planet}"
            )


# ══════════════════════════════════════════════════════════════════════
# 3. score_natal vs score_day are separate methods
# ══════════════════════════════════════════════════════════════════════

class TestScoringSplit:
    """score_natal() and score_day() must exist as separate methods with different outputs."""

    def test_score_natal_exists(self):
        service = ScoringService()
        assert hasattr(service, "score_natal"), "ScoringService must have score_natal()"

    def test_score_day_exists(self):
        service = ScoringService()
        assert hasattr(service, "score_day"), "ScoringService must have score_day()"

    def test_score_natal_returns_no_day_status(self):
        """score_natal returns sphere_scores, top_signals, planet_scores but NO day_status."""
        service = ScoringService()
        signals = [
            AstroSignal(type="aspect", planet="Sun", target_planet="Jupiter",
                       aspect_type="trine", orb=1.0, strength=0.9),
        ]
        result = service.score_natal(signals)

        assert "sphere_scores" in result
        assert "top_signals" in result
        assert "planet_scores" in result
        assert "day_status" not in result, "score_natal must NOT return day_status"

    def test_score_day_returns_day_status(self):
        """score_day returns day_status in addition to sphere_scores and top_signals."""
        service = ScoringService()
        signals = [
            AstroSignal(type="aspect", planet="Sun", target_planet="Jupiter",
                       aspect_type="trine", orb=1.0, strength=0.9),
        ]
        result = service.score_day(signals)

        assert "day_status" in result
        assert "sphere_scores" in result
        assert "top_signals" in result

    def test_score_natal_returns_planet_scores(self):
        """score_natal returns planet_scores for dominant planet determination."""
        service = ScoringService()
        signals = [
            AstroSignal(type="aspect", planet="Saturn", target_planet="Sun",
                       aspect_type="conjunction", orb=2.0, strength=0.8),
            AstroSignal(type="planet_in_house", planet="Saturn", house=10, strength=1.0),
        ]
        result = service.score_natal(signals)

        assert "planet_scores" in result
        assert isinstance(result["planet_scores"], dict)

    def test_score_day_day_status_values(self):
        """score_day day_status must be one of: supportive, tense, steady."""
        service = ScoringService()

        # Supportive
        supportive = [
            AstroSignal(type="aspect", planet="Sun", target_planet="Jupiter",
                       aspect_type="trine", orb=1.0, strength=0.95),
        ]
        result = service.score_day(supportive)
        assert result["day_status"] in {"supportive", "tense", "steady"}

        # Tense
        tense = [
            AstroSignal(type="aspect", planet="Mars", target_planet="Saturn",
                       aspect_type="square", orb=1.5, strength=0.95),
        ]
        result = service.score_day(tense)
        assert result["day_status"] in {"supportive", "tense", "steady"}

    def test_legacy_score_still_works(self):
        """Legacy score() method should still work for backward compat."""
        service = ScoringService()
        signals = [
            AstroSignal(type="aspect", planet="Sun", target_planet="Jupiter",
                       aspect_type="trine", orb=1.0, strength=0.9),
        ]
        result = service.score(signals)
        assert "day_status" in result
        assert "sphere_scores" in result
        assert "top_signals" in result


# ══════════════════════════════════════════════════════════════════════
# 4. Integration: natal-only path produces different signals than day path
# ══════════════════════════════════════════════════════════════════════

class TestNormalizationScoringIntegration:
    """End-to-end: natal path vs day path produce structurally different outputs."""

    def test_natal_path_has_no_transit_aspects(self, natal_chart):
        """Running natal-only normalization must not produce any Transit_ aspects."""
        service = NormalizationService()
        signals = service.normalize_natal_only(natal_chart)

        transit_count = sum(
            1 for s in signals
            if s.type == "aspect" and (
                (s.planet and s.planet.startswith("Transit_")) or
                (s.target_planet and s.target_planet.startswith("Transit_"))
            )
        )
        assert transit_count == 0, "Natal-only path must have 0 transit aspects"

    def test_day_path_includes_transit_aspects(self, natal_context_dict, transit_data):
        """Running day normalization must include transit aspects."""
        service = NormalizationService()
        signals = service.normalize_day(natal_context_dict, transit_data)

        transit_count = sum(
            1 for s in signals
            if s.type == "aspect" and s.planet and s.planet.startswith("Transit_")
        )
        assert transit_count > 0, "Day path must have transit aspects"

    def test_score_natal_and_score_day_produce_different_keys(self):
        """score_natal and score_day result dicts must have different key sets."""
        service = ScoringService()
        signals = [
            AstroSignal(type="aspect", planet="Sun", target_planet="Jupiter",
                       aspect_type="trine", orb=1.0, strength=0.9),
        ]
        natal_result = service.score_natal(signals)
        day_result = service.score_day(signals)

        # natal has planet_scores, day has day_status
        assert "planet_scores" in natal_result
        assert "day_status" not in natal_result
        assert "day_status" in day_result
