# P2-D TZ — shared sidecar activation grid for birth-time uncertainty

Date: 2026-07-31
Status: implementation packet
Depends on: packet 26 / commit `de91a5dc`.

## 1. Goal

Add one internal sidecar batch boundary that calculates the 1/3/7 birth-time
control points from `BirthTimeResolution` without repeating target ephemeris
and transit-timing work for every sample.

The calculation remains sequential inside one request. Swiss Ephemeris is not
parallelized in-process. Concurrency across users remains the worker/job
layer's responsibility.

## 2. Exact write scope

Only these paths may be created/changed:

1. `apps/solarsage/solarsage/services/calculation_core.py`;
2. `apps/solarsage/solarsage/api/activation_layer.py`;
3. `apps/solarsage/tests/test_activation_grid.py` (new);
4. `apps/api/app/clients/solarsage_client.py`;
5. `apps/api/tests/test_solarsage_client.py`;
6. `grace/verification-matrix.md`;
7. `grace/knowledge-graph.xml`;
8. this reviewer-owned packet — do not edit it.

Do not change shared activation evidence fields, calculation/activation
versions, frozen canons, legacy Today/Calendar, or public generated contracts.
If another path is needed, stop and report. Coder does not commit or push.

## 3. In-process calculation entrypoint

Add a public core function:

```python
calculate_activation_grid(
    *,
    birth_date: str,
    birth_times: Sequence[str],
    birth_lat: float,
    birth_lon: float,
    birth_tz: str,
    target_date: str,
    target_time: str,
    target_tz: str,
    house_system: str = "PLACIDUS",
    techniques: list[str] | None = None,
    current_location: dict[str, Any] | None = None,
) -> tuple[ActivationLayer, ...]
```

Behavior:

1. Validate 1..7 strictly increasing, unique minute-precision `HH:MM` values;
   `24:00`, seconds, whitespace/coercion and malformed strings are rejected.
2. Prepare `TargetCalculationContext` exactly once.
3. If requested/default techniques include a transit technique that uses the
   timing solver (`transit_to_natal|transit_to_angle|transit_to_lot`), create
   exactly one `TransitTimingSolver` for the shared target moment; otherwise do
   not create one.
4. For each birth time in request order, prepare its own natal context and call
   the accepted single-layer function with the shared target context, shared
   solver and `timing_scope="convergence_eligible"`.
5. Return layers in exact request order. Do not merge evidence here.

The single-layer entrypoint remains unchanged and direct single versus grid
calculation must serialize identically when both use the convergence timing
scope. No thread/process pool, no hidden cache, no NumPy.

## 4. Internal HTTP contract

Add `POST /v1/activation-layer-grid` alongside the existing endpoint.

Request reuses the existing target/current-location/house-system/techniques
shape; birth is:

```json
{
  "birth": {
    "date": "1980-10-30",
    "times": ["00:00", "03:00", "05:59"],
    "lat": 67.9394,
    "lon": 32.8144,
    "tz": "Europe/Moscow"
  }
}
```

Response is snake_case, internal-only:

```json
{
  "meta": {
    "calculation_version": "ss-calc-1.3.0",
    "activation_layer_version": "...",
    "sample_count": 3
  },
  "samples": [
    {"birth_time": "00:00", "activation_layer": {}}
  ]
}
```

Every sample contains the existing strict `ActivationLayer`; all layers must
have one calculation version and preserve request order. Invalid time grids
are Pydantic 422. Unexpected calculation failure returns a generic 500 detail
without echoing birth data or exception text.

Upgrade the modified sidecar route file to truthful operative GRACE markers;
do not mechanically reformat unrelated route behavior.

## 5. API client boundary

Add a frozen internal sample record and:

```python
SolarSageClient.get_activation_layer_grid(..., birth_times: Sequence[str])
    -> tuple[ActivationGridSample, ...]
```

The method posts once to `/v1/activation-layer-grid`, validates every nested
layer with `app.schemas.activation.ActivationLayer`, and returns ordered typed
samples containing echoed `birth_time` plus the typed layer.

Fail closed with a stable client error for malformed/missing meta, sample
count, order/time mismatch, duplicate/extra samples, version disagreement or
invalid nested layer. Do not fall back to N calls of `get_activation_layer`.
HTTP status/timeout exceptions keep their existing httpx behavior.

Update the client module contract/map/owned tests truthfully. Do not add a
public OpenAPI root: this is API-to-sidecar transport, not frontend wire.

## 6. Required tests

1. Core rejects empty, >7, duplicate, unsorted and malformed grids.
2. Spy test proves one target context, one timing solver and N natal/single
   layer calls for a transit grid; the exact same shared objects reach all N
   calls and order is preserved.
3. Non-transit technique grid creates no timing solver.
4. Actual one-point grid output is byte/value-identical to the existing direct
   single call with `timing_scope="convergence_eligible"`.
5. HTTP accepts canonical exact/bucket/unknown grids and preserves sample
   order; invalid grids return 422; unexpected error is generic 500.
6. API client sends one request with exact body, validates nested
   `ActivationLayer` records, and returns ordered typed samples.
7. API client rejects every malformed response category above and never calls
   the legacy single endpoint as fallback.
8. Existing single endpoint/direct parity tests remain green; versions are not
   changed.

Use real ephemeris only for the one-point parity test. Use small deterministic
fakes/spies for 3/7-point orchestration tests so the unit gate stays fast.

## 7. GRACE and verification

Register the grid orchestration edge/module behavior and
`UC-TODAY-BIRTH-TIME-ACTIVATION-GRID`.

Run:

```bash
PYTHONPATH=apps/solarsage:packages/py-contracts \
  /opt/solarsage-astro/apps/solarsage/venv/bin/python -m pytest \
  apps/solarsage/tests/test_activation_grid.py \
  apps/solarsage/tests/test_calculation_core.py \
  apps/solarsage/tests/test_activation_layer_endpoint.py -q

cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_solarsage_client.py tests/test_activation_contracts.py -q
cd ../..

/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/clients/solarsage_client.py \
  apps/api/tests/test_solarsage_client.py
/opt/solarsage-astro/apps/solarsage/venv/bin/python -m ruff check \
  apps/solarsage/solarsage/services/calculation_core.py \
  apps/solarsage/solarsage/api/activation_layer.py \
  apps/solarsage/tests/test_activation_grid.py
python3 scripts/grace_lint.py apps/api/app --quiet
python3 scripts/grace_lint.py \
  apps/solarsage/solarsage/services/calculation_core.py \
  apps/solarsage/solarsage/api/activation_layer.py
bash scripts/grace/check-markers.sh
git diff --check
```

Report exact counts, one-point parity, reuse call counts, HTTP/client negative
matrix and exact changed paths.

## 8. Out of scope / next packet

- cross-control semantic intersection, orb margin and sect stability;
- ActivationEvidence to RawPhysicalFact adaptation;
- profile hash/cache/snapshot identity;
- Today/Calendar cutover and legacy noon-fallback deletion;
- DB, public API/frontend contracts, LLM, pregen or deployment.
