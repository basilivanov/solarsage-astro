# ############################################################################
# AI_HEADER: MODULE_SERVICES_SYNASTRY
# ROLE: Sidecar synastry calculation service
# DEPENDENCIES: solarsage.utils.ephemeris, solarsage.schemas.synastry
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-SERVICE-SYNASTRY
# purpose: Compute partner chart positions, houses, and cross-aspects for synastry.
# owns:
#   - apps/solarsage/solarsage/services/synastry.py
# inputs: SynastryRequest
# outputs: SynastryResponse
# dependencies: solarsage.utils.ephemeris, solarsage.schemas.synastry
# side_effects: Ephemeris calculations
# emitted_logs: none
# invariants:
#   - Unknown birth time sets houses/ASC to None and flags precision as approximate
# failure_policy: Exception on invalid date/time/coordinates
# END_MODULE_CONTRACT: M-SIDECAR-SERVICE-SYNASTRY

# START_MODULE_MAP: M-SIDECAR-SERVICE-SYNASTRY
# public_entrypoints:
#   - SynastryService.calculate_synastry
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SIDECAR-SERVICE-SYNASTRY

from __future__ import annotations

from typing import Any
from ..schemas.synastry import CrossAspect, SynastryRequest, SynastryResponse
from ..services.natal import NatalService

ASPECT_LIMITS = [
    ("conjunction", 0.0, 8.0),
    ("sextile", 60.0, 6.0),
    ("square", 90.0, 7.0),
    ("trine", 120.0, 8.0),
    ("quincunx", 150.0, 5.0),
    ("opposition", 180.0, 8.0),
]


class SynastryService:
    """Sidecar synastry calculation service."""

    def __init__(self) -> None:
        self.natal_service = NatalService()

    def calculate_synastry(self, req: SynastryRequest) -> SynastryResponse:
        is_approximate = req.partner_birth_time_precision in ("approximate", "unknown")
        req_hs = (req.house_system or "PLACIDUS").upper()

        # 1. Owner chart
        owner_chart = self.natal_service.calculate_natal_chart(
            date_str=req.owner_birth_date,
            time_str=req.owner_birth_time,
            tz_str=req.owner_birth_tz,
            latitude=req.owner_birth_lat,
            longitude=req.owner_birth_lon,
            house_system=req_hs,
        )

        owner_planets = [
            {
                "name": p["name"],
                "longitude": p["longitude"],
                "latitude": p.get("latitude", 0.0),
                "sign": p["sign"],
                "retrograde": p.get("retrograde", False),
            }
            for p in owner_chart.positions
        ]

        owner_houses = [
            {"number": h["number"], "cusp": h["cusp"], "sign": h["sign"]}
            for h in owner_chart.houses
        ]

        # 2. Partner chart
        partner_time = req.partner_birth_time or "12:00"
        partner_tz = req.partner_birth_tz or "UTC"
        partner_lat = req.partner_birth_lat or 0.0
        partner_lon = req.partner_birth_lon or 0.0

        partner_chart = self.natal_service.calculate_natal_chart(
            date_str=req.partner_birth_date,
            time_str=partner_time,
            tz_str=partner_tz,
            latitude=partner_lat,
            longitude=partner_lon,
            house_system=req_hs,
        )

        partner_planets = [
            {
                "name": p["name"],
                "longitude": p["longitude"],
                "latitude": p.get("latitude", 0.0),
                "sign": p["sign"],
                "retrograde": p.get("retrograde", False),
            }
            for p in partner_chart.positions
        ]

        if is_approximate:
            partner_houses = None
            partner_special_points = None
        else:
            partner_houses = [
                {"number": h["number"], "cusp": h["cusp"], "sign": h["sign"]}
                for h in partner_chart.houses
            ]
            partner_special_points = [
                {"name": sp["name"], "longitude": sp["longitude"], "sign": sp["sign"]}
                for sp in partner_chart.special_points
            ]

        # 3. Calculate cross-aspects
        cross_aspects: list[CrossAspect] = []
        for op in owner_planets:
            for pp in partner_planets:
                diff = abs(op["longitude"] - pp["longitude"]) % 360.0
                angle = min(diff, 360.0 - diff)

                for asp_name, target_angle, max_orb in ASPECT_LIMITS:
                    orb = abs(angle - target_angle)
                    if orb <= max_orb:
                        cross_aspects.append(
                            CrossAspect(
                                owner_planet=op["name"],
                                partner_planet=pp["name"],
                                aspect_type=asp_name,
                                orb_degrees=round(orb, 2),
                                applying=None,
                            )
                        )
                        break

        precision_flags = {
            "houses_available": not is_approximate,
            "asc_available": not is_approximate,
            "moon_precision": "approximate" if is_approximate else "exact",
            "report_precision": "approximate" if is_approximate else "exact",
        }

        return SynastryResponse(
            owner_planets=owner_planets,
            partner_planets=partner_planets,
            owner_houses=owner_houses,
            partner_houses=partner_houses,
            partner_special_points=partner_special_points,
            cross_aspects=cross_aspects,
            precision_flags=precision_flags,
            owner_house_system=owner_chart.house_system,
            partner_house_system=partner_chart.house_system,
            house_system=owner_chart.house_system,
        )
