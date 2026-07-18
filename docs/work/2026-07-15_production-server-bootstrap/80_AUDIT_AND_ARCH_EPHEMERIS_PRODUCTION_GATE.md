# Ephemeris production gate — audit and architecture

## Verified current false-green

Read-only local probe found:

- `/opt/sweph/ephe` is empty;
- sidecar core health still returns success;
- `swe.calc_ut(..., FLG_SWIEPH | FLG_SPEED)` returns flag `260` (`MOSEPH|SPEED`) instead of expected `258` (`SWIEPH|SPEED`) for Sun, Moon and Pluto;
- health reports `git_sha=dev`, `calculation_version=ss-1.0.0` while shared canonical calculation version is `ss-calc-1.2.0`.

Therefore current `/v1/health` is not production readiness proof: missing Swiss files silently fall back to Moshier.

## Code drift

Multiple calculation paths hardcode `/opt/sweph/ephe` or set path independently, including ephemeris utils/calculator, returns, eclipses and progressions. Direct `calc_ut` callers ignore returned engine flags. Existing astronomy oracle also ignores flags and can certify fallback output.

Host-prepare currently creates only an empty writable directory; deploy checks readability/traversability only. Production Compose has no canonical ephemeris artifact mount/identity contract.

## Canonical artifact layout

```text
/opt/solarsage-ephemeris/
  releases/<artifact-id>/
    ephe/
      sepl_18.se1
      semo_18.se1
    manifest.json
    manifest.sha256
  current -> releases/<artifact-id>
```

Root-owned immutable release directories. `current` is an atomic symlink. Sidecar processes read but cannot mutate.

For currently used Sun–Pluto bodies and 1800–2399 technical range, minimum inventory is planetary and Moon files above. Product supported range may be narrower (e.g. 1900–2399) but must be explicit. Asteroid/fixed-star files are added only when product features require them.

## Manifest v1

Non-secret exact manifest:

```text
schema_version
artifact_id
created_at_utc
supported_date_range
file inventory: relative path, exact size, SHA256
Swiss Ephemeris data version
pyswisseph exact version
expected calculation version
oracle probe definitions and golden digest
```

Repository pins expected artifact ID/manifest digest and shared calculation version. Unknown/extra/missing files, symlinks, traversal, wrong owner/mode/size/hash fail.

## Offline installer

Root-only check/apply tool:

1. accepts staged local artifact path, never downloads implicitly;
2. validates regular non-symlink tree and normalized relative paths;
3. verifies exact manifest bytes/hash/inventory;
4. runs offline Swiss engine oracle using staged path;
5. requires returned flag contains `FLG_SWIEPH` and rejects `FLG_MOSEPH`/unexpected JPL fallback;
6. atomically installs immutable release and flips `current` only after proof;
7. preserves previous pointer/artifact for rollback;
8. failed apply leaves current byte/path unchanged.

No artifact bytes are created by host-prepare. Host-prepare verifies installer/config/expected pin; artifact apply is an explicit operator step with local bundle provenance.

## Single runtime owner

Create one central ephemeris runtime module:

- resolves configured current real path once;
- verifies manifest/artifact identity;
- calls `swe.set_ephe_path` once during startup;
- wraps every `calc_ut` and checks return flags;
- exposes stable engine/fallback reason codes;
- all returns/eclipses/progressions/calculator paths use it;
- remove hardcoded service paths/default fallbacks.

Production absence/mismatch is fatal at startup; test-only fallback must be explicit and impossible under `APP_ENV=production`.

## Three readiness layers

### Host gate

- root-owned immutable artifact/current symlink;
- exact manifest digest and inventory;
- files readable by sidecar;
- no writable artifact path for `astro`;
- offline oracle retflags SWIEPH.

### Deploy gate

After candidate venv build but before service switch:

- exact pinned pyswisseph version;
- manifest/artifact/calc-version match candidate repo;
- fixed oracle probes pass with SWIEPH flags;
- no fallback;
- failure before backup/migration/restart where possible.

### Runtime/startup gate

Sidecar `ExecStartPre` or lifespan validates same identity before serving traffic. Any missing/mutated file or fallback prevents ready status.

## Health schema v2

Health response must expose non-secret exact identity:

```text
ok
release_sha (full)
calculation_version
activation/version identity
ephemeris_artifact_id
ephemeris_manifest_sha256
engine=swieph
pyswisseph_version
swiss_data_version
probe flags/fallback=false
stable reason_codes
```

Deploy parses JSON and asserts exact target SHA, canonical calculation version, artifact/digest/library/engine and API↔sidecar identity handshake. Generic HTTP 200/`ok=true` is insufficient.

## Oracle probes

Use fixed deterministic probes covering slow/fast bodies and range boundaries:

- Moon and Pluto on `2026-07-08`;
- representative dates at lower/upper supported boundaries;
- exact requested/returned flags;
- golden longitude/speed with reviewed tolerances;
- artifact/manifest/version bound into golden digest.

The oracle must fail if retflag indicates Moshier/JPL fallback even when coordinates look plausible.

## CI/E2E correction

Current E2E explicitly creates an empty ephemeris directory and thereby tests Moshier fallback. Replace with one of:

- real licensed/redistributable minimal test artifact with manifest; or
- explicit test-only deterministic engine mode whose output cannot be confused with production SWIEPH readiness.

Production gate and health tests always require real SWIEPH flags.

## Dependency reproducibility

Replace loose `pyswisseph>=...` with exact locked version/hash for production. Artifact manifest and release manifest record it. Version mismatch blocks promotion.

## Acceptance matrix

- missing/empty/extra file;
- file/directory symlink and traversal;
- wrong owner/mode/size/hash;
- mutated single byte;
- wrong artifact/manifest/calc/library version;
- retflag MOSEPH/JPLEPH/missing SWIEPH;
- lower/upper date range probes;
- hardcoded-path static scan;
- installer failure/atomic rollback;
- current symlink swap/inode validation;
- startup/health false-green mutations;
- deploy generic-ok mutation rejected;
- API-sidecar release mismatch rejected;
- CI empty-directory fallback cannot pass production contract.

Until this is implemented and a real artifact installed, sidecar health is only process liveness, not production astronomy correctness.
