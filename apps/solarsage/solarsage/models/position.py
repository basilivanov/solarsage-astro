# AI_HEADER
# module: M-SOLARSAGE-POSITION-MODELS
# wave: W-SOLARSAGE-SVC
# purpose: Position data models

from dataclasses import dataclass


@dataclass
class PlanetPosition:
    """Planet position data."""
    name: str
    longitude: float
    latitude: float
    speed: float
    sign: str
