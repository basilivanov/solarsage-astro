#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: GENERATE_CORPUS_MANIFEST — deterministic synthetic replay corpus.
# ROLE: Produces privacy-safe charts spanning latitude, longitude, TZ, DST,
#       half-hour, and quarter-hour timezone regimes.
# ############################################################################

# START_MODULE_CONTRACT: M-GENERATE-CORPUS-MANIFEST
# purpose: Generate the canonical 120-chart × 2-year W1 replay manifest.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/generate_corpus_manifest.py
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_manifest.v1.json
# inputs: fixed seed, location registry, current calculation/canon source bytes.
# outputs: deterministic JSON manifest with source fingerprint and shard mapping.
# dependencies: Python stdlib; repository source files.
# side_effects: writes corpus_manifest.v1.json.
# emitted_logs: none.
# invariants:
#   - All chart data is synthetic and contains no user/profile identifiers.
#   - Same seed and source tree produce byte-identical chart entries.
#   - Every location contributes exactly five charts.
# failure_policy: raises on missing source, invalid timezone, or wrong chart count.
# END_MODULE_CONTRACT: M-GENERATE-CORPUS-MANIFEST

# START_MODULE_MAP: M-GENERATE-CORPUS-MANIFEST
# public_entrypoints:
#   - build_manifest
#   - main
# semantic_blocks:
#   - LOCATION_REGISTRY: geographic and timezone strata.
#   - SOURCE_FINGERPRINT: content identity for replay lineage.
#   - MANIFEST_BUILD: deterministic chart generation.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_corpus_manifest.py
# END_MODULE_MAP: M-GENERATE-CORPUS-MANIFEST

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name("corpus_manifest.v1.json")
SEED = 20260729
CHARTS_PER_LOCATION = 5


# START_BLOCK: LOCATION_REGISTRY
LOCATIONS: tuple[dict, ...] = (
    {"key": "moscow", "lat": 55.7558, "lon": 37.6173, "tz": "Europe/Moscow", "dst": False},
    {"key": "murmansk", "lat": 68.9707, "lon": 33.0749, "tz": "Europe/Moscow", "dst": False},
    {"key": "tromso", "lat": 69.6492, "lon": 18.9553, "tz": "Europe/Oslo", "dst": True},
    {"key": "reykjavik", "lat": 64.1466, "lon": -21.9426, "tz": "Atlantic/Reykjavik", "dst": False},
    {"key": "london", "lat": 51.5074, "lon": -0.1278, "tz": "Europe/London", "dst": True},
    {"key": "new_york", "lat": 40.7128, "lon": -74.0060, "tz": "America/New_York", "dst": True},
    {"key": "los_angeles", "lat": 34.0522, "lon": -118.2437, "tz": "America/Los_Angeles", "dst": True},
    {"key": "mexico_city", "lat": 19.4326, "lon": -99.1332, "tz": "America/Mexico_City", "dst": False},
    {"key": "quito", "lat": -0.1807, "lon": -78.4678, "tz": "America/Guayaquil", "dst": False},
    {"key": "sao_paulo", "lat": -23.5505, "lon": -46.6333, "tz": "America/Sao_Paulo", "dst": False},
    {"key": "buenos_aires", "lat": -34.6037, "lon": -58.3816, "tz": "America/Argentina/Buenos_Aires", "dst": False},
    {"key": "cape_town", "lat": -33.9249, "lon": 18.4241, "tz": "Africa/Johannesburg", "dst": False},
    {"key": "nairobi", "lat": -1.2921, "lon": 36.8219, "tz": "Africa/Nairobi", "dst": False},
    {"key": "cairo", "lat": 30.0444, "lon": 31.2357, "tz": "Africa/Cairo", "dst": True},
    {"key": "delhi", "lat": 28.6139, "lon": 77.2090, "tz": "Asia/Kolkata", "dst": False},
    {"key": "kathmandu", "lat": 27.7172, "lon": 85.3240, "tz": "Asia/Kathmandu", "dst": False},
    {"key": "bangkok", "lat": 13.7563, "lon": 100.5018, "tz": "Asia/Bangkok", "dst": False},
    {"key": "singapore", "lat": 1.3521, "lon": 103.8198, "tz": "Asia/Singapore", "dst": False},
    {"key": "tokyo", "lat": 35.6762, "lon": 139.6503, "tz": "Asia/Tokyo", "dst": False},
    {"key": "sydney", "lat": -33.8688, "lon": 151.2093, "tz": "Australia/Sydney", "dst": True},
    {"key": "adelaide", "lat": -34.9285, "lon": 138.6007, "tz": "Australia/Adelaide", "dst": True},
    {"key": "perth", "lat": -31.9523, "lon": 115.8613, "tz": "Australia/Perth", "dst": False},
    {"key": "auckland", "lat": -36.8509, "lon": 174.7645, "tz": "Pacific/Auckland", "dst": True},
    {"key": "anchorage", "lat": 61.2181, "lon": -149.9003, "tz": "America/Anchorage", "dst": True},
)
# END_BLOCK: LOCATION_REGISTRY


