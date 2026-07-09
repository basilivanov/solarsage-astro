# W6 Architect Review — Rework Required

Status: REJECTED
Branch: main
Reviewed commit: 4a8fe33

W6 is moving in the right architectural direction, but it is not acceptable yet. The implementation currently breaks a green main/typecheck gate and misses several explicit W6 acceptance requirements.

## Findings

### P0 — `pnpm typecheck` fails after the W6 contract changes

Evidence:

```bash
pnpm typecheck
```

Result: exit 2.

Representative errors:

```text
__tests__/hooks/useDay.test.ts: meta is missing frontendPayloadVersion, payloadVersion
__tests__/lib/adapt-payload.test.ts: meta is missing frontendPayloadVersion, payloadVersion
e2e/mock-visual/fixtures/day-2026-07-05.ts: meta is missing frontendPayloadVersion, payloadVersion
e2e/mock-visual/fixtures/day-v2-2026-07-08.ts: ActivationEvidence is missing phase, polarity
lib/adapters/today-payload.ts: api.v2 is not assignable to AdaptedTodayPayload.v2
```

Impact: main is not green. Also, the adapter currently passes generated API V2 data directly into the adapted Zod type without normalizing defaulted fields like `phase`, `polarity`, and `debug`.

Required: `pnpm typecheck` must pass. Fix this at the boundary, not with `any` casts. The adapter should normalize/validate `api.v2` into the frontend V2 shape, and old fixtures/tests must remain contract-valid after the new meta fields.

### P0 — whitespace gate fails, and the report claims it was clean

Evidence:

```bash
git show --check --stat --oneline HEAD
git diff 70767b2..HEAD --check
```

Result: exit 2.

Files:

```text
apps/api/app/services/llm_claim_validator.py
apps/api/app/services/llm_service.py
apps/api/app/services/semantic_v2_service.py
apps/api/tests/test_llm_service.py
apps/api/tests/test_semantic_v2_service.py
```

Impact: required verification in `00_TZ.md` was not actually satisfied.

Required: remove all trailing whitespace / EOF blank-line issues and rerun both `git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check` and `git show --check HEAD`.

### P1 — Playwright mock visual test has no screenshot assertion

Evidence:

```bash
rg -n "toHaveScreenshot|screenshot" e2e/mock-visual/day-v2.spec.ts e2e/mock-visual
```

Only the README mentions screenshots. The W6 spec required at least one screenshot assertion for the V2 day page or stable V2 section.

Impact: W6 does not establish the visual regression baseline it was asked to add.

Required: add a deterministic `toHaveScreenshot(...)` assertion against a stable V2 section or full day screen and commit the matching snapshot if Playwright writes one.

### P1 — `generate_why_sections` accepts `evidence_packet`, but TodayService never passes it

Evidence:

```text
apps/api/app/services/llm_service.py:457-487 adds evidence_packet support
apps/api/app/services/today_service.py:365-369 calls generate_why_sections(why_contexts, semantic_layer) without evidence_packet
```

The W6 spec required evidence-packet prompt support for both concrete advice and why sections. Concrete advice has a caller path; why sections does not.

Impact: the user-visible "why" LLM path still lacks explicit V2 evidence context.

Required: build/pass a deterministic evidence packet for why sections when V2 data is available. It can have empty `concrete_rows` before concrete advice is built, but activation/scoring facts must come from `ActivationLayer`/`ScoringV2Result`, not LLM output.

### P1 — `TodayV2Audit.canonVersions` violates its own contract at runtime

Evidence:

```bash
cd apps/api && source .venv/bin/activate && python - <<'PY'
from app.schemas.activation import ActivationLayer
from app.services.semantic_v2_service import SemanticV2Service
al = ActivationLayer(
    calculation_version='calc',
    target_date='2026-07-08',
    target_time='12:00',
    target_tz='UTC',
    house_system='PLACIDUS',
    activations=[],
    by_planet={},
    by_house={},
    by_lot={},
    by_angle={},
)
block = SemanticV2Service().build_v2_block(activation_layer=al)
print({k: type(v).__name__ for k, v in block.audit.canon_versions.items()})
PY
```

Observed values are dicts, while `TodayV2Audit.canon_versions` and the generated OpenAPI contract require `dict[str, str]`.

Impact: API can serialize invalid V2 audit payloads and frontend contract validation would reject them.

Required: populate audit canon versions from `get_canon_versions()` or `ScoringV2Result.canon_versions`, never from the full loaded canon bundle.

### P1 — Dev audit drawer is enabled in production by `?audit=1`

Evidence:

```text
components/today/dev-audit-drawer.tsx:12-18
```

The component shows the drawer whenever the query param is present. The W6 spec allowed `?audit=1` only in non-production/test, or an explicit test prop.

Impact: production users can expose internal trace/diff/canon details by adding a query param.

Required: gate query-param visibility by non-production/test environment, keep `forceShow` for component tests, and keep the drawer hidden by default.

### P2 — V2 semantic output is not fully deterministic

Evidence:

```text
apps/api/app/services/semantic_v2_service.py:128 uses list({act.technique for act in acts})
apps/api/app/services/semantic_v2_service.py:219 uses list({act.technique for act in acts_in_family})
```

Sets do not preserve deterministic output ordering across Python hash seeds.

Impact: API output and visual snapshots can churn even when input activations are identical.

Required: sort technique lists deterministically. Add a small unit assertion for ordering.

### P2 — generated Next env file was committed with local production build state

Evidence:

```diff
next-env.d.ts
- import "./.next/types/routes.d.ts";
+ import "./.next-prod/types/routes.d.ts";
```

Impact: this is unrelated generated churn from the local build mode. It can make source state depend on whether the last run was dev or production.

Required: revert this file unless a separate, documented source-level config change truly requires it.

## Verification Performed By Architect

Passing:

```bash
npx vitest run __tests__/contracts/today.test.ts __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx
# 54 passed

cd apps/api && source .venv/bin/activate && python -m pytest tests/test_semantic_v2_service.py tests/test_today_v2_payload.py tests/test_llm_claim_validator.py tests/test_llm_service.py -q
# 19 passed

python3 scripts/check_logging_guardrails.py
# All guardrails PASSED
```

Failing:

```bash
pnpm typecheck
# exit 2

git show --check --stat --oneline HEAD
# exit 2

git diff 70767b2..HEAD --check
# exit 2
```

