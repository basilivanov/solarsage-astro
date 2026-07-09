# Architect Review — W3.5 Rework 01

Status: REWORK REQUIRED

Reviewed range: `23c4511..8433753`
Implementation commit: `e899a8a`
Report commit: `8433753`

## Findings

### P0 — Regenerated W3.5 audit artifact was not committed

Evidence:
- After callback, `git status --short --branch` shows:
  - `M artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json`
- `git show --name-only e899a8a` does not include that artifact.
- The uncommitted diff contains the actual W3.5 contract fixes: uppercase solar arc IDs, `source_longitude`, and corrected secondary progression strengths.

Impact:
- HEAD does not contain the required canonical W3.5 artifact.
- A clean checkout of `main` would still have the old artifact, contradicting the report and TZ.

Required fix:
- Commit the regenerated artifact together with the rework report update.
- End with a clean working tree except the pre-existing unrelated untracked files.

### P1 — Sun transition debug is still incomplete in `ActivationEvidence`

Evidence:
- `progressed_sun_transitions()` now returns full transition keys, including `current_house`, `target_house`, `base_strength`, and `orb_factor`.
- `apps/solarsage/solarsage/services/activation_builder.py:1539-1554` still builds sign-transition debug without:
  - `current_house`
  - `target_house`
  - `base_strength`
  - `orb_factor`
- `apps/solarsage/solarsage/services/activation_builder.py:1576-1590` still builds house-transition debug without:
  - `current_sign`
  - `previous_sign`
  - `next_sign`
  - `base_strength`
  - `orb_factor`

Impact:
- The sidecar helper has the data, but the API contract output still violates the W3.5 TZ.
- Because Basil 2026-07-08 has no Sun transition, the artifact assertion does not catch this.

Required fix:
- Pass through every transition key required by `03_rework_01_TZ.md`.
- Add a builder/endpoint-level regression that constructs deterministic sign and house transition activations and verifies the final `ActivationEvidence.debug`, not only the helper output.

### P1 — Sun transition tests are conditional and can pass with zero transitions

Evidence:
- `apps/solarsage/tests/test_secondary_progressions.py:176-196` says "May or may not have a transition"; if `sign_trans` is empty, the test passes.
- `apps/solarsage/tests/test_secondary_progressions.py:198-215` has the same issue for house transitions.
- `apps/solarsage/tests/test_secondary_progressions.py:218-248` loops over whatever transitions exist and only asserts a broad longitude range; if there are no sign transitions, it also passes.

Impact:
- The exact branch that the TZ required to be covered can regress without failing tests.

Required fix:
- Make transition tests deterministic and non-conditional.
- Use a direct fake/minimal context or monkeypatch `calculate_houses_cusps()` if needed.
- Assert at least one sign transition and at least one house transition.
- Assert strength formula and full debug key shape for transitions.

### P2 — Aspect canon is still duplicated

Evidence:
- `apps/solarsage/solarsage/services/progressions.py:58-68` still defines its own `ASPECT_ANGLES`.
- `apps/solarsage/solarsage/services/progressions.py:71-78` still defines its own `_classify_polarity()`.
- The new test only proves equality today; it does not remove the divergence risk called out in the previous review.

Impact:
- Future aspect-map changes still need two edits.

Required fix:
- Reuse the existing builder constants/helpers or extract a small shared helper used by both modules.
- Keep the regression test after removing duplication.

### P2 — Non-numeric orb behavior is not covered

Evidence:
- `03_rework_01_TZ.md` required missing/non-numeric orb values to fail loudly.
- The new tests cover missing `solar_arc.orb` and missing `secondary_progression.orb`, but not non-numeric values.

Required fix:
- Add a non-numeric orb regression for at least both progression techniques, or one parametrized test covering both.

## Do not change

Keep the existing successful fixes:
- canon strength formula for aspect activations;
- per-technique orb lookup;
- uppercase solar arc IDs;
- solar arc `source_longitude`;
- corrected secondary progression strengths;
- no TodayService wiring;
- no push/deploy.

