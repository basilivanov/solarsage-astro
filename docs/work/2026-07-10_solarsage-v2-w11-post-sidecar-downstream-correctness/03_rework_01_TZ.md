# W11 Rework 01 TZ

Status: READY_FOR_CODER
Date: 2026-07-10
Base reviewed commit: `a5f2bd6`
Architect review: `docs/work/2026-07-10_solarsage-v2-w11-post-sidecar-downstream-correctness/02_arch_review.md`

## Goal

Turn the W11 audit from a scaffolding/demo into an independent, provenance-preserving proof of post-sidecar correctness.

Do not change sidecar astronomy, production scoring weights, rollout flags, UI design, deployment, or unrelated files.

## Required fixes

### 1. Make every expected scoring value independent

- Remove the audit import/call of private production scoring helpers, especially `_compute_day_status_v2`.
- Load canon YAML directly. Add `aspect_rules.v1.yml` for aspect weights and major/minor thresholds used by the independent day-status reducer.
- Keep production `ScoringV2Service.score_day()` as the single actual-result call.
- Independently calculate:
  - activation -> sphere mappings;
  - activation amounts;
  - unique-family convergence families and bonuses;
  - expected raw sphere scores from actual base input plus independent activation/convergence math;
  - dominance-cap threshold, final scores, flags, source ids, and cap amounts;
  - status breakdown and final day status.
- Do not call production mapping/convergence/cap/status helpers for expected values.

### 2. Enforce exact mapping/contribution traces

- Build the exact expected `(activation_id, sphere)` multiset.
- Extract the actual multiset without overwriting duplicates.
- Hard-fail on missing, duplicate, or extra activation contributions.
- Compare exact contribution amounts within `0.0001`.
- Compare exact convergence family sets with production debug and require the convergence contribution when expected.
- Make `scoring_activation_contribution_count` count contribution rows.

### 3. Make cap verification independent

- For each sphere, calculate expected raw score as:

```text
actual base_score input
+ sum(independent expected activation contributions)
+ independent expected convergence bonus
```

- Compare expected raw score to production `raw_score`.
- Calculate the cap from the full set of expected raw scores, not production raw scores.
- Compare expected/actual final score, `dominance_capped`, cap source id, and cap contribution amount.

### 4. Preserve replay/live provenance

- Never synthesize a V2 block in artifact replay or live mode.
- Replay/live payload missing V2 identity/body/evidence must produce structured failure and non-zero exit.
- `09_payload_v2.json` must be the normalized V2 block from the actual input/final payload.
- Synthetic mode may build a V2 block with `SemanticV2Service`, and metadata must say `synthetic_fixture`.
- Add a deterministic valid V2 artifact-replay input and a test that passes.
- Add a regression proving a V1 replay input fails instead of being upgraded inside the audit.

### 5. Correct live mode inputs

- Reconstruct live `day_signals` through the same public path used by `audit_today.py`:
  - current and previous-day transits;
  - `NormalizationService.normalize_day`;
  - `DayDeltaService.compute_deltas`;
  - `filter_day_scored_signals`.
- Use the trusted sidecar activation layer with those day signals for the actual scoring call.
- Keep the Today payload from `TodayService` and validate its V2 evidence/score breakdown against the trusted sidecar ids.
- Do not claim live success when the sidecar endpoint is unavailable.

### 6. Validate payload score breakdown and why references

- Extract payload activation evidence ids, score contribution ids, and why ids in snake_case/camelCase forms.
- Hard-fail if an activation contribution id in payload score breakdown is absent from activation evidence.
- Accept non-activation contribution sources only when their ids follow the production `base_signal:`, `convergence:`, or `cap:` policy and their source enum matches.
- Hard-fail if `whyToday.activationIds` contains an unknown id.
- Prefer equality for sidecar ids and payload evidence ids; at minimum missing sidecar ids remain a hard failure and extras are explicit warnings.

### 7. Make `11_frontend_fixture.json` genuinely frontend-ready

- Write a valid `AdaptedTodayPayload`-compatible payload, including a camelCase V2 block.
- Derive all assertions from that same payload.
- Add a hard self-consistency check: `assertions.has_v2` must equal whether `payload.v2` exists.
- Ensure fixture activation evidence, score breakdown, why ids, and audit versions preserve the trace.

### 8. Complete fixtures and tests

Populate every required fixture `expected` object with:

```json
{
  "mapped_spheres": {},
  "contributions": [],
  "convergence": {},
  "dominance_cap": {},
  "day_status": "steady",
  "payload_mapping": {}
}
```

Use exact deterministic values appropriate to each fixture.

Backend tests must include all section 11.1 failures:

- lost sidecar id;
- missing scoring contribution;
- contribution amount mismatch;
- convergence mismatch/family mismatch;
- missing payload evidence id;
- unmapped true/false policy;
- V1 replay rejected;
- frontend fixture self-consistency.

Scoring invariant tests must:

- compare exact planet/house/lot/angle/sphere mapping sets;
- assert exact contribution amounts;
- prove inactive skip;
- prove same-family dedup and multi-family convergence;
- use a fixture that definitely applies the dominance cap and assert exact cap trace.

Frontend tests must:

- consume the real generated/committed `11_frontend_fixture.json` rather than a separate hand-written object;
- validate it with `validateAdaptedTodayPayload` or the public schema;
- render the actual `TodayScreen` and assert V2 evidence is visible;
- render/open `WhyExpanded` and assert title/body/technique;
- render `DevAuditDrawer` and assert versions;
- prove no activation ids are fabricated.

Avoid `as any` for the V2 fixture proof.

### 9. GRACE, evidence, and report hygiene

- Add module contract/map markup to new code/test files as required by `AGENTS.md`.
- Replace the current false replay outputs with honest deterministic outputs.
- Commit required `artifacts/audit/2026-07-08/downstream/00..12` replay evidence so the frontend tests and architect can review the exact fixture. Optional debug files may be omitted if not needed.
- Final status must be clean except the known pre-existing untracked `.grace/`, `grace.db`, `skills/`, and `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.
- Do not rewrite `01_agent_report.md` as if its old SHA were current. Create:

```text
docs/work/2026-07-10_solarsage-v2-w11-post-sidecar-downstream-correctness/04_rework_01_report.md
```

Record code SHA, evidence/docs tip, exact commands/results, audit modes, remote CI, push, and deploy status.

## Required verification

```bash
cd apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_downstream_v2_audit.py \
  tests/test_scoring_v2_downstream_invariants.py \
  tests/test_payload_v2_downstream_mapping.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_breakdown_contract.py \
  -q
```

```bash
cd apps/api
source .venv/bin/activate
python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py \
  -q
```

```bash
npx vitest run \
  __tests__/components/ActivationEvidenceCard.downstream.test.tsx \
  __tests__/components/TodayScreen.v2-downstream.test.tsx
```

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

```bash
git diff --check a5f2bd6..HEAD
git show --check HEAD
git status --short --branch
```

Run and record:

- synthetic audit: must pass;
- valid V2 artifact replay: must pass;
- V1 replay negative regression: must fail in test;
- live audit: pass if the sidecar endpoint is available, otherwise record `NOT_RUN`/failure reason without weakening the implementation.

## Git process

- Use the normal git index.
- Do not use `sudo` for repository writes.
- Do not push or deploy.
- Commit the rework and report, then print the final SHAs.
