# AI_HEADER
# module: M-SOLARSAGE-ARCH-DOCS
# wave: W-SOLARSAGE-SVC
# purpose: SolarSage architecture documentation

# SolarSage Architecture

## Overview

SolarSage is split into modular services for better maintainability and testability. The refactoring (W-SOLARSAGE-SVC) extracts calculation logic from a monolithic structure into dedicated service modules.

## Directory Structure

```
apps/solarsage/solarsage/
├── api/                    # FastAPI endpoints
│   ├── natal.py           # POST /v1/natal
│   ├── transits.py        # POST /v1/transits
│   └── health.py          # GET /v1/health
├── services/              # Business logic services
│   ├── natal.py           # Natal chart calculations
│   ├── transits.py        # Transit calculations
│   └── calculator.py      # Legacy (deprecated)
├── models/                # Data models
│   ├── chart.py           # NatalChart, Transit
│   └── position.py        # PlanetPosition
├── utils/                 # Shared utilities
│   └── ephemeris.py       # Swiss Ephemeris wrapper
├── schemas/               # Pydantic request/response schemas
│   ├── natal.py
│   └── transits.py
└── core/                  # Core configuration
    ├── config.py
    └── health.py
```

## Modules

### Services (`solarsage/services/`)

**NatalService** — Natal chart calculations
- `calculate_natal_chart()` — Calculate natal chart from birth data
- Returns `NatalChart` with positions, houses, special points

**TransitsService** — Transit calculations
- `calculate_transits()` — Find transits to natal positions
- Detects major aspects: conjunction, opposition, trine, square, sextile
- Returns list of `Transit` objects

**Future services:**
- `ProgressionsService` — Secondary progressions
- `AspectsService` — Advanced aspect calculations
- `SynastryService` — Relationship compatibility
- `RelocationsService` — Relocation charts

### Models (`solarsage/models/`)

**NatalChart** — Natal chart data
- `birth_datetime` — Birth date/time
- `latitude`, `longitude` — Birth location
- `positions` — Planetary positions
- `houses` — House cusps
- `special_points` — ASC, MC, ARMC, Vertex
- `house_system` — PLACIDUS or WHOLE_SIGN

**Transit** — Transit data
- `planet` — Transiting planet
- `aspect` — Aspect type (conjunction, opposition, etc)
- `natal_planet` — Natal planet being aspected
- `orb` — Orb in degrees
- `date` — Transit date

**PlanetPosition** — Planet position data
- `name` — Planet name
- `longitude`, `latitude` — Ecliptic coordinates
- `speed` — Daily motion
- `sign` — Zodiac sign

### Utils (`solarsage/utils/`)

**ephemeris.py** — Swiss Ephemeris wrapper
- `calculate_julian_day()` — Convert date/time/tz to Julian Day
- `calculate_positions()` — Calculate planetary positions for JD
- `calculate_houses_cusps()` — Calculate houses and special points
- `get_sign()` — Get zodiac sign from longitude

Wraps `pyswisseph` library for astrological calculations.

## Service Responsibilities

### NatalService

1. Calculate natal chart from birth data (date, time, timezone, location)
2. Calculate houses using Placidus system (or Whole Sign for high latitudes ≥60°)
3. Calculate special points (ASC, MC, ARMC, Vertex)
4. Return structured `NatalChart` model

### TransitsService

1. Calculate current planetary positions for target date
2. Find transits to natal positions
3. Detect major aspects within orb:
   - Conjunction (0°, orb 8°)
   - Opposition (180°, orb 8°)
   - Trine (120°, orb 8°)
   - Square (90°, orb 8°)
   - Sextile (60°, orb 6°)
4. Return list of `Transit` objects

## Data Flow

```
API Request (POST /v1/natal)
    ↓
API Layer (api/natal.py)
    ↓
Service Layer (services/natal.py)
    ↓
Utils Layer (utils/ephemeris.py)
    ↓
Swiss Ephemeris (pyswisseph)
    ↓
Models (models/chart.py)
    ↓
API Response (NatalResponse)
```

## Design Principles

1. **Separation of Concerns** — API, services, models, utils are separate
2. **Single Responsibility** — Each service handles one domain
3. **Dependency Injection** — Services instantiated in API layer
4. **Testability** — Services can be tested independently
5. **Reusability** — Utils shared across services

## Migration from Monolith

**Before (W-3.2):**
- `services/calculator.py` — Monolithic calculation functions
- API endpoints call calculator functions directly

**After (W-SOLARSAGE-SVC):**
- `services/natal.py` — NatalService class
- `services/transits.py` — TransitsService class
- `utils/ephemeris.py` — Shared ephemeris utilities
- `models/chart.py` — Data models
- API endpoints use service classes

**Benefits:**
- Better testability (mock services, not functions)
- Clearer responsibilities (service per domain)
- Easier to extend (add new services)
- Reduced coupling (services don't depend on each other)

## Future Enhancements

### ProgressionsService
- Secondary progressions
- Solar arc directions
- Tertiary progressions

### AspectsService
- Advanced aspect calculations
- Aspect patterns (T-square, Grand Trine, Yod)
- Midpoints

### SynastryService
- Relationship compatibility
- Composite charts
- Davison charts

### RelocationsService
- Relocation charts (Astro*Carto*Graphy)
- Local space charts
- Parans

## Testing

Tests located in `apps/solarsage/tests/test_services.py`:

- `test_natal_service()` — Verify natal chart calculation
- `test_transits_service()` — Verify transit calculation
- `test_natal_service_high_latitude()` — Verify house system selection
- `test_transits_service_aspects()` — Verify aspect detection

Run tests:
```bash
cd apps/solarsage
pytest tests/test_services.py -v
```

## Dependencies

- **pyswisseph** — Swiss Ephemeris library for calculations
- **FastAPI** — Web framework
- **Pydantic** — Data validation and schemas
- **pytest** — Testing framework
