# ############################################################################
# AI_HEADER: MODULE_NORMALIZATION_SERVICE
# ROLE: Normalization layer (raw → AstroSignal[])
# DEPENDENCIES: app.schemas.normalization, app.services.astro_utils
# GRACE_ANCHORS: [NORMALIZE_NATAL, NORMALIZE_DAY, NORMALIZE_LEGACY]
# WAVE: W-4.1, W-NATAL-FULL
# ############################################################################

# START_MODULE_CONTRACT: M-NORMALIZATION-SERVICE
# purpose: Convert raw astrological data into AstroSignal[] for scoring.
#   W-NATAL-FULL: split into natal-only and day (natal + transits) paths.
# owns:
#   - apps/api/app/services/normalization_service.py
# inputs:
#   - natal dict with planets, houses, special_points
#   - transits dict with planets
# outputs:
#   - list[AstroSignal]
# dependencies:
#   - M-ASTRO-UTILS (find_house)
#   - M-CONTRACTS.normalization (AstroSignal, AspectType)
# side_effects:
#   - none (pure computation)
# invariants:
#   - normalize_natal_only never includes transit signals
#   - normalize_day includes both natal and transit signals
# failure_policy:
#   - returns empty list on empty input
# END_MODULE_CONTRACT: M-NORMALIZATION-SERVICE

# START_MODULE_MAP: M-NORMALIZATION-SERVICE
# public_entrypoints:
#   - NormalizationService.normalize_natal_only
#   - NormalizationService.normalize_day
#   - NormalizationService.normalize
# semantic_blocks:
#   - NORMALIZE_NATAL: natal-only signal extraction
#   - NORMALIZE_DAY: natal + transit signal extraction
#   - NORMALIZE_LEGACY: backward-compat full normalization
# END_MODULE_MAP: M-NORMALIZATION-SERVICE

from app.services.astro_utils import find_house
from app.schemas.normalization import AstroSignal, AspectType

ASPECT_ANGLES = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}

ASPECT_ORBS = {
    "conjunction": 8.0,
    "sextile": 6.0,
    "square": 7.0,
    "trine": 8.0,
    "opposition": 8.0,
}


