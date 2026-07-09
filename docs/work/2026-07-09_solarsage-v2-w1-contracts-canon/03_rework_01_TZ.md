# Rework 01 TZ: Finish W1 Contracts, Canon Startup Validation, Generated Contracts

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Fix the W1 blockers from `02_arch_review.md` without expanding into W2. W1 is accepted only when contracts are generated, canon validation is actually in the production boot path, and runtime metadata is truthful.

## Required Fixes

### 1. Wire strict canon validation into API startup/import path

Current problem:

- `apps/api/app/services/canon_service.py` exists but nothing in production startup/import path calls strict validation.
- `load_canon_bundle()` logs and continues on missing files.

Required:

- Add strict validation to `apps/api/app/main.py` or an equivalent API startup/import path.
- Use `validate_canon_bundle()` or a new strict wrapper.
- Missing or invalid canon must raise and prevent API boot in dev/test.
- Do not use best-effort logging mode for startup validation.

Tests:

- Add a test that proves API boot/startup invokes strict canon validation.
- Use monkeypatch/import strategy or a temporary canon dir.
- Do not mutate committed canon files.

### 2. Generate and commit OpenAPI/TS contracts

Current problem:

- `ActivationLayer` and `ScoringV2Result` are absent from `packages/contracts/openapi.json` and `_generated.ts`.
- `scripts/contracts/export_openapi.py` was not updated.

Required:

- Update `scripts/contracts/export_openapi.py` to include top-level W1 schemas.
- Run:

```bash
pnpm contracts:generate
```

- Commit generated:

```text
packages/contracts/openapi.json
packages/contracts/_generated.ts
```

- Add a test or simple contract check verifying generated files include:
  - `ActivationLayer`
  - canonical activation evidence fields (`techniqueFamily`, `targetType`, `strength`, `evidence`)
  - `ScoringV2Result`
  - `SphereScoreV2`
  - `SphereContribution`

Collision handling:

- There are two concepts named `ActivationEvidence`:
  - legacy Today convergence evidence in `apps/api/app/schemas/today.py`;
  - new canonical activation evidence in `apps/api/app/schemas/activation.py`.
- Generated contracts must not be ambiguous.
- If OpenAPI disambiguates cleanly, add tests proving `ActivationLayer.activations[]` points to the canonical activation evidence schema.
- If not, rename the legacy Today schema to `ConvergenceEvidence` or similar while preserving the JSON field `activationEvidence`.

### 3. Validate ActivationLayer index references

Required:

- API `ActivationLayer` must reject any id in `by_planet`, `by_house`, `by_lot`, or `by_angle` that is absent from `activations[].id`.
- Sidecar `ActivationLayer` must do the same.

Tests:

- Add API and sidecar tests for missing id references.
- Keep current positive tests green.

### 4. Populate runtime `canon_versions` in TodayMeta

Required:

- `TodayService` full payload meta and preview payload meta must set:

```python
canon_versions=get_canon_versions()
```

- Keep active runtime scoring metadata truthful:
  - no `ss-scoring-2.0` in production `TodayService` until W4;
  - `activation_layer_version=None` until W2.
- Keep `TODAY_CONTENT_VERSION = 7` unless you introduce another payload-shape change that requires bumping again.

Tests:

- Update `test_today_meta_versions.py` or endpoint tests to assert runtime-style meta includes all canon version keys:
  - `spheres`
  - `dignities`
  - `aspect_rules`
  - `activation_rules`
  - `scoring_v2`

### 5. Whitespace and report honesty

Required:

- Fix trailing whitespace in `apps/api/app/services/canon_service.py`.
- The report must include the required verification commands from the original W1 TZ. If a command fails, state it and explain whether it is related or unrelated. Do not omit it.

## Required Verification

Run and include exact results:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

```bash
pnpm contracts:generate
git diff --exit-code -- packages/contracts/openapi.json packages/contracts/_generated.ts
```

```bash
npx vitest run
```

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
```

```bash
rg -n 'ss-scoring-2.0' artifacts/audit/2026-07-08/11_final_today_payload.json apps/api/app/services/today_service.py
echo "Expected: no production/runtime payload path claims ss-scoring-2.0 before W4"
```

```bash
rg -n 'ActivationLayer|ScoringV2Result|SphereScoreV2|SphereContribution' packages/contracts/openapi.json packages/contracts/_generated.ts
```

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

If `npx vitest run` is too broad and fails on pre-existing unrelated tests, also run directly contract-affected frontend tests and document both results.

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w1-contracts-canon/04_rework_01_report.md
```

Include:

- changed files;
- how canon validation is wired into startup/import path;
- generated contract proof;
- how `ActivationEvidence` naming collision was handled;
- ActivationLayer index validation proof;
- runtime TodayMeta/canon_versions behavior;
- exact verification commands and results;
- commit SHA;
- push status `NOT_ATTEMPTED`.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W1 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w1-contracts-canon/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w1-contracts-canon/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w1-contracts-canon/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
