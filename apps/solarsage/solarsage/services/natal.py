
# ############################################################################
# AI_HEADER: MODULE_SERVICES_NATAL
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/solarsage/services/natal.py
# owns:
#   - apps/solarsage/solarsage/services/natal.py
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
# module: M-SOLARSAGE-NATAL-SERVICE
# wave: W-SOLARSAGE-SVC
# purpose: Natal chart service

from datetime import datetime
from typing import List, Dict, Any

from ..models.chart import NatalChart
from ..utils.ephemeris import calculate_julian_day, calculate_positions, calculate_houses_cusps


class NatalService:
    """Natal chart calculation service."""

    def calculate_natal_chart(
        self,
        date_str: str,
        time_str: str,
        tz_str: str,
        latitude: float,
        longitude: float,
    ) -> NatalChart:
        """
        Calculate natal chart.

        W-SOLARSAGE-SVC: Extracted from monolithic collector.

        Args:
            date_str: Birth date (YYYY-MM-DD)
            time_str: Birth time (HH:MM)
            tz_str: Timezone (e.g., "America/New_York")
            latitude: Birth latitude
            longitude: Birth longitude

        Returns:
            NatalChart with positions, houses, and special points
        """
        # Calculate Julian Day
        jd = calculate_julian_day(date_str, time_str, tz_str)

        # Calculate planetary positions
        positions = calculate_positions(jd)

        # Calculate houses and special points
        houses, special_points, house_system = calculate_houses_cusps(
            jd, latitude, longitude
        )

        # Parse birth datetime for model
        birth_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        return NatalChart(
            birth_datetime=birth_datetime,
            latitude=latitude,
            longitude=longitude,
            positions=positions,
            houses=houses,
            special_points=special_points,
            house_system=house_system,
        )
