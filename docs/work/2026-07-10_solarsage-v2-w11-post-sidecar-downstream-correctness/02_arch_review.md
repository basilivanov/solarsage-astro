# W11 Architect Review

Status: REWORK REQUIRED
Reviewed commits: `aecc699`, `a5f2bd6`
Date: 2026-07-10

## Executive decision

The implementation has useful scaffolding and the focused suites are green, but it does not yet prove the W11 hard invariants independently. Several checks currently confirm production output with production helpers or replace missing evidence with synthesized evidence. The frontend proof also does not consume the generated frontend fixture and does not render `TodayScreen`.

## Findings

### P0 — Day-status and cap checks are not independent

Evidence:

- `scripts/audit_downstream_v2.py` imports and calls the private production helper `_compute_day_status_v2()` to calculate the expected result.
- The comment says this is an independent reimplementation, but it is the exact production function under audit.
- Dominance-cap expected values start from production `SphereScoreV2.raw_score` and the production sum of raw scores. A production error in raw-score construction can therefore be accepted by the cap audit.
- The convergence debug-family comparison ends in `pass`, so a wrong family set with the same numeric bonus is not rejected.

Impact:

The audit cannot detect a shared production bug in V2 status, raw-score construction, convergence-family trace, or cap input math. This violates sections 8, 9.5, 9.6, 12.5 and the acceptance criterion requiring independent recalculation.

Required fix:

- Do not import or call `_compute_day_status_v2`, `_map_activation_to_spheres`, `_compute_convergence_bonus`, `_apply_dominance_cap`, or any other production scoring helper for expected values.
- Load the needed canon data directly, including `aspect_rules.v1.yml` for aspect weights/thresholds, and implement an audit-local status reducer.
- Build exact expected activation contribution keys and reject missing, duplicate, and extra actual activation contributions.
- Compare the exact expected unique-family set to the production convergence trace and require the matching convergence contribution when a bonus is expected.
- Reconstruct expected raw score from the sphere base score plus independently calculated activation amounts and convergence bonus, then calculate the cap from those expected raw scores. Compare raw score, final score, cap flag, cap source id, and cap amount.

### P0 — Artifact replay fabricates the evidence it claims to validate

Evidence:

- When the input final payload is V1, the audit calls `SemanticV2Service.build_v2_block()` and writes that synthesized block as `09_payload_v2.json`.
- The replay summary then reports `payload_preserves_sidecar_ids=true`, although the input artifact had no `payload.v2` at all.
- The generated `11_frontend_fixture.json` keeps the original V1 payload under `payload` but reports `assertions.has_v2=true` from the separately synthesized block.
- Direct inspection of the generated artifact shows `payload.v2` absent while `assertions.has_v2` is true.

Impact:

Replay mode no longer proves the supplied final payload. It proves a new semantic block created inside the audit. This violates the payload evidence hard invariant, the `09_payload_v2.json` copy contract, provenance requirements, and the frontend-fixture hard stop.

Required fix:

- Artifact replay and live modes must never synthesize a missing V2 body.
- A replay payload without V2 identity/body/evidence must fail with structured failures.
- `09_payload_v2.json` must be the normalized copy of the supplied/final payload V2 block.
- Use a deterministic valid V2 replay input for the passing replay proof. Add a regression proving the historical V1 input fails rather than being upgraded inside the audit.
- `11_frontend_fixture.json.assertions` must be derived from, and agree with, `11_frontend_fixture.json.payload`.

### P0 — Live mode does not score the live day signals

Evidence:

- Live mode fetches an activation layer and calls `TodayService`, but returns `day_signals=[]` with the comment that empty base scoring is acceptable.
- The actual `ScoringV2Service` result audited by the script is therefore not the live day calculation used by `TodayService`.

Impact:

Even if the sidecar endpoint becomes available, live mode cannot prove live status, base-plus-activation raw scores, cap behavior, or equality with the selected Today payload.

Required fix:

- Reconstruct the real filtered day signals through the normal transits -> normalization -> day delta -> `filter_day_scored_signals` path, as `audit_today.py` does.
- Score those signals with the trusted sidecar layer.
- Keep provenance explicit and compare the resulting activation ids/contribution ids with the real Today payload V2 block.

