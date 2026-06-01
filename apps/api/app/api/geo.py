from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas.geo import GeoSuggestionOut, GeoTimezoneOut
from app.services.geonames import search_geonames, get_timezone, GeoNamesError

router = APIRouter(prefix="/api")


@router.get("/geo/autocomplete", response_model=List[GeoSuggestionOut])
def geo_autocomplete(q: str, limit: int = 8):
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


@router.get("/geo/timezone", response_model=GeoTimezoneOut)
def geo_timezone(lat: float, lon: float):
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
