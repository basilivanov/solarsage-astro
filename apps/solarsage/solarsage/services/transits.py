# AI_HEADER
# module: M-SOLARSAGE-TRANSITS-SERVICE
# wave: W-SOLARSAGE-SVC
# purpose: Transits calculation service

from datetime import datetime, date
from typing import List, Dict, Any

from ..models.chart import Transit
from ..utils.ephemeris import calculate_julian_day, calculate_positions


class TransitsService:
    """Transits calculation service."""

    # Major aspects with orbs
    ASPECTS = {
        'conjunction': (0, 8),
        'opposition': (180, 8),
        'trine': (120, 8),
        'square': (90, 8),
        'sextile': (60, 6),
    }

    def calculate_transits(
        self,
        date_str: str,
        time_str: str,
        tz_str: str,
        natal_positions: List[Dict[str, Any]],
    ) -> List[Transit]:
        """
        Calculate transits for target date.

        W-SOLARSAGE-SVC: Extracted from monolithic collector.

        Args:
            date_str: Target date (YYYY-MM-DD)
            time_str: Target time (HH:MM)
            tz_str: Timezone
            natal_positions: Natal planet positions

        Returns:
            List of significant transits
        """
        # Calculate Julian Day for target date
        jd = calculate_julian_day(date_str, time_str, tz_str)

        # Calculate current positions
        current_positions = calculate_positions(jd)

        # Convert natal positions to dict for lookup
        natal_dict = {p['name']: p for p in natal_positions}

        # Find significant transits
        transits = []
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        for current_planet in current_positions:
            current_name = current_planet['name']
            current_lon = current_planet['longitude']

            for natal_name, natal_planet in natal_dict.items():
                natal_lon = natal_planet['longitude']

                # Check each aspect
                for aspect_name, (aspect_angle, orb) in self.ASPECTS.items():
                    angle_diff = abs(current_lon - natal_lon)

                    # Normalize to 0-180 range
                    if angle_diff > 180:
                        angle_diff = 360 - angle_diff

                    # Check if within orb
                    aspect_orb = abs(angle_diff - aspect_angle)

                    if aspect_orb <= orb:
                        transits.append(Transit(
                            planet=current_name,
                            aspect=aspect_name,
                            natal_planet=natal_name,
                            orb=aspect_orb,
                            date=target_date,
                        ))

        return transits