### P1 — Mapping and payload trace checks are incomplete

Evidence:

- The audit checks expected mappings for missing actual contributions but does not fail on extra actual activation-to-sphere contributions.
- Duplicate actual contributions overwrite each other in a dict.
- `scoring_activation_contribution_count` counts distinct activation ids, not contribution rows.
- Payload `scoreBreakdown` contribution ids are not audited against activation evidence or the allowed `base_signal`, `convergence`, and `cap` source-id policies.

Required fix:

- Compare exact expected and actual `(activation_id, sphere)` multisets.
- Detect duplicates and extras explicitly.
- Count contribution rows, not distinct ids, in the contribution count field.
- Validate every payload score contribution source/id and require activation ids to exist in `activationEvidence`.

### P1 — Required backend tests are absent or vacuous

Evidence:

- `test_downstream_v2_audit.py` does not prove failure on missing contribution, amount mismatch, convergence mismatch, or missing payload evidence.
- The unmapped warning assertion contains `warning_count >= 0`, which is always true.
- Planet/house/lot/angle tests do not compare exact canon sphere sets.
- The lot test accepts either mapping or no mapping.
- The dominance-cap test is conditional; the supplied `09_dominance_cap.json` produces no capped sphere, so the test passes without exercising cap behavior.

Required fix:

- Add all negative mutation tests required by section 11.1.
- Make mapping tests compare exact sets and exact expected amounts from fixture contracts.
- Make the cap fixture deterministically cap and assert the exact cap contribution/result.
- Add status fixtures/tests that assert exact expected breakdown values.

### P1 — Synthetic fixture contracts are incomplete

Evidence:

- Section 10 requires every fixture `expected` object to contain mapping, contributions, convergence, dominance cap, day status, and payload mapping expectations.
- Most fixtures currently use an empty `expected` object; the others contain only one partial field.

Required fix:

- Populate every required `expected` section with deterministic values.
- Drive tests from fixture expectations so fixtures are executable contracts rather than names only.

### P1 — Frontend tests do not prove the required UI path

Evidence:

- `TodayScreen.v2-downstream.test.tsx` never imports or renders `TodayScreen`.
- It uses an unrelated hand-written object with `as any`, not `11_frontend_fixture.json`.
- The `WhyExpanded` assertion only checks that `document.body` exists.
- The current generated frontend fixture is not `AdaptedTodayPayload`-compatible.

Required fix:

- Make `11_frontend_fixture.json.payload` a valid `AdaptedTodayPayload` with a camelCase V2 block.
- Parse it with the public frontend schema/validator.
- Render the actual `TodayScreen` with that payload and assert `today-screen`, `activation-evidence-card`, evidence text, and V2 why content.
- Render `WhyExpanded` in an opened state and assert its item title/body/technique.
- Assert all `whyToday.activationIds` and activation score contribution ids are present in fixture `activationEvidence`.

### P2 — Report, GRACE, and worktree hygiene need correction

Evidence:

- `01_agent_report.md` records evidence tip `6f5883c`, but the actual tip is `a5f2bd6`.
- New test files have only a short AI header and no module contract/map.
- Generated W11 downstream artifacts remain untracked while the report calls them unrelated.

Required fix:

- Correct report provenance in the rework report.
- Add required GRACE module contracts/maps to new code/test files.
- Regenerate honest downstream artifacts. Commit the deterministic `00..12` replay proof, or remove non-evidence outputs; final status must contain only the known pre-existing untracked paths.

## Architect checks

- `git diff --check 87adec4..a5f2bd6`: passed.
- Focused implementation report: 29 backend W11 tests, 52 W10 regressions, 6 frontend tests reported green.
- Manual fixture execution confirmed `09_dominance_cap.json` caps no sphere.
- Manual JSON inspection confirmed `11_frontend_fixture.json.assertions.has_v2=true` while `11_frontend_fixture.json.payload.v2` is absent.

## Decision

W11 is not accepted at `a5f2bd6`. The audit must be made independent and provenance-preserving before its green summary can be treated as downstream correctness evidence.
