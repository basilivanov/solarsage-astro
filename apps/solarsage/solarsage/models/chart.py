
# ############################################################################
# AI_HEADER: MODULE_MODELS_CHART
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Module: chart.py
# owns:
#   - apps/solarsage/solarsage/models/chart.py
# inputs: Function args
# outputs: Return values
# dependencies: local modules
# side_effects: n/a (pure)
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-SOLARSAGE-CHART-MODELS
# wave: W-SOLARSAGE-SVC
# purpose: Chart data models

from dataclasses import dataclass
from datetime import datetime, date
from typing import Dict, List, Any


@dataclass
class NatalChart:
    """Natal chart data."""
    birth_datetime: datetime
    latitude: float
    longitude: float
    positions: List[Dict[str, Any]]
    houses: List[Dict[str, Any]]
    special_points: List[Dict[str, Any]]
    house_system: str


@dataclass
class Transit:
    """Transit data."""
    planet: str
    aspect: str
    natal_planet: str
    orb: float
    date: date
