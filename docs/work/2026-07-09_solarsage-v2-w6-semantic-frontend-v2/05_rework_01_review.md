# W6 Rework 01 Architect Review — Rework Required

Status: REJECTED
Branch: main
Reviewed commits: 9cb7826, 5e8c313

The requested green gates now pass, and the main W6 blockers are resolved. One architecture issue remains in the frontend adapter boundary.

## Finding

### P1 — V2 adapter masks invalid backend contract data instead of validating it

Evidence:

```text
lib/adapters/today-payload.ts:153-250
```

Current `buildV2Block(...)` manually reconstructs the V2 block and fills missing backend fields with fallback values:

```text
targetKey || ""
label || ""
strength ?? 0
payloadVersion || "today.v2"
debug as Record<string, any>
scoreBreakdown: Record<string, any>
targetType as "planet" | ...
```

Impact:

- This can fabricate V2 evidence from malformed backend data, which conflicts with W6: "Do not fabricate activation evidence if backend did not send it."
- It bypasses the Zod V2 contract that was added for exactly this boundary.
- It violates the adapter module invariant / rework TZ direction to avoid `any`, `ts-ignore`, or broad casts.
- Runtime API data is not validated by `fetchDay`; it is only typed at compile time. The adapter is therefore the practical frontend boundary where invalid V2 payloads should be caught, not silently repaired into empty evidence.

Required:

- Replace the manual fallback mapper with contract validation/normalization at the boundary.
- Preferred direction: import `TodayV2BlockSchema` and use it to parse/normalize `api.v2`, relying on Zod defaults for `active`, `phase`, `polarity`, and `debug`.
- If custom mapping remains necessary, it must use concrete types (`NonNullable<AdaptedTodayPayload["v2"]>` etc.), no `any`, no broad enum casts, and no fallback empty strings for required backend-owned evidence fields.
- Add/adjust tests proving:
  - valid V2 payload preserves data;
  - missing optional defaulted activation fields are normalized by schema defaults;
  - required malformed V2 fields are not silently fabricated into empty strings.

## Verification Performed By Architect

Passing:

```bash
pnpm contracts:generate
# exit 0, no git drift

pnpm typecheck
# exit 0

cd apps/api && source .venv/bin/activate && python -m pytest tests/test_semantic_v2_service.py tests/test_today_v2_payload.py tests/test_llm_claim_validator.py tests/test_llm_service.py tests/test_today_concrete_advice.py tests/test_today_meta_versions.py tests/test_day_endpoints.py -q
# 47 passed, 1 warning

npx vitest run __tests__/contracts/today.test.ts __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx
# 58 passed

E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
# 1 passed

python3 scripts/check_logging_guardrails.py
# All guardrails PASSED

git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
# both clean
```

