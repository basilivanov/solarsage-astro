# Wave W0 Rework 01 Architect Review

Status: REWORK REQUIRED

Reviewed commit: `6cc4f16012492344c4099efd21bddcdd69805ee3`

## Verification Run

Passed:

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_astronomy_oracle.py \
  apps/api/tests/test_semantic_contexts.py \
  apps/api/tests/test_today_concrete_advice_consistency.py \
  apps/api/tests/test_today_concrete_advice.py \
  apps/api/tests/test_day_endpoints.py \
  apps/api/tests/test_calendar_endpoints.py \
  -q
```

Result: `34 passed, 1 warning`.

Passed:

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_ephemeris_retrograde.py \
  tests/test_services.py \
  -q
```

Result: `5 passed`.

Passed:

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

Result: exit code `0`.

Passed:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

Evidence:

- `day_status.pass=true`
- all `sphere_scores[*].pass=true`
- `top_signals.pass=true`
- `retrograde_flag_pass=true`
- `moon_phase.pass=true`
- `moon_phase.production_percent=44`
- `moon_phase.oracle_percent=43.792`
- `11_final_today_payload.json.meta.content_version=6`
- `11_final_today_payload.json.meta.cached=false`

Note: this architect verification regenerated `11_final_today_payload.json`, `debug/final_today_payload.json`, and `debug/audit_summary.json`, so the worktree is currently dirty on generated artifacts. Rework must leave a clean committed state.

## Findings

### P0 — scoring oracle can still exit `0` when `top_signals` mismatch

`scripts/audit_scoring_oracle.py` compares `top_signals` and writes a `pass` flag, but `main()` only propagates failures from `day_status` and `sphere_scores`.

Current code:

```python
has_failed = not comp["day_status"]["pass"]
for key, val in comp["sphere_scores"].items():
    if not val["pass"]:
        has_failed = True
```

Impact:

- W0 baseline explicitly covers `top_signals`.
- A production regression that changes the visible top evidence can pass the oracle command.
- The existing regression only proves day-status mismatch exits non-zero.

Required:

- Make `scripts/audit_scoring_oracle.py` exit non-zero when `comparison.top_signals.pass` is false.
- Add a regression test that keeps `day_status` and `sphere_scores` passing but intentionally mismatches `top_signals`, and assert non-zero exit.

### P1 — audit claim report is still hardcoded and stale

`scripts/audit_today.py` claims dynamic reports, but `14_claims_audit.md` is still a hardcoded table from the old Basil payload:

- old headline: `"поддержку в глубоких чувствах и творческих порывах"`
- old typo claim: `"Секспектиль Марса с Луной"`
- old unsupported why rows about houses `5` and `2`
- old contradiction: `"Общайся с близкими для улучшения отношений"`

After the rework, a fresh `make audit-day` produced a different `11_final_today_payload.json`, so these claim rows are no longer describing the actual payload. For any non-Basil run they are false by construction.

Required:

- Generate `14_claims_audit.md` from the actual `TodayPayload` fields and computed artifacts, or explicitly mark unimplemented automatic claim evaluation while listing actual payload excerpts.
- Do not hardcode old Basil text.
- Generic runs must not contain Basil-specific or old-payload claims unless clearly labeled as a separate historical snapshot.

### P1 — audit docs still contradict the current W0 artifact contract

`docs/audits/README.md` says `make audit-day` outputs "18 canonical numbered" files, but W0 contract and current root output are exactly 16 files: `00_...` through `15_...`.

`docs/audits/2026-07-08-solarsage-independent-audit.md` still states the pre-fix findings as current facts:

- raw retrograde flags fail;
- Moon phase fails with `46%` vs `43.792%`;
- Why contexts include stale unsupported claims.

Impact:

- The docs no longer match the current W0 state.
- Future agents/operators will misread fixed trust bugs as still active in the committed audit baseline.

Required:

- Fix README count to 16 and document optional `debug/`.
- Either update the 2026-07-08 audit doc to the post-W0 state, or rename/label it clearly as a pre-fix independent audit snapshot and link the post-W0 canonical artifacts.

### P1 — API response/cache schemas still contain silent `retrograde=False` defaults

The audited sidecar validation schemas were fixed, but API natal response/cache schemas still have silent defaults:

```text
apps/api/app/schemas/natal.py:236 NatalPreviewChartPlanet.retrograde: bool = False
apps/api/app/schemas/natal.py:338 NatalChartPlanet.retrograde: bool = False
```

These are not the new `SolarSagePlanetPosition` / `SolarSageTransitPlanet` validators, but they are still API/cache chart schemas. They can mask missing retrograde data as direct motion if any caller constructs them without the field.

Required:

- Remove silent `False` defaults from these chart planet schemas too, or make them `bool | None = None` and fail/derive at the boundary where speed is available.
- Add a small regression test proving missing retrograde is not silently converted to `False` for the API/cache chart schema path.

### P2 — final report has stale commit SHA

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/04_rework_01_report.md` says:

```text
Commit: 42f48f816ea422ceebba5a57702f2d4ecd5f8c5d
```

Actual reviewed HEAD is:

```text
6cc4f16012492344c4099efd21bddcdd69805ee3
```

Required:

- Update the report to the actual final commit after the final amend/commit.

### P2 — rework must leave a clean worktree except known unrelated files

Architect verification regenerated committed artifacts, leaving these tracked files dirty:

```text
artifacts/audit/2026-07-08/11_final_today_payload.json
artifacts/audit/2026-07-08/debug/audit_summary.json
artifacts/audit/2026-07-08/debug/final_today_payload.json
```

Required:

- Regenerate and commit the intended artifact state, or restore them to the committed artifact state.
- Final `git status --short --branch` must show only known unrelated untracked files:
  `.grace/`, `grace.db`, `skills/`, and `docs/superpowers/...`.

