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
