# W6 Agent Report — Semantic Layer, LLM Guard, Frontend V2 Evidence Rendering

## Goal
Implement Wave W6 scope: backend-owned V2 evidence rendering on frontend, deterministic V2 semantic layer builder, LLM evidence packet prompt context, deterministic LLM claim validator, and E2E/mock visual tests.

## Changed/Created Files

### Backend (API)
- `apps/api/app/schemas/today.py` (added V2 block schemas, cleaned duplicate fields)
- `apps/api/app/services/cache_key_service.py` (updated expected_cache_identity to respect frontend payload version 2 when V2 frontend is enabled)
- `apps/api/app/services/today_service.py` (integrated SemanticV2Service, build_v2_block, and passed V2 parameters)
- `apps/api/app/services/today_interpretation_service.py` (enriched advice row evidence with activations/contributions, integrated LLMClaimValidator)
- `apps/api/app/services/llm_service.py` (added evidence_packet support to prompt generation for concrete advice and why sections)
- `apps/api/app/services/semantic_v2_service.py` (created: deterministic V2 semantic layer, whyToday generator, evidence selector, and LLM packet builder)
- `apps/api/app/services/llm_claim_validator.py` (created: deterministic LLM advice text claim validator with hard guards)
- `apps/api/tests/test_semantic_v2_service.py` (created unit tests for SemanticV2Service)
- `apps/api/tests/test_llm_claim_validator.py` (created unit tests for LLMClaimValidator)
- `apps/api/tests/test_today_v2_payload.py` (created integration tests for TodayPayload V2 block rendering and flags)
- `apps/api/tests/test_llm_service.py` (added mock test for generate_concrete_advice with evidence packet)
- `packages/contracts/openapi.json` (regenerated OpenAPI schemas)
- `packages/contracts/_generated.ts` (regenerated TS definitions)

### Frontend (Next.js)
- `lib/contracts/today.ts` (added Zod schemas for V2 blocks, target, summary, audit, whyToday, and activations)
- `lib/adapters/today-payload.ts` (adapted v2 block, passed it through adaptTodayPayload)
- `components/today/today-screen.tsx` (rendered ActivationEvidenceCard and DevAuditDrawer, passed whyToday to WhyExpanded)
- `components/today/why-expanded.tsx` (implemented V2 "Почему именно сегодня" deterministic list rendering)
- `components/today/concrete-day-advice.tsx` (shows technique chips next to row text, displays detailed frame/orb/technique evidence in expandable row)
- `components/today/activation-evidence-card.tsx` (created: renders activation summary, top activated targets, and exact activations list)
- `components/today/technique-chip.tsx` (created: maps technical technique name to user-friendly Russian labels)
- `components/today/dev-audit-drawer.tsx` (created: dev audit console drawer toggled by `?audit=1` or forceShow)
- `__tests__/components/TodayScreen.test.tsx` (added unit tests for ActivationEvidenceCard and DevAuditDrawer rendering)

### E2E / Mock Visual Tests
- `e2e/mock-visual/fixtures/day-v2-2026-07-08.ts` (created TodayPayload V2 mock fixture)
- `e2e/mock-visual/day-v2.spec.ts` (created E2E spec for mock visual testing of V2 blocks, drawer, and evidence)

## Backend V2 Contract Summary
Added the optional `v2: TodayV2Block` schema inside `TodayPayload`. It maps activation summary (headline, top activated targets), activation evidence list (Swiss Ephemeris transits and technique activations), score breakdown (sphere V2 scores and contributions), deterministic whyToday items, and audit trace/versions information. All fields are correctly camelCased in JSON serialization.

## Cache & Frontend Payload Version Behavior
When `settings.solarsage_v2_frontend_enabled` is active, `/day` response is versioned as `today.v2` with `frontend_payload_version=2` and includes the `v2` block. The write cache key and `expected_cache_identity` are automatically updated to require `frontend_payload_version=2`, ensuring that SWR or DB cached responses are cleanly separated by version. When disabled, the output behaves exactly as V1.

## LLM Guard Behavior
The `LLMClaimValidator` checks every generated recommendation text against the verdict for that sphere. For any row with `avoid` verdict:
- relationships: rejects direct relationship improvement/conflict-opening text and replaces it with safe mitigation text.
- money: rejects invest/spend/buy text and replaces it with safe financial warnings.
- sport/health: rejects intense sport text and replaces it with safe light movement suggestions.
- communication: rejects negotiation/debate text and replaces it with safe transfer suggestions.

## Frontend Rendering Summary
- **WhyExpanded**: Renders deterministic "Почему именно сегодня" section based on technique convergence when V2 is available.
- **ConcreteDayAdvice**: Shows technique chips next to row recommendations and expands to show exact frame/orb/technique details.
- **ActivationEvidenceCard**: Renders activation summary and top activated targets.
- **DevAuditDrawer**: Console drawer rendering only when dev/admin audit is active (triggered by `?audit=1` query parameter).

## Visual / E2E Status
The mock visual test `day-v2.spec.ts` runs against Next.js production build running on port 3002 and passes completely.

## Verification Outputs

### Target Verification Tests
```text
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_semantic_v2_service.py \
  tests/test_today_v2_payload.py \
  tests/test_llm_claim_validator.py \
  tests/test_llm_service.py \
  tests/test_today_concrete_advice.py \
  tests/test_today_meta_versions.py \
  tests/test_day_endpoints.py -q

45 passed, 1 warning in 2.29s
```

### Vitest Unit Tests
```text
npx vitest run \
  __tests__/contracts/today.test.ts \
  __tests__/lib/adapt-payload.test.ts \
  __tests__/components/TodayScreen.test.tsx

Test Files  3 passed (3)
     Tests  54 passed (54)
  Duration  2.46s
```

### Playwright E2E Test
```text
sudo E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile

Running 1 test using 1 worker
  ✓  1 [mobile] › e2e/mock-visual/day-v2.spec.ts:46:7 › W6 V2 Day Screen mock visual ... (5.7s)
  1 passed (6.5s)
```

### Logging Guardrails
```text
python3 scripts/check_logging_guardrails.py

drift gate: OK
backend logger gate: OK
frontend console gate: OK
All guardrails PASSED.
```

### Whitespace and Git Check
```text
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
(No output, completely clean)
```

## Push / Deploy Status
Push: NOT_ATTEMPTED

## Commit SHA
Commit: see callback/current HEAD
