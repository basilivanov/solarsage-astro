# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_GEONAMES_CACHE — in-process search dedup proofs.
# ROLE: Proves the bounded GeoNames search cache: one upstream call per
#       (query, limit, username) key, defensive copies out, exceptions never
#       cached, and cold-miss provider failure staying fail-closed.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-GEONAMES-CACHE
# purpose: Directed tests for the geonames.py bounded lru_cache dedup.
# owns:
#   - apps/api/tests/test_geonames_cache.py
# inputs: monkeypatched _fetch_geonames (no real network).
# outputs: outbound-call-count, key-separation and mutation-independence
#   assertions.
# dependencies: app.services.geonames.
# side_effects: none (upstream fetch mocked at the module boundary).
# emitted_logs: none.
# invariants:
#   - Identical (query, limit, username) -> at most one outbound fetch.
#   - Exceptions are never cached; the next identical call retries for real.
#   - Cached results cannot be mutated by callers (defensive copies).
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-GEONAMES-CACHE

from __future__ import annotations

import pytest

from app.services import geonames
from app.services.geonames import GeoNamesError

RESULT = [
    {
        "id": "524901",
        "name": "Москва",
        "admin1": "Москва",
        "country": "Россия",
        "lat": 55.75,
        "lon": 37.61,
        "label": "Москва, Москва, Россия",
        "timezone_id": "Europe/Moscow",
    }
]


@pytest.fixture
def outbound(monkeypatch):
    calls: list[tuple] = []

    def fake_fetch(query: str, limit: int, mode: str):
        calls.append((query, limit, mode))
        return [dict(item) for item in RESULT]

    monkeypatch.setattr(geonames, "_fetch_geonames", fake_fetch)
    monkeypatch.setenv("GEONAMES_USERNAME", "cache-test-user")
    return calls


def test_identical_search_uses_single_outbound_call_and_defensive_copies(outbound):
    first = geonames.search_geonames("Москва", limit=8)
    # Stripped-query normalization shares the key: surrounding whitespace
    # must NOT cause a second upstream call.
    second = geonames.search_geonames("  Москва  ", limit=8)

    # One upstream fetch for the identical key (cold first call is real).
    assert outbound == [("Москва", 8, "startswith")]
    assert first == second == RESULT

    # Defensive copies: mutating the first result never touches the second.
    first[0]["name"] = "ИЗМЕНЕНО"
    first[0]["nested"] = "x"
    third = geonames.search_geonames("Москва", limit=8)
    assert third == RESULT
    assert outbound == [("Москва", 8, "startswith")]  # still one outbound


def test_keys_differ_by_query_limit_username(outbound, monkeypatch):
    geonames.search_geonames("Москва", limit=8)
    geonames.search_geonames("Сочи", limit=8)  # different query
    geonames.search_geonames("Москва", limit=5)  # different limit
    monkeypatch.setenv("GEONAMES_USERNAME", "cache-test-user-2")
    geonames.search_geonames("Москва", limit=8)  # different username

    assert len(outbound) == 4


def test_exception_never_cached_and_provider_retried(outbound, monkeypatch):
    def failing_fetch(query: str, limit: int, mode: str):
        raise GeoNamesError("GeoNames request failed.")

    monkeypatch.setattr(geonames, "_fetch_geonames", failing_fetch)
    with pytest.raises(GeoNamesError):
        geonames.search_geonames("Москва", limit=8)

    # The failure is NOT cached: the next identical call really retries the
    # provider (and this time it succeeds).
    def recovering_fetch(query: str, limit: int, mode: str):
        outbound.append((query, limit, mode))
        return [dict(item) for item in RESULT]

    monkeypatch.setattr(geonames, "_fetch_geonames", recovering_fetch)
    result = geonames.search_geonames("Москва", limit=8)
    assert result == RESULT
    assert outbound == [("Москва", 8, "startswith")]


def test_short_query_never_hits_provider_or_cache(outbound):
    assert geonames.search_geonames("М", limit=8) == []
    assert outbound == []
