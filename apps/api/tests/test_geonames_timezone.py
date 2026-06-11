
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_GEONAMES_TIMEZONE
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for geonames_timezone.py behavior
# owns:
#   - apps/api/tests/test_geonames_timezone.py
# inputs: Endpoint params, request body
# outputs: Parsed response / typed data
# dependencies: local modules
# side_effects: Network calls to API
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

from app.services.geonames import (
    GeoNamesError,
    _fetch_timezone,
    search_geonames,
)


class TestFetchTimezone:
    def test_returns_timezone_id_on_success(self):
        payload = json.dumps(
            {"timezoneId": "Europe/Moscow", "gmtOffset": 3.0, "dstOffset": 3.0}
        ).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("app.services.geonames._get_username", return_value="testuser"):
            with patch("app.services.geonames.urllib.request.urlopen", return_value=mock_resp):
                result = _fetch_timezone(55.75, 37.62)
        assert result == "Europe/Moscow"

    def test_returns_none_on_network_error(self):
        with patch("app.services.geonames._get_username", return_value="testuser"):
            with patch("app.services.geonames.urllib.request.urlopen", side_effect=Exception("timeout")):
                result = _fetch_timezone(55.75, 37.62)
        assert result is None

    def test_returns_none_when_timezoneId_missing(self):
        payload = json.dumps({"gmtOffset": 3.0}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("app.services.geonames._get_username", return_value="testuser"):
            with patch("app.services.geonames.urllib.request.urlopen", return_value=mock_resp):
                result = _fetch_timezone(55.75, 37.62)
        assert result is None


class TestSearchGeoNamesTimezone:
    def test_autocomplete_includes_timezone_id(self):
        search_payload = json.dumps(
            {
                "geonames": [
                    {
                        "geonameId": 524901,
                        "name": "Moscow",
                        "adminName1": "Moscow",
                        "countryName": "Russia",
                        "lat": 55.7558,
                        "lng": 37.6173,
                    },
                ]
            }
        ).encode()
        tz_payload = json.dumps(
            {"timezoneId": "Europe/Moscow", "gmtOffset": 3.0, "dstOffset": 3.0}
        ).encode()

        mock_search_resp = MagicMock()
        mock_search_resp.read.return_value = search_payload
        mock_search_resp.__enter__ = lambda s: s
        mock_search_resp.__exit__ = MagicMock(return_value=False)

        mock_tz_resp = MagicMock()
        mock_tz_resp.read.return_value = tz_payload
        mock_tz_resp.__enter__ = lambda s: s
        mock_tz_resp.__exit__ = MagicMock(return_value=False)

        call_count = [0]

        def mock_urlopen(url, timeout=5):
            call_count[0] += 1
            if "timezoneJSON" in url:
                return mock_tz_resp
            return mock_search_resp

        with patch("app.services.geonames.urllib.request.urlopen", side_effect=mock_urlopen):
            with patch("app.services.geonames._get_username", return_value="testuser"):
                results = search_geonames("Moscow", limit=8)

        assert len(results) == 1
        assert results[0]["timezone_id"] == "Europe/Moscow"
        assert results[0]["name"] == "Moscow"
        assert results[0]["lat"] == 55.7558

    def test_autocomplete_timezone_fallback_to_none(self):
        search_payload = json.dumps(
            {
                "geonames": [
                    {
                        "geonameId": 524901,
                        "name": "Moscow",
                        "lat": 55.7558,
                        "lng": 37.6173,
                    },
                ]
            }
        ).encode()

        mock_search_resp = MagicMock()
        mock_search_resp.read.return_value = search_payload
        mock_search_resp.__enter__ = lambda s: s
        mock_search_resp.__exit__ = MagicMock(return_value=False)

        def mock_urlopen(url, timeout=5):
            if "timezoneJSON" in url:
                raise Exception("tz error")
            return mock_search_resp

        with patch("app.services.geonames.urllib.request.urlopen", side_effect=mock_urlopen):
            with patch("app.services.geonames._get_username", return_value="testuser"):
                results = search_geonames("Moscow", limit=8)

        assert len(results) == 1
        assert results[0]["timezone_id"] is None