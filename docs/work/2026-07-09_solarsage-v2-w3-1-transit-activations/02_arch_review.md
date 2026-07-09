# Architect Review: Wave W3.1 Transit Activations

Status: REWORK REQUIRED

Reviewed commit:

- `df82fe3` — W3.1 sidecar real transit activation extraction

## Summary

The implementation is a strong first pass:

- sidecar `/v1/activation-layer` now returns real W3.1 transit activations;
- all four requested techniques are represented in the Basil artifact;
- `Transit Moon opposition natal PLUTO` appears with orb `1.0454°`;
- TodayService remains unwired to the sidecar layer;
- focused sidecar/API tests pass according to the agent report.

W3.1 cannot be accepted yet because several explicit W3.1 gates are red or under-tested.

## Blocking Findings

### P0. Audit script command from TZ fails with system `python3`

Required TZ command:

```bash
python3 scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
```

Architect rerun:

```text
ModuleNotFoundError: No module named 'swisseph'
```

The script imports sidecar code, which depends on `swisseph`, but system `python3` does not have that dependency. The sidecar venv does.

Required fix:

- Make `scripts/audit_sidecar_activation.py` runnable from repo root with the TZ command, or update the accepted verification command and report to use:

```bash
PYTHONPATH=apps/solarsage apps/solarsage/venv/bin/python scripts/audit_sidecar_activation.py ...
```

Preferred: make the script self-reexec into `apps/solarsage/venv/bin/python` when invoked by system `python3`, so the documented root command works.

### P0. Audit artifact is not deterministic across processes

Architect rerun:

```bash
for i in 1 2 3 4 5; do
  PYTHONHASHSEED=random apps/solarsage/venv/bin/python scripts/audit_sidecar_activation.py ...
  sha256sum /tmp/sidecar_activation_$i.json
done
```

Result: different hashes and different first activation technique blocks.

Root cause:

```python
W3_1_SUPPORTED = {"transit_to_natal", "transit_to_angle", "transit_to_lot", "transit_planet_in_house"}
ALL_TECHNIQUES = list(W3_1_SUPPORTED)
```

Set iteration order is hash-seed dependent, so default technique order and artifact JSON order are non-deterministic.

Required fix:

- Replace set-derived default ordering with an explicit list/tuple:

```python
W3_1_SUPPORTED_ORDER = (
    "transit_to_natal",
    "transit_to_angle",
    "transit_planet_in_house",
    "transit_to_lot",
)
W3_1_SUPPORTED = set(W3_1_SUPPORTED_ORDER)
ALL_TECHNIQUES = list(W3_1_SUPPORTED_ORDER)
```

- Preserve requested technique order when caller provides `techniques`.
- Add a test that runs two default builds and asserts activation id order is identical.

### P0. `phase/applying` is computed from raw angular distance, not orb to aspect

TZ required:

> future orb smaller -> applying; future orb larger -> separating.

Current code:

```python
if probe_adist < adist:
    applying = True
```

This is wrong for non-conjunction aspects. Example from Basil Moon-Pluto:

```text
current angular distance = 178.9546
current orb to opposition = 1.0454
probe angular distance = 177.5794
probe orb to opposition = 2.4206
```

The orb is increasing, so the activation is separating. Current artifact says:

```text
phase=applying, applying=True
```

Required fix:

- Compute `current_orb = abs(adist - aspect_angle)`.
- Compute `probe_orb = abs(probe_adist - aspect_angle)`.
- Compare `probe_orb` to `current_orb`.
- Add regression test for Basil `Transit Moon opposition natal Pluto` proving it is `separating` with `applying is False` for 2026-07-08 12:00 Europe/Moscow.

### P1. Basil evidence string does not match required frame-readable form

TZ required:

```text
Transit Moon opposition natal Pluto
```

Current artifact:

```text
Transit Moon opposition natal PLUTO, orb 1.0454°
```

Field/index keys may remain uppercase, but evidence text should be human-readable and match the required exact string.

Required fix:

- Use display/title names in evidence strings for planets:
  - `Pluto`, not `PLUTO`;
  - `Mercury`, not `MERCURY`.
- Keep `target_key="PLUTO"` and `by_planet["PLUTO"]` uppercase.
- Add exact grep/test for `Transit Moon opposition natal Pluto`.

### P1. Sidecar tests do not actually prove Basil Moon-Pluto or lots

Issues:

- `BASIL_REQUEST` in `apps/solarsage/tests/test_activation_transits.py` uses `1990-01-15 Moscow`, not Basil's audit profile.
- The test named `test_activation_layer_endpoint_basil_evidence` also uses the same non-Basil data.
- `test_lot_calculations_and_transit_to_lot` contains a tautology:

```python
assert len(total_lot_refs) >= 0
```

That assertion always passes.

Required fix:

- Rename non-Basil fixtures to avoid false confidence, e.g. `MOSCOW_FIXTURE_REQUEST`.
- Add a true `BASIL_AUDIT_REQUEST` using:
  - birth date `1980-10-30`;
  - birth time `19:50`;
  - lat `67.9394`;
  - lon `32.8144`;
  - tz `Europe/Moscow`;
  - target `2026-07-08 12:00 Europe/Moscow`.
- Add a test that finds `t2n__MOON__OPPOSITION__PLUTO` and checks:
  - evidence includes `Transit Moon opposition natal Pluto`;
  - orb is within `0.05°` of `1.0454`;
  - `phase == "separating"`;
  - `applying is False`.
- Replace the tautology with real assertions:
  - `by_lot` is populated for the fixture used;
  - all seven lot keys are present in debug or index for the audit fixture, if generated;
  - `transit_to_lot` refs point to valid activation ids.

### P2. Agent report has an unfilled commit placeholder

`01_agent_report.md` says:

```text
`<will be filled>`
```

Required fix:

- Update in the rework report with the actual rework commit SHA.

## Evidence To Preserve

Keep these good parts:

- sidecar builder returns all four W3.1 technique families;
- by-planet/by-house/by-angle/by-lot are populated in the Basil artifact;
- no unsupported W3+ techniques are emitted into the artifact;
- TodayService remains unwired to sidecar activation layer;
- API boundary test validates sidecar dict acceptance.

## Required Rework

See `03_rework_01_TZ.md`.
