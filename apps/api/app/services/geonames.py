# ############################################################################
# AI_HEADER: MODULE_GEONAMES
# ROLE: GeoNames autocomplete integration.
# DEPENDENCIES: standard library (json, urllib, copy, functools.lru_cache).
# GRACE_ANCHORS: [GEONAMES_FETCH, GEONAMES_PARSE, GEONAMES_CACHE]
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
#   - search uses style=FULL; an inline item.timezone.timeZoneId is used as
#     timezone_id directly, otherwise _fetch_timezone (timezoneJSON) is the
#     per-item fallback
#   - search results are memoized by a bounded lru_cache (256) keyed by
#     (stripped query, limit, username): after a COMPLETED successful miss,
#     subsequent same-key calls reuse the cache (concurrent cold misses may
#     still duplicate the upstream call — lru_cache is thread-safe but NOT
#     a single-flight); exceptions are never cached, callers get defensive
#     deep copies
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
#   - GEONAMES_CACHE: bounded in-process search dedup (lru_cache 256 keyed by
#     stripped query + limit + username; exceptions never cached; defensive
#     deep copies out; process restart clears)
# END_MODULE_MAP: M-GEONAMES

import copy
import json
import os
import urllib.parse
import urllib.request
from functools import lru_cache
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
        "style": "FULL",
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

        # style=FULL carries an inline timezone for most populated places;
        # only items without it cost a separate timezoneJSON round-trip.
        tz_inline = item.get("timezone")
        if isinstance(tz_inline, dict) and tz_inline.get("timeZoneId"):
            tz_id = tz_inline["timeZoneId"]
        else:
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
    # returns: List of dicts with id, name, lat, lon, timezone_id, label —
    #   a defensive deep copy on EVERY call (callers may mutate freely).
    # side_effects: makes HTTP requests to GeoNames API (deduplicated: see
    #   _search_geonames_cached)
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

    # Bounded in-process dedup: identical autocomplete bursts (same stripped
    # query, same limit, same username) cost ONE upstream search. Cold
    # process and every first unique query still call GeoNames for real;
    # exceptions are never cached (lru_cache re-raises on every miss), so a
    # cold-miss provider failure stays fail-closed. GeoNames data is
    # effectively static and a process restart clears the cache.
    return copy.deepcopy(
        _search_geonames_cached(query.strip(), limit, _get_username())
    )


@lru_cache(maxsize=256)
def _search_geonames_cached(stripped_query: str, limit: int, username: str) -> List[dict]:
    # START_FUNCTION_CONTRACT: F-M-GEONAMES._search_geonames_cached
    # purpose: Memoized wrapper over _search_geonames_uncached keyed by
    #   (stripped query, limit, username). username is part of the key so a
    #   credential change never crosses cached entries.
    # inputs: stripped_query, limit, username (key material only — the
    #   upstream fetch reads the env username itself).
    # returns: the cached result list (callers receive deep copies only).
    # side_effects: upstream searches only on cache misses (one completed
#   successful miss per key is then reused; concurrent cold misses may
#   duplicate the upstream call — no single-flight guarantee).
    # emitted_logs: none.
    # error_behavior: GeoNamesError propagates and is NEVER cached — the
    #   next identical call retries the provider for real.
    # END_FUNCTION_CONTRACT: F-M-GEONAMES._search_geonames_cached
    return _search_geonames_uncached(stripped_query, limit)


def _search_geonames_uncached(query: str, limit: int) -> List[dict]:
    # START_FUNCTION_CONTRACT: F-M-GEONAMES._search_geonames_uncached
    # purpose: Real GeoNames autocomplete lookup: startswith search, then
    #   full-text, then compact (space/dash-stripped) variants.
    # inputs: stripped query, limit.
    # returns: suggestion dicts (may be empty).
    # side_effects: 1-4 HTTP requests to GeoNames.
    # emitted_logs: none.
    # error_behavior: GeoNamesError on API failure.
    # END_FUNCTION_CONTRACT: F-M-GEONAMES._search_geonames_uncached
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
