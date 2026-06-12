# ############################################################################
# AI_HEADER: MODULE_API_GEO
# ROLE: GeoNames autocomplete and timezone endpoints
# DEPENDENCIES: fastapi, app.services.geonames
# GRACE_ANCHORS: [GEO_AUTOCOMPLETE_ENDPOINT, GEO_TIMEZONE_ENDPOINT]
# ############################################################################

# START_MODULE_CONTRACT: M-API-GEO
# purpose: Location autocomplete and timezone lookup via GeoNames.
# owns:
#   - apps/api/app/api/geo.py
# inputs:
#   - q: str (autocomplete query)
#   - lat, lon: float (timezone lookup)
# outputs:
#   - List[GeoSuggestionOut] or GeoTimezoneOut
# dependencies:
#   - M-GEONAMES (search_geonames, get_timezone)
# side_effects:
#   - HTTP requests to GeoNames API
# failure_policy:
#   - GeoNamesError → 400
# non_goals:
#   - no DB writes
# END_MODULE_CONTRACT: M-API-GEO

# START_MODULE_MAP: M-API-GEO
# public_entrypoints:
#   - geo_autocomplete
#   - geo_timezone
# semantic_blocks:
#   - GEO_AUTOCOMPLETE_ENDPOINT: GET /api/geo/autocomplete
#   - GEO_TIMEZONE_ENDPOINT: GET /api/geo/timezone
# END_MODULE_MAP: M-API-GEO

from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas.geo import GeoSuggestionOut, GeoTimezoneOut
from app.services.geonames import search_geonames, get_timezone, GeoNamesError

router = APIRouter(prefix="/api")


# START_BLOCK: GEO_AUTOCOMPLETE_ENDPOINT
@router.get("/geo/autocomplete", response_model=List[GeoSuggestionOut])
def geo_autocomplete(q: str, limit: int = 8):
    # START_FUNCTION_CONTRACT: F-M-API-GEO.geo_autocomplete
    # purpose: Return GeoNames suggestions for location autocomplete.
    # inputs: q (str), limit (int, default 8)
    # returns: List[GeoSuggestionOut] with name, admin1, country, lat, lon
    # side_effects: makes HTTP request to GeoNames API
    # emitted_logs: none
    # error_behavior: GeoNamesError → HTTPException 400
    # END_FUNCTION_CONTRACT: F-M-API-GEO.geo_autocomplete
    """
    # PURPOSE: Return GeoNames suggestions for location autocomplete.
    # INPUT: q (query), limit.
    # OUTPUT: List[GeoSuggestionOut].
    # CONTEXT: Used by the frontend location picker.
    """

    try:
        return search_geonames(q, limit=limit)
    except GeoNamesError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# END_BLOCK: GEO_AUTOCOMPLETE_ENDPOINT

# START_BLOCK: GEO_TIMEZONE_ENDPOINT
@router.get("/geo/timezone", response_model=GeoTimezoneOut)
def geo_timezone(lat: float, lon: float):
    # START_FUNCTION_CONTRACT: F-M-API-GEO.geo_timezone
    # purpose: Return GeoNames timezone for coordinates.
    # inputs: lat (float), lon (float)
    # returns: GeoTimezoneOut with timezone_id, gmt_offset, dst_offset, raw_offset
    # side_effects: makes HTTP request to GeoNames API
    # emitted_logs: none
    # error_behavior: GeoNamesError → HTTPException 400
    # END_FUNCTION_CONTRACT: F-M-API-GEO.geo_timezone
    """
    # PURPOSE: Return GeoNames timezone for coordinates.
    # INPUT: lat, lon.
    # OUTPUT: GeoTimezoneOut.
    # CONTEXT: Used by the frontend location picker.
    """

    try:
        return get_timezone(lat, lon)
    except GeoNamesError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
# END_BLOCK: GEO_TIMEZONE_ENDPOINT
