# Architect Acceptance: Wave W3.1 Transit Activations

Status: ACCEPTED

Accepted implementation:

- `df82fe3` — initial W3.1 transit activation extraction
- `b345a5b` — runtime stabilization rework
- `e5c4ff8` — test-contract rework
- `149a489` — report traceability fix

## Accepted Scope

The sidecar now produces real W3.1 activation families:

- `transit_to_natal`
- `transit_to_angle`
- `transit_planet_in_house`
- `transit_to_lot`

The accepted implementation preserves the W3.1 boundary:

- scoring v2 is not enabled;
- TodayService is not wired to the sidecar activation layer;
- unsupported W3+ techniques are not emitted as fake activations.

## Architect Verification

Fresh verification on current `main`:

```text
sidecar targeted: 20 passed, 1 warning
sidecar full:     41 passed, 1 warning
API full:         682 passed, 5 skipped, 1 warning
```

Audit command from repository root:

```bash
python3 scripts/audit_sidecar_activation.py \
  --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
  --date 2026-07-08 \
  --out artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
```

Verified:

- command exits successfully;
- regenerated artifact is clean against git;
- three `PYTHONHASHSEED=random` runs produce identical SHA-256:
  `71f69a4d297c064afe6f6dff4e797e49abfa05020e84389888b0d2d64c689c82`;
- artifact contains 111 activations;
- all four W3.1 technique families are present;
- all seven lot keys are present:
  `FORTUNE`, `SPIRIT`, `EROS`, `MARRIAGE`, `NECESSITY`, `VICTORY`, `NEMESIS`;
- all four angle keys are present:
  `ASC`, `DSC`, `MC`, `IC`;
- Basil Moon-Pluto evidence is:
  `Transit Moon opposition natal Pluto, orb 1.0454°`;
- Basil Moon-Pluto is `phase="separating"` and `applying=false`;
- no `natal PLUTO` display text remains;
- no deferred W3+ technique appears in the artifact;
- `sidecar_activation_layer=None` remains in TodayService;
- base-to-HEAD whitespace check is clean.

## Decision

Wave W3.1 is accepted. Proceed to the next activation-technique wave from
`docs/15_SolarSage_v2_activation_audit_TZ.md`.