class NormalizationService:
    """Normalization layer for astrological data.

    W-NATAL-FULL: split into natal-only and day (natal + transits) paths.
    """

    # ── Natal-only path (no transits) ─────────────────────────────

    def normalize_natal_only(self, natal: dict) -> list[AstroSignal]:
        # START_FUNCTION_CONTRACT: F-M-NORMALIZATION-SERVICE.normalize_natal_only
        # purpose: Normalize natal-only chart data (no transit signals).
        # inputs: natal dict with planets, houses, special_points
        # returns: list[AstroSignal] with planet_in_house, planet_in_sign, aspect signals
        # side_effects: none (pure computation)
        # emitted_logs: none
        # error_behavior: returns empty list on empty input
        # END_FUNCTION_CONTRACT: F-M-NORMALIZATION-SERVICE.normalize_natal_only
        """Normalize natal chart data only — no transits.

        Used by NatalContextService to build persistent natal context.
        Must NOT include any transit signals.
        """
        signals = []

        # 1. Natal planets in houses
        signals.extend(self._planets_in_houses(natal))

        # 2. Natal planets in signs
        signals.extend(self._planets_in_signs(natal))

        # 3. Natal aspects (planet-to-planet)
        signals.extend(self._natal_aspects(natal))

        # NO transit aspects — natal-only!

        return signals

    # ── Day path (natal context + transits) ────────────────────────

    def normalize_day(
        self,
        natal_context: dict,
        transits: dict,
    ) -> list[AstroSignal]:
        # START_FUNCTION_CONTRACT: F-M-NORMALIZATION-SERVICE.normalize_day
        # purpose: Normalize day signals from cached natal context + fresh transits.
        # inputs: natal_context (dict), transits (dict)
        # returns: list[AstroSignal] with natal and transit signals
        # side_effects: none (pure computation)
        # emitted_logs: none
        # error_behavior: returns empty list on empty input
        # END_FUNCTION_CONTRACT: F-M-NORMALIZATION-SERVICE.normalize_day
        """Normalize day signals from cached natal context + fresh transits.

        W-NATAL-FULL: This replaces the old normalize(natal, transits) for day use.
        Natal context is already normalized; we only add transit signals.
        """
        signals = []

        # 1. Natal signals from context (planets in houses, signs, natal aspects)
        #    These are already computed in NatalContextData; rebuild from raw chart
        #    so we get proper AstroSignal objects for scoring.
        natal_signals = natal_context.get("natal_signals", [])
        if natal_signals:
            # If pre-computed signals are available, use them
            for s_data in natal_signals:
                signals.append(AstroSignal(
                    type=s_data.get("type"),
                    planet=s_data.get("planet"),
                    house=s_data.get("house"),
                    sign=s_data.get("sign"),
                    target_planet=s_data.get("target_planet"),
                    aspect_type=s_data.get("aspect_type"),
                    orb=s_data.get("orb"),
                    strength=s_data.get("strength", 1.0),
                ))
        else:
            # Fallback: rebuild from raw chart if signals not available
            signals.extend(self._planets_in_houses(natal_context))
            signals.extend(self._planets_in_signs(natal_context))
            signals.extend(self._natal_aspects(natal_context))

        # 2. Transit aspects (transit planet to natal planet)
        natal_planets = natal_context.get("planets", natal_context.get("planets", []))
        transit_planets = transits.get("planets", [])
        if transit_planets and natal_planets:
            signals.extend(self._transit_aspects_from_planets(transit_planets, natal_planets))

        return signals

    # ── Legacy path (backward compat) ─────────────────────────────

    def normalize(
        self,
        natal: dict,
        transits: dict,
    ) -> list[AstroSignal]:
        # START_FUNCTION_CONTRACT: F-M-NORMALIZATION-SERVICE.normalize
        # purpose: Legacy normalization — normalize raw natal + transits data.
        # inputs: natal dict, transits dict
        # returns: list[AstroSignal]
        # side_effects: none (pure computation)
        # emitted_logs: none
        # error_behavior: returns empty list on empty input
        # END_FUNCTION_CONTRACT: F-M-NORMALIZATION-SERVICE.normalize
        """
        Normalize raw data into AstroSignal[].

        Args:
            natal: {"planets": [...], "houses": [...], "special_points": [...]}
            transits: {"planets": [...]}

        Returns:
            List of AstroSignal
        """
        signals = []

        # 1. Natal planets in houses
        signals.extend(self._planets_in_houses(natal))

        # 2. Natal planets in signs
        signals.extend(self._planets_in_signs(natal))

        # 3. Natal aspects (planet-to-planet)
        signals.extend(self._natal_aspects(natal))

        # 4. Transit aspects (transit planet to natal planet)
        signals.extend(self._transit_aspects(transits, natal))

        return signals

    def _planets_in_houses(self, natal: dict) -> list[AstroSignal]:
        """Generate planet_in_house signals."""
        signals = []

        planets = natal["planets"]
        houses = natal["houses"]

        for planet in planets:
            # Find which house the planet is in
            planet_lon = planet["longitude"]
            house_num = find_house(planet_lon, houses) or 1

            signals.append(AstroSignal(
                type="planet_in_house",
                planet=planet["name"],
                house=house_num,
                strength=1.0,  # W-4.2: real strength from scoring
            ))

        return signals

    def _planets_in_signs(self, natal: dict) -> list[AstroSignal]:
        """Generate planet_in_sign signals."""
        signals = []

        for planet in natal["planets"]:
            signals.append(AstroSignal(
                type="planet_in_sign",
                planet=planet["name"],
                sign=planet["sign"],
                strength=1.0,  # W-4.2: real strength from scoring
            ))

        return signals

    def _natal_aspects(self, natal: dict) -> list[AstroSignal]:
        """Generate natal aspect signals (planet-to-planet)."""
        signals = []
        planets = natal["planets"]

        for i, p1 in enumerate(planets):
            for p2 in planets[i+1:]:
                aspect = self._calculate_aspect(p1["longitude"], p2["longitude"])
                if aspect:
                    aspect_type, orb = aspect
                    signals.append(AstroSignal(
                        type="aspect",
                        planet=p1["name"],
                        target_planet=p2["name"],
                        aspect_type=aspect_type,
                        orb=orb,
                        strength=self._aspect_strength(orb, aspect_type),
                    ))

        return signals

    def _transit_aspects(self, transits: dict, natal: dict) -> list[AstroSignal]:
        """Generate transit aspect signals (transit planet to natal planet)."""
        signals = []

        transit_planets = transits["planets"]
        natal_planets = natal["planets"]

        for t_planet in transit_planets:
            for n_planet in natal_planets:
                aspect = self._calculate_aspect(t_planet["longitude"], n_planet["longitude"])
                if aspect:
                    aspect_type, orb = aspect
                    signals.append(AstroSignal(
                        type="aspect",
                        planet=f"Transit_{t_planet['name']}",
                        target_planet=n_planet["name"],
                        aspect_type=aspect_type,
                        orb=orb,
                        strength=self._aspect_strength(orb, aspect_type),
                    ))

        return signals

    def _transit_aspects_from_planets(
        self, transit_planets: list[dict], natal_planets: list[dict]
    ) -> list[AstroSignal]:
        """Generate transit aspect signals from pre-separated planet lists.

        Used by normalize_day() when natal context provides planets separately.
        """
        signals = []

        for t_planet in transit_planets:
            for n_planet in natal_planets:
                aspect = self._calculate_aspect(t_planet["longitude"], n_planet["longitude"])
                if aspect:
                    aspect_type, orb = aspect
                    signals.append(AstroSignal(
                        type="aspect",
                        planet=f"Transit_{t_planet['name']}",
                        target_planet=n_planet["name"],
                        aspect_type=aspect_type,
                        orb=orb,
                        strength=self._aspect_strength(orb, aspect_type),
                    ))

        return signals

    @staticmethod
    def _calculate_aspect(lon1: float, lon2: float) -> tuple[AspectType, float] | None:
        """
        Calculate aspect between two longitudes.

        Returns:
            (aspect_type, orb) or None if no aspect within orb
        """
        # Calculate angular distance
        diff = abs(lon1 - lon2)
        if diff > 180:
            diff = 360 - diff

        # Check each aspect type
        for aspect_name, angle in ASPECT_ANGLES.items():
            orb = abs(diff - angle)
            max_orb = ASPECT_ORBS[aspect_name]

            if orb <= max_orb:
                return (aspect_name, orb)

        return None

    def _aspect_strength(self, orb: float, aspect_type: AspectType) -> float:
        """
        Calculate aspect strength based on orb.

        Strength = 1.0 - (orb / max_orb)
        """
        max_orb = ASPECT_ORBS[aspect_type]
        return max(0.0, 1.0 - (orb / max_orb))
