# Review: 13eead1 — Wave 6 Golden Tests

Date: 2026-06-11
Status: ACCEPTED WITH NON-BLOCKING CLARIFICATION
Reviewed commit: `13eead1`
Branch: `feat/natal-full-report`
Related TZ: `docs/work/2026-06-10_natal_full_report_cache_TZ.md`
Previous Wave 5 follow-up review: `docs/work/2026-06-11_0609502_wave_5_non_blocking_followups_acceptance_review.md`

## 1. Scope reviewed

Wave 6 target:

- add a stable golden fixture for Zhanna's natal data;
- add a realistic mocked SolarSage sidecar response;
- verify key natal facts through the actual `NatalContextService` pipeline;
- prove no transit contamination in natal context;
- prove cache hit/miss behavior;
- add fixture integrity checks.

Files reviewed:

- `apps/api/tests/fixtures/golden_zhanna.json`
- `apps/api/tests/fixtures/sidecar_zhanna_natal.json`
- `apps/api/tests/test_natal_golden_zhanna.py`

Commit message reports: `193 natal tests passing`.

## 2. Verdict

ACCEPTED WITH NON-BLOCKING CLARIFICATION.

The Wave 6 golden regression guard is accepted. The new fixture and tests cover the key natal facts, mocked sidecar contract, no-transit rule, and NatalContext cache hit/miss behavior.

One clarification: the new Wave 6 file directly tests cache hit/miss and profile-hash mutation, but it does not itself directly test report idempotency or explicit cache invalidation rows. If those are intended as final-project acceptance claims, they should be referenced from prior waves or covered by a separate explicit test. This is not blocking for the Wave 6 golden tests themselves.

## 3. Golden fixture review

### GOOD 1 — Birth profile matches the Zhanna golden sample

`golden_zhanna.json` contains:

- birth date: `1993-01-07`;
- birth time: `10:33`;
- city: `Chirchiq`;
- coordinates: `41.4689`, `69.5822`;
- timezone: `Asia/Tashkent`;
- gender: `female`.

Acceptance result: OK.

### GOOD 2 — Key chart facts match the supplied TZ/golden reference

The fixture includes the expected facts that matter for regression:

- ASC Pisces `~11.92°`;
- MC Sagittarius `~20.47°`;
- Sun Capricorn, house 11;
- Moon Gemini, house 4;
- Mercury Capricorn, house 10;
- Venus Pisces, house 12;
- Mars Cancer, house 5, retrograde;
- Jupiter Libra, house 7;
- Saturn Aquarius, house 12;
- Uranus Capricorn, house 11;
- Neptune Capricorn, house 11;
- Pluto Scorpio, house 9;
- North Node Sagittarius, house 10;
- South Node Gemini, house 4.

`degree_tolerance` is set to `2.0`, which is reasonable for a regression guard over formatted/normalized degrees.

Acceptance result: OK.

### GOOD 3 — Sidecar fixture uses consistent longitude/sign mapping

`sidecar_zhanna_natal.json` uses absolute longitudes consistent with sign starts plus in-sign degree, for example:

- Sun Capricorn 16.93 → longitude `286.93`;
- Moon Gemini 29.63 → longitude `89.63`;
- Mars Cancer 17.95 → longitude `107.95`;
- North Node Sagittarius 21.42 → longitude `261.42`;
- South Node Gemini 21.42 → longitude `81.42`.

This is important because the pipeline may derive in-sign degree from longitude.

Acceptance result: OK.

## 4. Test coverage review

### GOOD 4 — Planet signs and degrees are checked through `NatalContextService`

The tests do not only inspect the JSON fixture. They patch `get_solarsage_client().get_natal()` and run:

```python
context = await service.get_or_build_natal_context(user.id)
```

Then they assert planet signs and degrees from the resulting `NatalContextData`.

Covered objects:

- Sun;
- Moon;
- Mercury;
- Venus;
- Mars;
- Jupiter;
- Saturn;
- Uranus;
- Neptune;
- Pluto;
- North Node;
- South Node.

Acceptance result: OK.

### GOOD 5 — Houses and retrograde flags are checked

House checks cover the 10 main planets against the `natal_houses` fixture.

Retrograde checks cover:

- Mars retrograde = `True`;
- Sun retrograde = `False`;
- Jupiter retrograde = `False`.

Acceptance result: OK.

### GOOD 6 — ASC/MC and house system are checked

The tests assert:

- ASC sign and degree tolerance;
- MC sign and degree tolerance;
- `context.house_system == "Placidus"`.

Acceptance result: OK.

### GOOD 7 — No transit contamination is explicitly guarded

The tests assert:

- no planet name starts with `Transit_`;
- no aspect endpoint starts with `Transit_`;
- `mock_client.get_transits.assert_not_called()`.

This directly protects the earlier architectural requirement that natal context is natal-only.

Acceptance result: OK.

### GOOD 8 — Cache hit/miss is covered

The tests verify:

- first `get_or_build_natal_context()` call calls sidecar `get_natal()` once;
- second call for the same profile does not call sidecar again.

This is the right golden regression for NatalContext cache reuse.

Acceptance result: OK.

### GOOD 9 — Profile hash mutation is covered

The tests verify that the profile hash is deterministic and changes when:

- birthday changes;
- birth latitude changes.

Acceptance result: OK.

### GOOD 10 — Fixture integrity checks exist

The test file validates structural presence of:

- golden profile;
- expected facts;
- natal houses;
- degree tolerance;
- house system;
- sidecar house system;
- 12 sidecar houses;
- sidecar special points.

Acceptance result: OK.

## 5. Non-blocking clarification

### NOTE 1 — “Invalidation” and “report idempotency” are not directly tested in the new Wave 6 file

The header and summary mention acceptance coverage for:

- invalidation;
- report idempotency.

The new Wave 6 test file directly covers:

- cache hit/miss;
- profile hash mutation;
- no transit contamination;
- golden chart facts.

It does not directly assert, in this file:

- old `NatalChartCache` row invalidation via `invalidated_at`;
- rebuilding a context after profile mutation;
- `NatalReportService.generate_report()` idempotency for existing READY/GENERATING reports.

If these are already covered by previous wave tests, the final evidence document should reference those tests explicitly. If not, add a small follow-up test file for final acceptance evidence.

This is not a blocker for accepting Wave 6 golden regression tests.

### NOTE 2 — Structural planet-count test is intentionally loose

`test_has_12_planets_and_nodes()` currently asserts `len(context.planets) >= 10`, not exactly 12. The sign/degree parameterized tests still force North Node and South Node to exist, so this is acceptable. If desired, tighten this assertion later to `>= 12` or exact expected count after deciding whether nodes are included in `context.planets` by contract.

### NOTE 3 — CI was not independently fetched

Commit message reports `193 natal tests passing`. I reviewed the relevant code and tests but did not independently fetch CI logs.

## 6. Acceptance decision

Accepted.

Wave 6 now provides a useful golden regression layer for the natal pipeline:

- stable Zhanna fixture;
- deterministic sidecar mock;
- key signs/degrees/houses/angles/retrograde facts;
- no transit contamination;
- NatalContext cache hit/miss;
- profile-hash determinism/mutation;
- fixture integrity.

All six waves can be considered implemented from the review perspective, with only the non-blocking clarification above to reference or close in final evidence.