# W-SOLARSAGE-SVC — Split reference collector into product service modules

## Decision

Refactor monolithic SolarSage into modular architecture: services (natal, transits), models (chart, position), utils (ephemeris). Improves maintainability and testability.

**Architecture:**
- **Services** — NatalService, TransitsService (business logic)
- **Models** — NatalChart, Transit, PlanetPosition (data structures)
- **Utils** — ephemeris utilities (Swiss Ephemeris wrapper)
- **API** — Updated to use services instead of direct calculator calls

**Benefits:**
- Better separation of concerns
- Easier to test (mock services)
- Clearer responsibilities
- Reduced coupling
- Foundation for future services (progressions, synastry, relocations)

## Acceptance Criteria

- [x] NatalService for natal chart calculations
- [x] TransitsService for transit calculations
- [x] Chart models (NatalChart, Transit, PlanetPosition)
- [x] Ephemeris utils (calculate_positions, calculate_julian_day, calculate_houses_cusps)
- [x] Updated API endpoints (natal.py, transits.py) to use services
- [x] Package exports (__init__.py files)
- [x] Tests for services (4 tests)
- [x] Architecture documentation (SOLARSAGE_ARCHITECTURE.md)
- [x] All existing tests pass (20/20)

## Evidence

**Services:**
- File: `apps/solarsage/solarsage/services/natal.py` — NatalService (60 lines)
- File: `apps/solarsage/solarsage/services/transits.py` — TransitsService (80 lines)
- File: `apps/solarsage/solarsage/services/__init__.py` — Service exports

**Models:**
- File: `apps/solarsage/solarsage/models/chart.py` — NatalChart, Transit (30 lines)
- File: `apps/solarsage/solarsage/models/position.py` — PlanetPosition (15 lines)
- File: `apps/solarsage/solarsage/models/__init__.py` — Model exports

**Utils:**
- File: `apps/solarsage/solarsage/utils/ephemeris.py` — Ephemeris utilities (140 lines)
- File: `apps/solarsage/solarsage/utils/__init__.py` — Utils exports

**API Updates:**
- File: `apps/solarsage/solarsage/api/natal.py` — Uses NatalService (W-SOLARSAGE-SVC)
- File: `apps/solarsage/solarsage/api/transits.py` — Uses ephemeris utils (W-SOLARSAGE-SVC)
- File: `apps/solarsage/solarsage/core/health.py` — Direct swisseph usage (W-SOLARSAGE-SVC)

**Documentation:**
- File: `docs/SOLARSAGE_ARCHITECTURE.md` — Architecture documentation (200+ lines)

**Tests:**
- File: `apps/solarsage/tests/test_services.py` — 4 service tests
- Test: `test_natal_service` — PASSED
- Test: `test_transits_service` — PASSED
- Test: `test_natal_service_high_latitude` — PASSED
- Test: `test_transits_service_aspects` — PASSED
- All tests: 20/20 PASSED (including existing tests)

## Negative Tests

- [x] Calculate natal without birth_datetime → ValueError (handled by datetime.strptime)
- [x] Calculate transits with invalid date → ValueError (handled by datetime.strptime)
- [x] Ephemeris calculation failure → HTTPException 500 (handled in API layer)
- [x] High latitude (≥60°) → Graceful fallback to WHOLE_SIGN house system

## Migration Notes

**Before (W-3.2):**
```python
# Monolithic calculator
from ..services.calculator import calculate_planets, calculate_houses
```

**After (W-SOLARSAGE-SVC):**
```python
# Modular services
from ..services.natal import NatalService
from ..utils.ephemeris import calculate_positions
```

**Deprecated:**
- `services/calculator.py` — Functions moved to utils/ephemeris.py and services

**Future Services:**
- ProgressionsService — Secondary progressions
- AspectsService — Advanced aspect calculations
- SynastryService — Relationship compatibility
- RelocationsService — Relocation charts

## Performance

No performance regression. All calculations use same Swiss Ephemeris backend. Modular structure adds negligible overhead (service instantiation).

## Backward Compatibility

API endpoints unchanged. Request/response schemas unchanged. Existing clients unaffected.