# START_BLOCK: SOURCE_FINGERPRINT
FINGERPRINT_FILES: tuple[str, ...] = (
    "grace/canon/aspect_rules.v1.yml",
    "grace/canon/activation_rules.v1.yml",
    "grace/canon/firdar.v1.yml",
    "grace/canon/today_convergence.v1.yml",
    "packages/py-contracts/solarsage_contracts/versions.py",
    "apps/solarsage/solarsage/core/ephemeris_runtime.py",
    "apps/solarsage/solarsage/utils/ephemeris.py",
    "apps/solarsage/solarsage/services/activation_builder.py",
    "apps/solarsage/solarsage/services/calculation_core.py",
    "apps/solarsage/solarsage/services/transit_timing.py",
    "apps/api/app/services/normalization_service.py",
    "apps/api/app/services/day_delta_service.py",
    "apps/api/app/services/day_factor_ledger.py",
    "apps/api/app/services/today_focus_builder.py",
    "docs/work/2026-07-29_today-convergence-rewrite/analysis/ablation_harness.py",
    "docs/work/2026-07-29_today-convergence-rewrite/analysis/birthtime_replay.py",
    "docs/work/2026-07-29_today-convergence-rewrite/analysis/corpus_replay.py",
    "docs/work/2026-07-29_today-convergence-rewrite/analysis/direct_replay_pipeline.py",
    "docs/work/2026-07-29_today-convergence-rewrite/analysis/tone_policy_candidate.py",
)


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for relative in FINGERPRINT_FILES:
        path = REPO / relative
        data = path.read_bytes()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()
# END_BLOCK: SOURCE_FINGERPRINT


# START_BLOCK: MANIFEST_BUILD
def _bucket(hour: int) -> str:
    return ("night", "morning", "day", "evening")[hour // 6]


def build_manifest() -> dict:
    rng = random.Random(SEED)
    charts: list[dict] = []
    for location in LOCATIONS:
        ZoneInfo(location["tz"])
        for _ in range(CHARTS_PER_LOCATION):
            index = len(charts)
            year = rng.randint(1950, 2004)
            month = rng.randint(1, 12)
            day = rng.randint(10, 20)
            hour = rng.randint(0, 23)
            minute = rng.randint(0, 59)
            birth_time = f"{hour:02d}:{minute:02d}"
            charts.append(
                {
                    "chart_id": f"syn-{index:03d}-{location['key']}",
                    "synthetic": True,
                    "birth_date": f"{year:04d}-{month:02d}-{day:02d}",
                    "birth_time": birth_time,
                    "birth_time_bucket": _bucket(hour),
                    "birth_lat": location["lat"],
                    "birth_lon": location["lon"],
                    "birth_tz": location["tz"],
                    "target_tz": location["tz"],
                    "current_lat": location["lat"],
                    "current_lon": location["lon"],
                    "current_tz": location["tz"],
                    "house_system": "PLACIDUS",
                    "location_key": location["key"],
                    "location_dst": location["dst"],
                    "latitude_band": (
                        "high" if abs(location["lat"]) >= 60
                        else "equatorial" if abs(location["lat"]) < 10
                        else "mid"
                    ),
                    "shard_residue_mod5": index % 5,
                }
            )
    expected = len(LOCATIONS) * CHARTS_PER_LOCATION
    if len(charts) != expected or expected != 120:
        raise RuntimeError(f"Expected 120 charts, got {len(charts)}")

    return {
        "schema_version": "today-convergence-corpus.v1",
        "synthetic_only": True,
        "seed": SEED,
        "formula_version": "today-convergence-2",
        "date_range": ["2025-01-01", "2026-12-31"],
        "n_days": 730,
        "n_charts": len(charts),
        "source_fingerprint_sha256": source_fingerprint(),
        "fingerprint_files": list(FINGERPRINT_FILES),
        "sharding": {
            "modulus": 5,
            "local_residues": [0],
            "remote_residues": [1, 2, 3, 4],
        },
        "birth_time_modes": {
            "exact": "manifest birth_time",
            "night": ["00:00", "03:00", "05:59"],
            "morning": ["06:00", "09:00", "11:59"],
            "day": ["12:00", "15:00", "17:59"],
            "evening": ["18:00", "21:00", "23:59"],
            "unknown": ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:59"],
            "shifted_night": ["01:00", "03:00", "05:00"],
            "shifted_morning": ["07:00", "09:00", "11:00"],
            "shifted_day": ["13:00", "15:00", "17:00"],
            "shifted_evening": ["19:00", "21:00", "23:00"],
        },
        "charts": charts,
    }


def main() -> None:
    payload = build_manifest()
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT}: {payload['n_charts']} charts, fingerprint={payload['source_fingerprint_sha256']}")


if __name__ == "__main__":
    main()
# END_BLOCK: MANIFEST_BUILD
