# ############################################################################
# AI_HEADER: MODULE_GEO_SCHEMA
# ROLE: Geo schemas — autocomplete suggestions and timezone.
# DEPENDENCIES: pydantic
# GRACE_ANCHORS: [GEO_SCHEMAS]
# ############################################################################

# START_MODULE_CONTRACT: M-GEO-SCHEMA
# purpose: Define GeoSuggestionOut and GeoTimezoneOut Pydantic schemas.
# owns:
#   - apps/api/app/schemas/geo.py
# inputs:
#   - none (type definitions)
# outputs:
#   - GeoSuggestionOut, GeoTimezoneOut
# dependencies:
#   - pydantic.BaseModel
# side_effects:
#   - none (type-only module)
# END_MODULE_CONTRACT: M-GEO-SCHEMA

# START_MODULE_MAP: M-GEO-SCHEMA
# public_entrypoints:
#   - GeoSuggestionOut
#   - GeoTimezoneOut
# semantic_blocks:
#   - GEO_SCHEMAS: Pydantic models for Geo endpoints
# END_MODULE_MAP: M-GEO-SCHEMA

from pydantic import BaseModel
from typing import Optional


class GeoSuggestionOut(BaseModel):
    """
    # PURPOSE: Describe a GeoNames autocomplete suggestion.
    # INPUT: geoname identifiers and location details.
    # OUTPUT: Serializable suggestion data.
    # CONTEXT: Returned by /api/geo/autocomplete.
    """

    id: str
    name: str
    admin1: Optional[str]
    country: Optional[str]
    lat: float
    lon: float
    label: str
    timezone_id: Optional[str] = None


class GeoTimezoneOut(BaseModel):
    """
    # PURPOSE: Describe GeoNames timezone response.
    # INPUT: timezone identifiers and offsets.
    # OUTPUT: Serializable timezone data.
    # CONTEXT: Returned by /api/geo/timezone.
    """

    timezone_id: Optional[str]
    gmt_offset: Optional[float]
    dst_offset: Optional[float]
    raw_offset: Optional[float]
