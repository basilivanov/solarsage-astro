# ############################################################################
# AI_HEADER: MODULE_GEONAMES
# ROLE: GeoNames autocomplete integration.
# DEPENDENCIES: standard library (json, urllib).
# GRACE_ANCHORS: [GEONAMES_FETCH, GEONAMES_PARSE]
# ############################################################################

# START_MODULE_CONTRACT: M-GEONAMES
# purpose: GeoNames API integration for location autocomplete and timezone lookup.
# owns:
#   - apps/api/app/services/geonames.py
# inputs:
#   - query: str (location name)
#   - lat, lon: float (coordinates)
# outputs:
#   - List[dict] of location suggestions
#   - dict with timezone data
# dependencies:
#   - standard library: json, urllib, os
# side_effects:
#   - HTTP requests to GeoNames API
# invariants:
#   - GEONAMES_USERNAME must be set in environment
#   - retries with compact query if no results
# failure_policy:
#   - GeoNamesError on API failure
#   - returns empty list if no results
# END_MODULE_CONTRACT: M-GEONAMES

# START_MODULE_MAP: M-GEONAMES
# public_entrypoints:
#   - search_geonames
#   - get_timezone
# semantic_blocks:
#   - GEONAMES_FETCH: HTTP requests to GeoNames
#   - GEONAMES_PARSE: parse GeoNames response JSON
# END_MODULE_MAP: M-GEONAMES

import json
import os
import urllib.parse
import urllib.request
from typing import List, Optional


class GeoNamesError(RuntimeError):
    pass


def _get_username() -> str:
    username = os.getenv("GEONAMES_USERNAME", "").strip()
    if not username:
        raise GeoNamesError("GEONAMES_USERNAME is not set.")
    return username


def _fetch_timezone(lat: float, lon: float) -> Optional[str]:
    params = {
        "lat": str(lat),
        "lng": str(lon),
        "username": _get_username(),
    }
    url = "https://secure.geonames.org/timezoneJSON?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))
        if isinstance(data, dict) and data.get("timezoneId"):
            return data["timezoneId"]
    except Exception:
        pass
    return None


def _fetch_geonames(query: str, limit: int, mode: str) -> List[dict]:
    params = {
        "maxRows": str(limit),
        "featureClass": "P",
        "style": "MEDIUM",
        "lang": "ru",
        "username": _get_username(),
    }
    if mode == "startswith":
        params["name_startsWith"] = query
    else:
        params["q"] = query

    url = "https://secure.geonames.org/searchJSON?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = response.read().decode("utf-8")
    except Exception as exc:
        raise GeoNamesError("GeoNames request failed.") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise GeoNamesError("GeoNames JSON parse failed.") from exc

    if isinstance(data, dict) and data.get("status"):
        message = data["status"].get("message", "GeoNames error.")
        raise GeoNamesError(message)

    results: List[dict] = []
    for item in data.get("geonames", []):
        name = item.get("name", "")
        admin1 = item.get("adminName1")
        country = item.get("countryName")
        label_parts = [part for part in [name, admin1, country] if part]
        label = ", ".join(label_parts) if label_parts else name

        lat_raw = item.get("lat")
        lon_raw = item.get("lng")
        try:
            lat = float(lat_raw) if lat_raw is not None else None
            lon = float(lon_raw) if lon_raw is not None else None
        except (TypeError, ValueError):
            lat = None
            lon = None

        if lat is None or lon is None:
            continue

        tz_id = _fetch_timezone(lat, lon)

        results.append(
            {
                "id": str(item.get("geonameId", "")),
                "name": name,
                "admin1": admin1,
                "country": country,
                "lat": lat,
                "lon": lon,
                "label": label,
                "timezone_id": tz_id,
            }
        )

    return results


def search_geonames(query: str, limit: int = 8) -> List[dict]:
    # START_FUNCTION_CONTRACT: F-M-GEONAMES.search_geonames
    # purpose: Fetch GeoNames autocomplete suggestions by query.
    # inputs: query (str), limit (int, default 8)
    # returns: List of dicts with id, name, lat, lon, timezone_id, label
    # side_effects: makes HTTP requests to GeoNames API
    # emitted_logs: none
    # error_behavior: returns empty list if query too short (<2 chars); raises GeoNamesError on API failure
    # END_FUNCTION_CONTRACT: F-M-GEONAMES.search_geonames
    """
    # PURPOSE: Fetch GeoNames autocomplete suggestions.
    # INPUT: query string, limit.
    # OUTPUT: List of suggestion dicts.
    # CONTEXT: Used by /api/geo/autocomplete.
    """

    if not query or len(query.strip()) < 2:
        return []

    query = query.strip()

    results = _fetch_geonames(query, limit, "startswith")
    if results:
        return results

    results = _fetch_geonames(query, limit, "full")
    if results:
        return results

    compact = query.replace(" ", "").replace("-", "")
    if compact != query:
        results = _fetch_geonames(compact, limit, "startswith")
        if results:
            return results
        return _fetch_geonames(compact, limit, "full")

    return results


def get_timezone(lat: float, lon: float) -> dict:
    # START_FUNCTION_CONTRACT: F-M-GEONAMES.get_timezone
    # purpose: Fetch timezone data for a coordinate pair from GeoNames.
    # inputs: lat (float), lon (float)
    # returns: dict with timezone_id, gmt_offset, dst_offset, raw_offset
    # side_effects: makes HTTP request to GeoNames API
    # emitted_logs: none
    # error_behavior: raises GeoNamesError on API or JSON parse failure
    # END_FUNCTION_CONTRACT: F-M-GEONAMES.get_timezone
    """
    # PURPOSE: Fetch timezone data for a coordinate pair.
    # INPUT: latitude, longitude.
    # OUTPUT: Dict with timezone details.
    # CONTEXT: Used by /api/geo/timezone.
    """

    params = {
        "lat": str(lat),
        "lng": str(lon),
        "username": _get_username(),
    }
    url = "https://secure.geonames.org/timezoneJSON?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = response.read().decode("utf-8")
    except Exception as exc:
        raise GeoNamesError("GeoNames timezone request failed.") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise GeoNamesError("GeoNames timezone JSON parse failed.") from exc

    if isinstance(data, dict) and data.get("status"):
        message = data["status"].get("message", "GeoNames timezone error.")
        raise GeoNamesError(message)

    return {
        "timezone_id": data.get("timezoneId"),
        "gmt_offset": data.get("gmtOffset"),
        "dst_offset": data.get("dstOffset"),
        "raw_offset": data.get("rawOffset"),
    }
